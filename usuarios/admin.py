from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """
    Usuários do Hub (fornecedores/comerciantes). A senha é exibida somente como
    hash e só pode ser definida via fluxo de recuperação/`set_password`.
    A exclusão física fica desabilitada: contas saem do ar por anonimização
    (RF-016) ou suspensão (status_conta), pois as FKs do banco.sql impedem DELETE.
    """

    list_display = ("id_usuario", "nome", "email", "tipo_perfil", "status_conta")
    list_filter = ("tipo_perfil", "status_conta")
    search_fields = ("nome", "email", "cpf_cnpj")
    readonly_fields = ("password",)
    fields = ("nome", "email", "password", "cpf_cnpj", "telefone", "whatsapp", "tipo_perfil", "status_conta")

    def has_delete_permission(self, request, obj=None):
        return False
