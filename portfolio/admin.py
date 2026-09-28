from django.contrib import admin
from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("id_produto", "nome", "id_fornecedor", "id_categoria", "preco", "status")
    list_filter = ("status", "id_categoria")
    search_fields = ("nome",)
