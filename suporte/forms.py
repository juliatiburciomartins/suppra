"""
Formulários de suporte interno (RF-019 / CU19).

O CU19, passo 2, define os campos: "assunto, descrição do problema ou dúvida e
campo opcional para anexo de evidência".

O banco.sql guarda `img VARCHAR(500)`, ou seja, o caminho do arquivo — o upload é
feito pela view (ver `suporte/views.py`), igual à evidência da denúncia
(`moderacao/forms.py`).
"""

from django import forms
from django.core.exceptions import ValidationError

from suporte.models import Suporte

TAMANHO_MAXIMO_EVIDENCIA = 5 * 1024 * 1024  # 5 MiB


class SuporteForm(forms.ModelForm):
    """
    Abertura de chamado de suporte (RF-019).

    - `assunto` e `descricao` são obrigatórios (CU19, fluxo de exceção E1);
    - `img` é opcional ("campo opcional para anexo de evidência").
    """

    img = forms.ImageField(
        required=False,
        label="Evidência (opcional)",
        help_text="PNG, JPG, WEBP ou GIF, até 5 MB.",
        error_messages={
            "invalid_image": "Envie uma imagem válida (PNG, JPG, WEBP ou GIF).",
            "invalid_extension": "Formato não aceito. Envie PNG, JPG, WEBP ou GIF.",
        },
    )

    class Meta:
        model = Suporte
        fields = ["assunto", "descricao", "img"]
        widgets = {
            "assunto": forms.TextInput(
                attrs={"placeholder": "Ex.: não consigo publicar uma demanda", "maxlength": 200}
            ),
            "descricao": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Descreva o problema ou a sua dúvida com o máximo de detalhes.",
                }
            ),
            "img": forms.ClearableFileInput(
                attrs={"accept": ".jpg,.jpeg,.png,.webp,.gif"}
            ),
        }
        labels = {
            "assunto": "Assunto",
            "descricao": "Descrição do problema ou dúvida",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # CU19 E1: os dois campos são obrigatórios, com mensagem que diz o que
        # fazer (RNF-010).
        self.fields["assunto"].error_messages["required"] = "Informe o assunto."
        self.fields["descricao"].error_messages["required"] = (
            "Descreva o problema ou dúvida."
        )

    def clean_assunto(self):
        assunto = (self.cleaned_data.get("assunto") or "").strip()
        if len(assunto) < 5:
            raise ValidationError("Informe um assunto com pelo menos 5 caracteres.")
        return assunto

    def clean_descricao(self):
        descricao = (self.cleaned_data.get("descricao") or "").strip()
        if len(descricao) < 15:
            raise ValidationError(
                "Descreva o problema com pelo menos 15 caracteres, para que a "
                "equipe consiga ajudar."
            )
        return descricao

    def clean_img(self):
        img = self.cleaned_data.get("img")

        if not img:
            return None  # opcional (RF-019)

        if img.size > TAMANHO_MAXIMO_EVIDENCIA:
            raise ValidationError("A imagem excede 5 MB. Envie uma imagem menor.")

        return img