from django import forms
from django.contrib.auth.hashers import make_password

from usuarios.models import Usuario


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
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    def clean_cpf_cnpj(self):
        cpf_cnpj = self.cleaned_data["cpf_cnpj"].strip()
        if Usuario.objects.filter(cpf_cnpj=cpf_cnpj).exists():
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
        usuario.senha = make_password(self.cleaned_data["senha"])
        if commit:
            usuario.save()
        return usuario


class EditarPerfilForm(forms.ModelForm):
    """
    Edição de perfil (RF-003). O e-mail é somente leitura no template
    (renderizado fora deste form), então não faz parte dos campos aqui.
    """

    class Meta:
        model = Usuario
        fields = ["nome", "cpf_cnpj", "telefone", "whatsapp"]

    def clean_cpf_cnpj(self):
        cpf_cnpj = self.cleaned_data["cpf_cnpj"].strip()
        if Usuario.objects.filter(cpf_cnpj=cpf_cnpj).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este CPF/CNPJ.")
        return cpf_cnpj
