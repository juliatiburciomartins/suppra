"""
Painel de moderação (RF-025 / CU22) no Django Admin.

O CU22 descreve duas decisões do administrador:

  - **Revisão de denúncia**: arquivar (improcedente) ou aplicar suspensão de
    conta ao infrator (confirmação de informação enganosa / descumprimento dos
    Termos de Uso). As duas viraram *actions* da lista de denúncias.
  - **Revisão de avaliação**: manter ou remover a avaliação.

`Avaliacao` não pode ser registrada no Django Admin porque usa chave primária
composta — o Admin recusa o registro com `ImproperlyConfigured`. A fila de
avaliações do CU22 é por isso uma view do app, protegida por `admin_required`
(ver `moderacao/views.py`).
"""

from django.contrib import admin, messages
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html

from moderacao.models import Denuncia
from moderacao.services import resumo_do_conteudo, julgar_denuncia

# NOTA — Avaliacao (CU22, fluxo alternativo A1: fila de avaliações):
#
# `Avaliacao` usa chave primária composta (id_comerciante, id_fornecedor) e o
# Django Admin recusa o registro com `ImproperlyConfigured: The model Avaliacao
# has a composite primary key`. Por isso essa fila é uma view do app, com
# controle de acesso por `admin_required`: ver `moderacao/views.py`
# (fila_avaliacoes_view / decidir_avaliacao_view). O mesmo vale para Favorito,
# que não tem tela de moderação na documentação.


class DenunciaAdmin(admin.ModelAdmin):
    """
    Fila de denúncias pendentes e histórico de decisões (CU22).

    A decisão não é uma edição de campo: passa por
    `moderacao.services.julgar_denuncia`, que valida, audita (RF-024) e suspende
    a conta do infrator quando aplicável.
    """

    list_display = (
        "id_denuncia",
        "tipo_conteudo",
        "conteudo_denunciado",
        "id_denunciante",
        "status",
        "data_denuncia",
    )
    list_filter = ("status", "tipo_conteudo", "data_denuncia")
    search_fields = ("id_denunciante__nome", "descricao")
    list_select_related = ("id_denunciante", "id_produto", "id_demanda")
    # Sem `date_hierarchy`: o Django só consegue derivar ano/mês/dia de um
    # DateTimeField se o servidor MySQL tiver as tabelas de fuso carregadas
    # (`mysql.time_zone_name`). Sem elas a tela quebra com "Database returned an
    # invalid datetime value". Como o README manda cada programador usar o MySQL
    # que já tem instalado, depender disso quebraria em parte da equipe e em
    # hospedagem em nuvem (RNF-011/RNF-012). O filtro por período do CU21 está na
    # tela `log_auditoria` (core/admin_views.py), que usa consulta direta.
    readonly_fields = (
        "id_denunciante",
        "tipo_conteudo",
        "conteudo_denunciado_detalhado",
        "evidencia",
        "data_denuncia",
    )
    actions = ("arquivar_denuncias", "proceder_denuncias")

    def has_add_permission(self, request):
        # A denúncia é criada pelo usuário (CU14), não pelo painel.
        return False

    @admin.display(description="Conteúdo denunciado")
    def conteudo_denunciado(self, obj):
        titulo, autor, referencia = resumo_do_conteudo(obj)
        return f"{titulo} — {autor} (id {referencia})"

    @admin.display(description="Conteúdo (detalhado)")
    def conteudo_denunciado_detalhado(self, obj):
        """Link para a página real, para o admin julgar com o texto na tela (CU22)."""
        if obj.tipo_conteudo == "portfolio" and obj.id_produto:
            titulo, autor, _ = resumo_do_conteudo(obj)
            url = reverse("detalhes_fornecedor", args=[obj.id_produto.id_fornecedor_id])
            return format_html(
                "<strong>{}</strong><br>Autor: {}<br>"
                '<a href="{}" target="_blank">Ver portfólio</a>',
                titulo,
                autor,
                url,
            )

        if obj.tipo_conteudo == "demanda" and obj.id_demanda:
            titulo, autor, _ = resumo_do_conteudo(obj)
            try:
                url = reverse("detalhes_demanda", args=[obj.id_demanda_id])
                link = format_html(
                    '<a href="{}" target="_blank">Ver demanda</a>', url
                )
            except NoReverseMatch:
                link = "(demanda removida)"
            return format_html(
                "<strong>{}</strong><br>Autor: {}<br>{}", titulo, autor, link
            )

        return "(conteúdo removido da plataforma)"

    @admin.action(description="Arquivar denúncias selecionadas (improcedentes)")
    def arquivar_denuncias(self, request, queryset):
        """CU22: arquivar quando a denúncia não se sustenta."""
        total = 0
        for denuncia in queryset.filter(status="pendente"):
            julgar_denuncia(denuncia, request.user, "arquivar", motivo="Improcedente")
            total += 1

        self.message_user(
            request,
            f"{total} denúncia(s) arquivada(s).",
            level=messages.SUCCESS if total else messages.WARNING,
        )

    @admin.action(description="Confirmar denúncias selecionadas e suspender infrator")
    def proceder_denuncias(self, request, queryset):
        """
        CU22: "aplicar suspensão de conta ao infrator em caso de confirmação de
        informações enganosas ou descumprimento dos Termos de Uso".
        """
        total, suspensos = 0, 0
        for denuncia in queryset.filter(status="pendente"):
            _, infrator = julgar_denuncia(
                denuncia,
                request.user,
                "procedente",
                motivo="Denúncia confirmada pela equipe gestora.",
            )
            total += 1
            if infrator is not None:
                suspensos += 1

        self.message_user(
            request,
            f"{total} denúncia(s) confirmada(s); {suspensos} conta(s) suspensa(s).",
            level=messages.WARNING if suspensos else messages.SUCCESS,
        )


admin.site.register(Denuncia, DenunciaAdmin)