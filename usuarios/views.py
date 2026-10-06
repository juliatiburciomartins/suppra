from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode
from portfolio.models import Produto
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from core.services import registrar_log
from usuarios.decorators import (
    comerciante_required,
    fornecedor_required,
    login_usuario_requerido,
    url_painel,
)
from usuarios.forms import CadastroForm, EditarPerfilForm
from usuarios.models import Usuario
from usuarios.services import anonimizar_usuario

AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _url_dashboard(usuario):
    return url_painel(usuario)


password_reset_token_generator = default_token_generator


# --------------------------------------------------------------------------
# Login / Cadastro / Logout
# --------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect(_url_dashboard(request.user))

    if request.method == "POST":
        email = request.POST.get("username", "").strip()
        senha = request.POST.get("password", "")
        field_errors = {}
        usuario = Usuario.objects.filter(email__iexact=email).first()

        # check_password é sempre False para conta excluída (senha inutilizável, RF-016)
        if not usuario or not usuario.check_password(senha):
            field_errors["password"] = ["E-mail ou senha inválidos."]
            return render(request, "registration/login.html", {"field_errors": field_errors})

        # Conta suspensa (moderação) ou excluída não faz login.
        if not usuario.is_active:
            return render(request, "registration/login.html", {"conta_suspensa": True})

        login(request, usuario, backend=AUTH_BACKEND)
        messages.success(request, f"Bem-vindo(a) de volta, {usuario.nome}!")

        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect(_url_dashboard(usuario))

    return render(request, "registration/login.html")


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect(_url_dashboard(request.user))

    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario, backend=AUTH_BACKEND)
            messages.success(request, "Conta criada com sucesso! Bem-vindo(a) ao hub_fecc.")
            return redirect(_url_dashboard(usuario))
    else:
        form = CadastroForm()

    return render(request, "usuarios/cadastro.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect("home")


# --------------------------------------------------------------------------
# Recuperação de senha (RF-023)
# --------------------------------------------------------------------------

def recuperar_senha_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario and usuario.is_active:
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = password_reset_token_generator.make_token(usuario)
            link = request.build_absolute_uri(reverse("redefinir_senha", kwargs={"uidb64": uid, "token": token}))
            mensagem = f"Olá, {usuario.nome}.\n\nRecebemos uma solicitação para redefinir sua senha no hub_fecc.\n\nAcesse o link abaixo para criar uma nova senha:\n{link}\n\nSe você não solicitou a recuperação, ignore este e-mail."
            send_mail("Recuperação de senha - hub_fecc", mensagem, settings.DEFAULT_FROM_EMAIL, [usuario.email], fail_silently=True)

        messages.info(request, "Se o e-mail estiver cadastrado, um link foi enviado.")
        return redirect("recuperar_senha_enviado")

    return render(request, "registration/password_reset_form.html")


def redefinicao_senha_enviado_view(request):
    return render(request, "registration/password_reset_done.html")


def redefinir_senha_view(request, uidb64, token):
    try:
        usuario = Usuario.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None

    if not usuario or not usuario.is_active or not password_reset_token_generator.check_token(usuario, token):
        return render(request, "registration/password_reset_confirm.html", {"validlink": False})

    if request.method == "POST":
        senha1 = request.POST.get("new_password1", "")
        senha2 = request.POST.get("new_password2", "")

        if not senha1 or not senha2:
            return render(request, "registration/password_reset_confirm.html", {"validlink": True, "erro_senha": "Preencha os dois campos de senha."})

        if senha1 != senha2:
            return render(request, "registration/password_reset_confirm.html", {"validlink": True, "erro_senha": "As novas senhas não coincidem. Preencha os campos novamente."})

        usuario.set_password(senha1)  # RNF-002
        usuario.save(update_fields=["password"])
        messages.success(request, "Sua senha foi redefinida com sucesso.")
        return redirect("password_reset_complete")

    return render(request, "registration/password_reset_confirm.html", {"validlink": True})



def redefinicao_senha_concluida_view(request):
    return render(request, "registration/password_reset_complete.html")


def redefinir_senha_preview_view(request):
    return render(request, "registration/password_reset_confirm.html", {"validlink": True})

def link_expirado_view(request):
    return render(request, "registration/password_reset_confirm.html", {"validlink": False})


# --------------------------------------------------------------------------
# Dashboards
# --------------------------------------------------------------------------

@fornecedor_required
def dashboard_fornecedor_view(request):
    produtos = Produto.objects.filter(id_fornecedor=request.user).select_related("id_categoria")
    return render(request, "usuarios/dashboard_fornecedor.html", {
        "tipo_menu": "fornecedor",
        "produtos": produtos,
        "total_produtos": produtos.count(),
        "produtos_ativos": produtos.filter(status="ativo").count(),
        "plano_nome": "Grátis",
    })


@comerciante_required
def dashboard_comerciante_view(request):
    from avaliacoes.models import Favorito
    from demandas.models import Demanda

    demandas_qs = Demanda.objects.filter(id_comerciante=request.user).select_related("id_categoria")

    return render(request, "usuarios/dashboard_comerciante.html", {
        "tipo_menu": "comerciante",
        "total_demandas": demandas_qs.count(),
        "demandas_recentes": demandas_qs.order_by("-data_publicacao")[:5],
        "total_favoritos": Favorito.objects.filter(id_comerciante=request.user).count(),
        "total_fornecedores": Usuario.objects.filter(tipo_perfil="fornecedor").count(),
    })


# --------------------------------------------------------------------------
# Perfil e conta (CU16 / RF-026 e CU15 / RF-016)
# --------------------------------------------------------------------------

@login_usuario_requerido
def editar_perfil_view(request):
    """CU16 — Editar dados cadastrais. E-mail somente leitura; A1 = descartar; E1 = erro por campo."""
    # Instância "fresca": um POST inválido não deve alterar o request.user em memória
    # (senão o menu/cabeçalho mostraria dados ainda não salvos).
    usuario = Usuario.objects.get(pk=request.user.pk)
    tipo_menu = usuario.tipo_perfil

    if request.method == "POST":
        if "descartar" in request.POST:  # A1: volta aos dados originais sem salvar
            messages.info(request, "Alterações descartadas. Seus dados cadastrais não foram modificados.")
            return redirect("editar_perfil")

        form = EditarPerfilForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Dados cadastrais atualizados com sucesso.")
            return redirect("editar_perfil")
    else:
        form = EditarPerfilForm(instance=usuario)

    return render(request, "usuarios/editar_perfil.html", {"form": form, "tipo_menu": tipo_menu})


@login_usuario_requerido
def excluir_conta_view(request):
    """
    CU15 — Excluir minha conta (RF-016).

    Não faz DELETE em `usuario` (FKs de produto/demanda/avaliação/assinatura...):
    soft delete por anonimização + status_conta='suspensa' (ver usuarios/services.py).
    Login bloqueado, sessão encerrada e redirecionamento para a home.
    """
    usuario = request.user
    tipo_menu = usuario.tipo_perfil

    if request.method == "POST":
        senha = request.POST.get("senha", "")

        if not usuario.check_password(senha):  # E1: senha incorreta, nada é excluído
            return render(request, "usuarios/excluir_conta.html", {
                "tipo_menu": tipo_menu,
                "erro_senha": "Senha incorreta. Sua conta não foi excluída.",
            })

        # Sem e-mail/CPF no log: os dados pessoais devem sair do sistema (LGPD).
        registrar_log(
            usuario=usuario,
            acao="UPDATE",
            modelo_afetado="Usuario",
            id_registro_afetado=usuario.pk,
            conteudo_anterior="Exclusão de conta solicitada pelo titular (soft delete: dados pessoais anonimizados e login bloqueado).",
        )

        anonimizar_usuario(usuario)
        logout(request)
        messages.success(request, "Sua conta foi excluída e seus dados pessoais foram anonimizados.")
        return redirect("home")

    return render(request, "usuarios/excluir_conta.html", {"tipo_menu": tipo_menu})
