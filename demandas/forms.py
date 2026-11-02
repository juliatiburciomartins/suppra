"""
Formulários de demanda (RF-009 / RF-011, CU07).

A ordem dos campos aqui é a mesma em que `templates/demandas/demanda_form.html`
renderiza os campos — ver `demandas/forms.py` (mesma convenção do resto do
projeto).
"""

from django import forms

from core.models import CategoriaInsumo
from demandas.models import Demanda


class DemandaForm(forms.ModelForm):
    """
    Publicação/edição de Demanda pelo comerciante (RF-009/RF-011).

    Campos exigidos pelo CU07 (passo 2): categoria de insumo, descrição do
    produto desejado e quantidade aproximada.
    """

    class Meta:
        model = Demanda
        fields = ["id_categoria", "descricao_produto", "quantidade_produto"]
        widgets = {
            "id_categoria": forms.Select(),
            "descricao_produto": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Ex.: Cerveja long neck, latinha 350ml"}
            ),
            "quantidade_produto": forms.TextInput(
                attrs={"placeholder": "Ex.: 10 caixas por semana"}
            ),
        }
        labels = {
            "id_categoria": "Categoria de insumo",
            "descricao_produto": "Descrição do produto desejado",
            "quantidade_produto": "Quantidade aproximada",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só categorias ativas (RF-032/CU20: a equipe gestora desativa o que não
        # quiser mais oferecer).
        self.fields["id_categoria"].queryset = CategoriaInsumo.objects.filter(
            status="ativa"
        ).order_by("nome")
        self.fields["id_categoria"].empty_label = "Selecione uma categoria"

        # Mensagens de erro que dizem o campo e a correção (RNF-010 / CU07 E1).
        self.fields["descricao_produto"].error_messages["required"] = (
            "Descreva o produto que você procura."
        )
        self.fields["quantidade_produto"].error_messages["required"] = (
            "Informe a quantidade aproximada."
        )

    def clean_descricao_produto(self):
        descricao = (self.cleaned_data.get("descricao_produto") or "").strip()
        if len(descricao) < 5:
            raise forms.ValidationError(
                "Descreva o produto desejado com pelo menos 5 caracteres."
            )
        return descricao

    def clean_quantidade_produto(self):
        quantidade = (self.cleaned_data.get("quantidade_produto") or "").strip()
        if len(quantidade) < 1:
            raise forms.ValidationError("Informe a quantidade aproximada.")
        return quantidade