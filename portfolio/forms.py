"""
Formulários do portfólio do fornecedor (RF-005 a RF-008, CU10).

Segue a mesma convenção de `demandas/forms.py` e `usuarios/forms.py`: os
labels e a ordem dos campos aqui são os mesmos que o template renderiza.

A ordem dos campos declarada em `Meta.fields` é a ordem em que
`templates/produtos/produto_form.html` e `templates/produtos/gerenciar_portfolio.html`
percorrem o form.
"""

from django import forms

from core.models import CategoriaInsumo
from portfolio.models import Produto


class ProdutoForm(forms.ModelForm):
    """
    Cadastro/edição de um item do portfólio.

    Campos exigidos pelo CU10 (passo 6): nome do produto ou serviço, categoria de
    insumo, preço unitário e dados de contato para negociação (telefone e/ou
    WhatsApp).
    """

    class Meta:
        model = Produto
        fields = [
            "nome",
            "id_categoria",
            "preco",
            "telefone_contato",
            "whatsapp_contato",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Refrigerante lata 350ml"}),
            "id_categoria": forms.Select(),
            "preco": forms.TextInput(attrs={"placeholder": "0,00", "inputmode": "decimal"}),
            "telefone_contato": forms.TextInput(attrs={"placeholder": "(19) 3333-3333"}),
            "whatsapp_contato": forms.TextInput(attrs={"placeholder": "(19) 99999-9999"}),
        }
        labels = {
            "nome": "Nome do produto ou serviço",
            "id_categoria": "Categoria de insumo",
            "preco": "Preço unitário",
            "telefone_contato": "Telefone para contato",
            "whatsapp_contato": "WhatsApp para contato",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Só categorias ativas aparecem no formulário (RF-032/CU20: a equipe
        # gestora desativa o que não quiser mais oferecer).
        self.fields["id_categoria"].queryset = CategoriaInsumo.objects.filter(
            status="ativa"
        ).order_by("nome")
        self.fields["id_categoria"].empty_label = "Selecione uma categoria"

        # RNF-010: mensagem de erro que diz qual campo está errado e como
        # corrigir. `required` cobre o CU10 E1 de campo obrigatório ausente.
        self.fields["nome"].error_messages["required"] = "Informe o nome do produto ou serviço."
        self.fields["id_categoria"].error_messages["required"] = "Selecione a categoria de insumo."
        self.fields["preco"].error_messages["required"] = "Informe o preço unitário."

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if len(nome) < 2:
            raise forms.ValidationError("Informe o nome do produto ou serviço.")
        return nome

    def clean_preco(self):
        """
        O banco.sql define `preco` como DECIMAL(10,2) NOT NULL: preço zerado ou
        negativo não faz sentido para um insumo ofertado, então é recusado aqui
        com mensagem explicativa (RNF-010).
        """
        preco = self.cleaned_data.get("preco")
        if preco is not None and preco <= 0:
            raise forms.ValidationError("Informe um preço maior que zero, ex.: 12,90.")
        return preco

    def clean(self):
        cleaned_data = super().clean()
        # CU10 (passo 6): dados de contato para negociação = telefone e/ou
        # WhatsApp, ao menos um deles.
        if not self.errors.get("telefone_contato") and not self.errors.get("whatsapp_contato"):
            if not cleaned_data.get("telefone_contato") and not cleaned_data.get("whatsapp_contato"):
                self.add_error(
                    "telefone_contato",
                    "Informe ao menos um contato para negociação: telefone ou WhatsApp.",
                )
        return cleaned_data