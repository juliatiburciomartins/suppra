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
    list_display = ("id_log", "id_usuario", "acao", "modelo_afetado", "data_alteracao")
    list_filter = ("acao", "modelo_afetado")
