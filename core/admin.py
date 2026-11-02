from django.contrib import admin
from .models import CategoriaInsumo, TermoUso, TermoAceite, LogAlteracao


@admin.register(CategoriaInsumo)
class CategoriaInsumoAdmin(admin.ModelAdmin):
    """
    CU20 / RF-031 a RF-034 — gerenciar categorias de insumo.

    "O sistema exibe as categorias já cadastradas com nome e status de cada uma
    (ativa ou inativa)" e "garantindo que não há duplicidade" na criação.
    """

    list_display = ("id_categoria", "nome", "status", "total_produtos", "total_demandas")
    list_filter = ("status",)
    search_fields = ("nome",)

    def get_readonly_fields(self, request, obj=None):
        # Editar é permitido (RF-033); excluir é bloqueado quando há produtos
        # vinculados (RF-034 / CU20 A2-E2), tratado em has_delete_permission.
        return ()

    def has_delete_permission(self, request, obj=None):
        """
        RF-034 / CU20 A2: "O sistema verifica se há produtos vinculados à
        categoria selecionada" e, havendo, orienta a desvincular antes.

        `Produto.id_categoria` é `on_delete=PROTECT`, então sem esta checagem o
        admin deixaria clicar em excluir e o banco recusaria com um erro técnico
        em vez da mensagem que a documentação exige.
        """
        if obj is None:
            return super().has_delete_permission(request, obj)

        if obj.produtos.exists():
            return False

        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        if obj.produtos.exists():
            from django.contrib import messages
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "Não é possível excluir a categoria porque há produtos vinculados."
            )
        super().delete_model(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.has_delete_permission(request):
            actions.pop("delete_selected", None)
        return actions

    @admin.display(description="Produtos", ordering="pk")
    def total_produtos(self, obj):
        return obj.produtos.count()

    @admin.display(description="Demandas", ordering="pk")
    def total_demandas(self, obj):
        return obj.demandas.count()


@admin.register(TermoUso)
class TermoUsoAdmin(admin.ModelAdmin):
    list_display = ("id_termo_uso", "versao", "data_vigencia")


@admin.register(TermoAceite)
class TermoAceiteAdmin(admin.ModelAdmin):
    """RF-001/RF-002 + RNF-007: evidência do aceite, gravada no cadastro."""

    list_display = ("id_aceite", "id_usuario", "id_termo_uso", "data_aceite")
    list_select_related = ("id_usuario", "id_termo_uso")
    search_fields = ("id_usuario__nome", "id_usuario__email")

    def has_add_permission(self, request):
        # O aceite é registrado por `CadastroForm.save()` no ato do cadastro.
        return False

    def has_change_permission(self, request, obj=None):
        # Evidência de consentimento não é editável (LGPD).
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogAlteracao)
class LogAlteracaoAdmin(admin.ModelAdmin):
    """
    CU21 — "Consultar log de auditoria (administrador)".

    O CU21 pede filtros "por usuário, por modelo ou por período":
      - `list_filter` cobre modelo e ação;
      - `search_fields` cobre o usuário responsável;
      - `date_hierarchy` cobre o período (data e hora da alteração);
      - `conteudo_anterior` fica visível na página de detalhe, que é onde o CU21
        diz que o administrador consulta o "conteúdo anterior à alteração".

    Tudo somente-leitura: a pós-condição do CU21 é "Nenhuma alteração é
    realizada no log durante a consulta".
    """

    list_display = (
        "id_log",
        "id_usuario",
        "acao",
        "modelo_afetado",
        "id_registro_afetado",
        "resumo_anterior",
        "data_alteracao",
    )
    list_filter = ("acao", "modelo_afetado", "data_alteracao")
    search_fields = (
        "id_usuario__nome",
        "id_usuario__email",
        "modelo_afetado",
        "conteudo_anterior",
    )
    list_select_related = ("id_usuario",)
    # Sem `date_hierarchy` (ver nota em `moderacao/admin.py`). O filtro por
    # período do CU21 está na tela dedicada `log_auditoria`, em
    # core/admin_views.py, com os três filtros (usuário, modelo, período).
    readonly_fields = (
        "id_usuario",
        "acao",
        "modelo_afetado",
        "id_registro_afetado",
        "conteudo_anterior",
        "data_alteracao",
    )

    def has_add_permission(self, request):
        # RF-024: o log é gravado pelo sistema (`core.services.registrar_log`) e
        # pelo django-simple-history, nunca digitado no painel.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Conteúdo anterior")
    def resumo_anterior(self, obj):
        return (obj.conteudo_anterior or "—")[:90]
