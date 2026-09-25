from django import forms

from core.models import CategoriaInsumo
from demandas.models import Demanda


class DemandaForm(forms.ModelForm):
    """
    Publicação/edição de Demanda pelo comerciante (RF-009/RF-011).

    A ordem dos campos aqui é a mesma em que `templates/demandas/demanda_form.html`
    renderiza via `{{ form.<campo> }}`.
    """

    class Meta:
        model = Demanda
        fields = ["id_categoria", "descricao_produto", "quantidade_produto"]
        widgets = {
            "id_categoria": forms.Select(),
            "descricao_produto": forms.Textarea(attrs={"rows": 4}),
            "quantidade_produto": forms.TextInput(attrs={"placeholder": "Ex.: 10 caixas por semana"}),
        }
        labels = {
            "id_categoria": "Categoria de insumo",
            "descricao_produto": "Descrição do produto desejado",
            "quantidade_produto": "Quantidade aproximada",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id_categoria"].queryset = CategoriaInsumo.objects.filter(status="ativa").order_by("nome")
