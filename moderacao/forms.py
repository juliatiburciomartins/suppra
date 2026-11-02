"""
Formulários de denúncia (RF-025 / CU14).

O RF-025 define o formulário como: "um campo de texto descritivo (onde descreve
o ocorrido) e um campo opcional para anexo de imagem como evidência".

O banco.sql guarda `evidencia VARCHAR(500)`, ou seja, o **caminho** do arquivo
enviado, não os bytes — quem faz o upload é a própria view (ver
`moderacao/views.py`). Por isso o campo é `FileField` com `required=False`:
é opcional no RF-025, mas obrigatório avisar quando vier arquivo inválido.
"""

from django import forms
from django.core.exceptions import ValidationError

from moderacao.models import Denuncia

# Limite do anexo. O banco guarda só o caminho (VARCHAR(500)); o tamanho é uma
# decisão de usabilidade da própria aplicação.
TAMANHO_MAXIMO_EVIDENCIA = 5 * 1024 * 1024  # 5 MiB
TIPOS_EVIDENCIA = ["jpg", "jpeg", "png", "webp", "gif"]


class DenunciaForm(forms.ModelForm):
    """
    Formulário de denúncia de conteúdo (portfólio ou demanda).

    - `descricao` é obrigatória (CU14, fluxo de exceção E1: campo vazio não
      permite envio);
    - `evidencia` é opcional, com validação de tipo para não subir arquivo
      executável ou giganticamente grande;
    - `id_produto`/`id_demanda` **não** são campos do formulário: a view os
      recebe por POST e valida qual deles combina com `tipo_conteudo`, porque o
      banco.sql não tem CHECK tying os dois (só o ENUM `tipo_conteudo`).
    """

    evidencia = forms.ImageField(
        required=False,
        label="Imagem de evidência (opcional)",
        help_text="PNG, JPG, WEBP ou GIF, até 5 MB.",
        error_messages={
            "invalid_image": "Envie uma imagem válida (PNG, JPG, WEBP ou GIF).",
            "invalid_extension": "Formato não aceito. Envie PNG, JPG, WEBP ou GIF.",
        },
    )

    class Meta:
        model = Denuncia
        fields = ["descricao", "evidencia"]
        widgets = {
            "descricao": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Descreva o que aconteceu neste conteúdo.",
                }
            ),
            "evidencia": forms.ClearableFileInput(
                attrs={"accept": ".jpg,.jpeg,.png,.webp,.gif"}
            ),
        }
        labels = {
            "descricao": "Descrição do ocorrido",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["descricao"].error_messages["required"] = (
            "A descrição é obrigatória para o envio da denúncia."
        )

    def clean_descricao(self):
        descricao = (self.cleaned_data.get("descricao") or "").strip()
        if len(descricao) < 10:
            raise ValidationError(
                "Descreva o ocorrido com pelo menos 10 caracteres, para que a "
                "equipe consiga analisar."
            )
        return descricao

    def clean_evidencia(self):
        evidencia = self.cleaned_data.get("evidencia")

        if not evidencia:
            return None  # opcional (RF-025)

        if evidencia.size > TAMANHO_MAXIMO_EVIDENCIA:
            raise ValidationError(
                "A imagem excede 5 MB. Envie uma imagem menor."
            )

        return evidencia