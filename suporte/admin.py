from django.contrib import admin
from .models import Suporte


@admin.register(Suporte)
class SuporteAdmin(admin.ModelAdmin):
    list_display = ("id_suporte", "id_usuario", "assunto", "status", "data_abertura")
    list_filter = ("status",)
