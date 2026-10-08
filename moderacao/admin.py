from django.contrib import admin
from .models import Denuncia


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    """Denúncias de conteúdo (RF-025). Fila e histórico no painel."""

    list_display = (
        "id_denuncia",
        "tipo_conteudo",
        "id_denunciante",
        "status",
        "data_denuncia",
    )
    list_filter = ("status", "tipo_conteudo", "data_denuncia")
    search_fields = ("id_denunciante__nome", "descricao")
    list_select_related = ("id_denunciante", "id_produto", "id_demanda")

    def has_add_permission(self, request):
        # A denúncia é criada pelo usuário (CU14), não pelo painel.
        return False
