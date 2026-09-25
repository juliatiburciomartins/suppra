from django.contrib import admin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("id_usuario", "nome", "email", "tipo_perfil", "status_conta")
    list_filter = ("tipo_perfil", "status_conta")
    search_fields = ("nome", "email", "cpf_cnpj")
