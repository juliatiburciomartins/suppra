"""
Formulários de avaliação e de favoritos (RF-018 / RF-029, CU09, CU08).

O RF-018 define a avaliação como "estrelas de 0 a 5, onde 0 representa a pior
avaliação e 5 a melhor", com comentário opcional. O banco.sql guarda a nota em
`nota TINYINT(4) NOT NULL` — a faixa 0..5 é garantida aqui, porque o ENUM/CHECK
do banco não existe e uma nota 7 passaria a ser gravada.

A denúncia é do app `moderacao` (RF-025), não deste.
"""

from django import forms

from avaliacoes.models import Avaliacao


class AvaliacaoForm(forms.ModelForm):
    """
    Registrar ou editar a avaliação de um fornecedor.

    `nota` vira ChoiceField de 0 a 5 (as estrelas do
    `templates/componentes/estrelas.html`), e não um input numérico solto: o
    usuário escolhe por clique e o valor gravado já vem validado.
    """

    NOTA_CHOICES = [(n, f"{n} {'estrela' if n == 1 else 'estrelas'}") for n in range(0, 6)]

    nota = forms.TypedChoiceField(
        choices=NOTA_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        label="Sua nota",
        error_messages={"required": "Escolha uma nota de 0 a 5 estrelas."},
    )

    class Meta:
        model = Avaliacao
        fields = ["nota", "comentario"]
        widgets = {
            "comentario": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Conte como foi sua experiência com este fornecedor (opcional).",
                }
            ),
        }
        labels = {
            "nota": "Sua nota",
            "comentario": "Comentário (opcional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nota"].widget.attrs = {"class": "stars-field__opcoes"}
        self.fields["comentario"].required = False

    def clean_comentario(self):
        return (self.cleaned_data.get("comentario") or "").strip() or None

    def clean_nota(self):
        """Barreira final da faixa 0..5, independente de como chegou o valor."""
        nota = self.cleaned_data.get("nota")
        if nota is None or not 0 <= nota <= 5:
            raise forms.ValidationError("Escolha uma nota de 0 a 5 estrelas.")
        return nota