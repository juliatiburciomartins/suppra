import re

from django import forms
from django.conf import settings

from usuarios.models import Usuario


def _somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def normalizar_cpf_cnpj(valor):
    """
    Valida o formato (CPF = 11 dígitos, CNPJ = 14) e devolve o valor com máscara
    (000.000.000-00 / 00.000.000/0000-00), que cabe no VARCHAR(18) do banco.sql.
    """
    digitos = _somente_digitos(valor)
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    if len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    raise forms.ValidationError(
        "CPF/CNPJ inválido. Informe 11 dígitos (CPF) ou 14 dígitos (CNPJ)."
    )


def cpf_cnpj_em_uso(valor_normalizado, excluir_pk=None):
    """Compara com e sem máscara, pois cadastros antigos podem ter sido gravados sem ela."""
    qs = Usuario.objects.filter(
        cpf_cnpj__in={valor_normalizado, _somente_digitos(valor_normalizado)}
    )
    if excluir_pk is not None:
        qs = qs.exclude(pk=excluir_pk)
    return qs.exists()


def validar_telefone(valor, rotulo):
    """Telefone/WhatsApp opcionais individualmente; se preenchidos, 10 a 13 dígitos (DDD, com ou sem +55)."""
    valor = (valor or "").strip()
    if not valor:
        return None
    if not 10 <= len(_somente_digitos(valor)) <= 13:
        raise forms.ValidationError(f"{rotulo} inválido. Informe o DDD e o número, ex.: (19) 99999-9999.")
    return valor


class CadastroForm(forms.ModelForm):
    """
    Cadastro de novo Usuario (RF-001/RF-002).

    A ordem dos campos aqui é a mesma ordem em que `usuarios/cadastro.html`
    renderiza via `{% for field in form %}` (que pula 'aceite_termos' do
    loop e o renderiza manualmente no fim, junto do checkbox de termos).
    """

    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo de 8 caracteres"}),
        min_length=8,
    )
    confirmar_senha = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"placeholder": "Repita a senha"}),
    )
    aceite_termos = forms.BooleanField(
        label="Aceito os Termos de Uso e a Política de Privacidade",
        required=True,
        error_messages={"required": "É preciso aceitar os Termos de Uso e a Política de Privacidade."},
    )

    class Meta:
        model = Usuario
        fields = [
            "nome",
            "email",
            "senha",
            "confirmar_senha",
            "cpf_cnpj",
            "telefone",
            "whatsapp",
            "tipo_perfil",
        ]
        widgets = {
            "tipo_perfil": forms.Select(),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email in settings.ADMIN_EMAILS:
            # e-mails da equipe gestora não podem ser registrados pelo cadastro público
            raise forms.ValidationError("Este e-mail não está disponível para cadastro.")
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    def clean_cpf_cnpj(self):
        cpf_cnpj = normalizar_cpf_cnpj(self.cleaned_data["cpf_cnpj"])
        if cpf_cnpj_em_uso(cpf_cnpj):
            raise forms.ValidationError("Já existe uma conta cadastrada com este CPF/CNPJ.")
        return cpf_cnpj

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")
        if senha and confirmar_senha and senha != confirmar_senha:
            self.add_error("confirmar_senha", "As senhas não coincidem.")
        return cleaned_data

    def save(self, commit=True):
        # RNF-002: a senha nunca é gravada em texto puro.
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["senha"])
        if commit:
            usuario.save()
        return usuario


class EditarPerfilForm(forms.ModelForm):
    """
    Edição de dados cadastrais (CU16 / RF-026).

    Editáveis: nome/razão social, CNPJ/CPF, telefone e/ou WhatsApp.
    O e-mail de acesso é exibido apenas para consulta: o campo é `disabled`,
    então o Django ignora qualquer valor enviado no POST (não dá para alterá-lo
    nem adulterando a requisição).

    Erros (E1) são levantados por campo, para o template destacar cada um.
    """

    class Meta:
        model = Usuario
        fields = ["nome", "email", "cpf_cnpj", "telefone", "whatsapp"]
        labels = {
            "nome": "Nome / Razão social",
            "email": "E-mail",
            "cpf_cnpj": "CPF / CNPJ",
            "telefone": "Telefone",
            "whatsapp": "WhatsApp",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].disabled = True
        self.fields["email"].widget.attrs["readonly"] = True
        self.fields["nome"].error_messages["required"] = "Informe o nome ou a razão social."
        self.fields["cpf_cnpj"].error_messages["required"] = "Informe o CPF ou CNPJ."
        self.fields["telefone"].widget.attrs["placeholder"] = "(19) 3333-3333"
        self.fields["whatsapp"].widget.attrs["placeholder"] = "(19) 99999-9999"

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if len(nome) < 2:
            raise forms.ValidationError("Informe o nome ou a razão social (mínimo de 2 caracteres).")
        return nome

    def clean_cpf_cnpj(self):
        cpf_cnpj = normalizar_cpf_cnpj(self.cleaned_data.get("cpf_cnpj"))
        if cpf_cnpj_em_uso(cpf_cnpj, excluir_pk=self.instance.pk):
            raise forms.ValidationError("Já existe uma conta cadastrada com este CPF/CNPJ.")
        return cpf_cnpj

    def clean_telefone(self):
        return validar_telefone(self.cleaned_data.get("telefone"), "Telefone")

    def clean_whatsapp(self):
        return validar_telefone(self.cleaned_data.get("whatsapp"), "WhatsApp")

    def clean(self):
        cleaned_data = super().clean()
        # RF-026: dados de contato = telefone e/ou WhatsApp (ao menos um)
        if not self.errors.get("telefone") and not self.errors.get("whatsapp"):
            if not cleaned_data.get("telefone") and not cleaned_data.get("whatsapp"):
                self.add_error("telefone", "Informe ao menos um contato: telefone ou WhatsApp.")
        return cleaned_data
