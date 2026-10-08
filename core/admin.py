from django.contrib import admin
from .models import CategoriaInsumo, TermoUso, TermoAceite, LogAlteracao


@admin.register(CategoriaInsumo)
class CategoriaInsumoAdmin(admin.ModelAdmin):
    list_display = ("id_categoria", "nome", "status")
    list_filter = ("status",)
    search_fields = ("nome",)


@admin.register(TermoUso)
class TermoUsoAdmin(admin.ModelAdmin):
    list_display = ("id_termo_uso", "versao", "data_vigencia")


@admin.register(TermoAceite)
class TermoAceiteAdmin(admin.ModelAdmin):
    list_display = ("id_aceite", "id_usuario", "id_termo_uso", "data_aceite")


@admin.register(LogAlteracao)
class LogAlteracaoAdmin(admin.ModelAdmin):
    """
    Log de auditoria (RF-024), somente leitura. Suporte ao CU21.

    Filtros por ação, modelo e data; busca pelo usuário responsável. Sem
    `date_hierarchy`: em DateTimeField ele depende das tabelas de fuso do MySQL.
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
    readonly_fields = (
        "id_usuario",
        "acao",
        "modelo_afetado",
        "id_registro_afetado",
        "conteudo_anterior",
        "data_alteracao",
    )

    def has_add_permission(self, request):
        # O log é gravado pelo sistema (`core.services.registrar_log`) e pelo
        # django-simple-history, nunca digitado no painel.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Conteúdo anterior")
    def resumo_anterior(self, obj):
        return (obj.conteudo_anterior or "—")[:90]
