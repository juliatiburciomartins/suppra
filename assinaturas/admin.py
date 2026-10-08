"""
Painel de planos e assinaturas (RF-017 / CU23).

O CU23 descreve três coisas da equipe gestora:
  - cadastrar plano (nome, preço mensal, descrição dos benefícios);
  - editar plano existente;
  - ver assinaturas ativas, filtrando por status ou por fornecedor.

As duas primeiras são o `ModelAdmin` padrão. A terceira é o `list_display` com
`list_filter` de `AssinaturaAdmin`. Como `data_vencimento` é `DateField`, o
`date_hierarchy` também dá o filtro por período exigido pela documentação.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Assinatura, PlanoAssinatura


@admin.register(PlanoAssinatura)
class PlanoAssinaturaAdmin(admin.ModelAdmin):
    """CU23, fluxo principal e A1 — cadastrar e editar planos."""

    list_display = ("id_plano", "nome_plano", "valor", "total_assinaturas", "nivel")
    search_fields = ("nome_plano", "descricao")
    ordering = ("valor",)

    @admin.display(description="Assinaturas")
    def total_assinaturas(self, obj):
        return obj.assinaturas.count()

    @admin.display(description="Nível")
    def nivel(self, obj):
        if obj.eh_gold:
            return "Gold"
        if obj.eh_silver:
            return "Silver"
        return "—"


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    """CU23 A2 — listar assinaturas vigentes, filtrando por status/fornecedor."""

    list_display = (
        "id_assinatura",
        "id_fornecedor",
        "id_plano",
        "selo_plano",
        "data_inicio",
        "data_vencimento",
        "status_exibido",
    )
    list_filter = ("status", "id_plano", "data_vencimento")
    search_fields = ("id_fornecedor__nome", "id_fornecedor__email")
    date_hierarchy = "data_vencimento"
    list_select_related = ("id_fornecedor", "id_plano")
    # `data_vencimento` é DateField (não DateTimeField), então o `date_hierarchy`
    # funciona sem depender das tabelas de fuso do MySQL — diferente das telas de
    # denúncia e suporte, cujos campos são DateTimeField.

    @admin.display(description="Nível")
    def selo_plano(self, obj):
        nivel = obj.id_plano.nivel
        if nivel == "gold":
            return format_html(
                '<span style="background:#eed16b;color:#5a4a05;padding:2px 10px;'
                'border-radius:999px;font-weight:700;font-size:0.72rem;">Gold</span>'
            )
        if nivel == "silver":
            return format_html(
                '<span style="background:#ececf1;color:#565b6b;padding:2px 10px;'
                'border-radius:999px;font-weight:700;font-size:0.72rem;">Silver</span>'
            )
        return "—"

    @admin.display(description="Status")
    def status_exibido(self, obj):
        return obj.get_status_exibicao()