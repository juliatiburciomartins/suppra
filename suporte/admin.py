"""
Painel de chamados de suporte (RF-019 / CU19).

O CU19 diz que a solicitação é "encaminhada à equipe gestora" e que o status
acompanha o atendimento. Os três estados existem no `banco.sql`
('aberto', 'em_atendimento', 'encerrado'), então o admin do Django é o lugar
natural para a equipe operar o chamado.

Para deixar o trabalho mais rápido, há duas ações em lote que ajustam o status
de vários chamados de uma vez.
"""

from django.contrib import admin

from .models import Suporte


@admin.register(Suporte)
class SuporteAdmin(admin.ModelAdmin):
    list_display = (
        "id_suporte",
        "id_usuario",
        "assunto",
        "status",
        "data_abertura",
        "tem_evidencia",
    )
    list_filter = ("status", "data_abertura")
    search_fields = ("id_usuario__nome", "id_usuario__email", "assunto", "descricao")
    list_select_related = ("id_usuario",)
    # `data_abertura` é DateTimeField (DEFAULT CURRENT_TIMESTAMP no banco.sql),
    # então `date_hierarchy` exigiria as tabelas de fuso do MySQL carregadas —
    # ver a nota em `moderacao/admin.py`. O filtro `data_abertura` acima já
    # permite filtrar por período.
    readonly_fields = (
        "id_usuario",
        "assunto",
        "descricao",
        "img",
        "data_abertura",
        "contato_do_usuario",
    )
    actions = ("marcar_em_atendimento", "encerrar_chamados")

    def has_add_permission(self, request):
        # Chamado é aberto pelo usuário (CU19), não pelo painel.
        return False

    @admin.display(boolean=True, description="Evidência")
    def tem_evidencia(self, obj):
        return bool(obj.img)

    @admin.display(description="Contato do solicitante")
    def contato_do_usuario(self, obj):
        """O banco.sql não guarda telefone/e-mail do chamado; os dados ficam no
        usuário, então o admin mostra os canais de contato do RF-012."""
        usuario = obj.id_usuario
        partes = [f"E-mail: {usuario.email}"]
        if usuario.telefone:
            partes.append(f"Telefone: {usuario.telefone}")
        if usuario.whatsapp:
            partes.append(f"WhatsApp: {usuario.whatsapp}")
        return " | ".join(partes)

    @admin.action(description="Marcar como em atendimento")
    def marcar_em_atendimento(self, request, queryset):
        total = queryset.exclude(status="encerrado").update(status="em_atendimento")
        self.message_user(request, f"{total} chamado(s) em atendimento.")

    @admin.action(description="Encerrar chamados selecionados")
    def encerrar_chamados(self, request, queryset):
        total = queryset.exclude(status="encerrado").update(status="encerrado")
        self.message_user(request, f"{total} chamado(s) encerrado(s).")