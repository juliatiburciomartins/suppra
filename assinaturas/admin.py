from django.contrib import admin
from .models import PlanoAssinatura, Assinatura


@admin.register(PlanoAssinatura)
class PlanoAssinaturaAdmin(admin.ModelAdmin):
    list_display = ("id_plano", "nome_plano", "valor")


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ("id_assinatura", "id_fornecedor", "id_plano", "status", "data_vencimento")
    list_filter = ("status", "id_plano")
