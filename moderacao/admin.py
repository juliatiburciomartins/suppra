from django.contrib import admin
from .models import Denuncia


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ("id_denuncia", "id_denunciante", "tipo_conteudo", "status", "data_denuncia")
    list_filter = ("status", "tipo_conteudo")
