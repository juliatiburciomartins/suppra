from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from portfolio.models import Produto

from core.services import registrar_log
from usuarios.decorators import (
    SESSION_KEY_USUARIO_ID,
    comerciante_logado,
    fornecedor_logado,
    login_usuario_requerido,
)
from usuarios.forms import CadastroForm, EditarPerfilForm
from usuarios.models import Usuario
from usuarios.services import anonimizar_usuario


def _url_dashboard(usuario):
    return "dashboard_fornecedor" if usuario.tipo_perfil == "fornecedor" else "dashboard_comerciante"


class UsuarioPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.senha}{timestamp}"


password_reset_token_generator = UsuarioPasswordResetTokenGenerator()


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

        if not usuario or not check_password(senha, usuario.senha):
            field_errors["password"] = ["E-mail ou senha inválidos."]
            return render(request, "registration/login.html", {"field_errors": field_errors})

        if usuario.status_conta == "suspensa":
            return render(request, "registration/login.html", {"conta_suspensa": True})

        request.session[SESSION_KEY_USUARIO_ID] = usuario.pk
        messages.success(request, f"Bem-vindo(a) de volta, {usuario.nome}!")

        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url:
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
            request.session[SESSION_KEY_USUARIO_ID] = usuario.pk
            messages.success(request, "Conta criada com sucesso! Bem-vindo(a) ao hub_fecc.")
            return redirect(_url_dashboard(usuario))
    else:
        form = CadastroForm()

    return render(request, "usuarios/cadastro.html", {"form": form})


def logout_view(request):
    request.session.pop(SESSION_KEY_USUARIO_ID, None)
    messages.info(request, "Você saiu da sua conta.")
    return redirect("home")


# --------------------------------------------------------------------------
# Recuperação de senha (RF-023)
# --------------------------------------------------------------------------

def recuperar_senha_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario:
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

    if not usuario or not password_reset_token_generator.check_token(usuario, token):
        return render(request, "registration/password_reset_confirm.html", {"validlink": False})

    if request.method == "POST":
        senha1 = request.POST.get("new_password1", "")
        senha2 = request.POST.get("new_password2", "")

        if not senha1 or not senha2:
            return render(request, "registration/password_reset_confirm.html", {"validlink": True, "erro_senha": "Preencha os dois campos de senha."})

        if senha1 != senha2:
            return render(request, "registration/password_reset_confirm.html", {"validlink": True, "erro_senha": "As novas senhas não coincidem. Preencha os campos novamente."})

        usuario.senha = make_password(senha1)
        usuario.save(update_fields=["senha"])
        messages.success(request, "Sua senha foi redefinida com sucesso.")
        return redirect("password_reset_complete")

    return render(request, "registration/password_reset_confirm.html", {"validlink": True})


def redefinicao_senha_concluida_view(request):
    return render(request, "registration/password_reset_complete.html")


# --------------------------------------------------------------------------
# Dashboards
# --------------------------------------------------------------------------

@fornecedor_logado
def dashboard_fornecedor_view(request):
    produtos = Produto.objects.filter(id_fornecedor=request.user).select_related("id_categoria")
    return render(request, "usuarios/dashboard_fornecedor.html", {
        "tipo_menu": "fornecedor",
        "produtos": produtos,
        "total_produtos": produtos.count(),
        "produtos_ativos": produtos.filter(status="ativo").count(),
        "plano_nome": "Grátis",
    })


@comerciante_logado
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
# Perfil (RF-003 / RF-016)
# --------------------------------------------------------------------------

@login_usuario_requerido
def editar_perfil_view(request):
    tipo_menu = request.user.tipo_perfil

    if request.method == "POST":
        form = EditarPerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso.")
            return redirect("editar_perfil")
    else:
        form = EditarPerfilForm(instance=request.user)

    return render(request, "usuarios/editar_perfil.html", {"form": form, "tipo_menu": tipo_menu})


@login_usuario_requerido
def excluir_conta_view(request):
    tipo_menu = request.user.tipo_perfil

    if request.method == "POST":
        senha = request.POST.get("senha", "")

        if not check_password(senha, request.user.senha):
            messages.error(request, "Senha incorreta. A conta não foi excluída.")
            return render(request, "usuarios/excluir_conta.html", {"tipo_menu": tipo_menu})

        usuario = request.user
        usuario_id = usuario.pk

        registrar_log(
            usuario=usuario,
            acao="UPDATE",
            modelo_afetado="Usuario",
            id_registro_afetado=usuario_id,
            conteudo_anterior=f"Exclusão de conta solicitada pelo titular (email original: {usuario.email}).",
        )

        anonimizar_usuario(usuario)
        request.session.pop(SESSION_KEY_USUARIO_ID, None)
        messages.success(request, "Sua conta foi excluída e seus dados pessoais foram anonimizados.")
        return redirect("home")

    return render(request, "usuarios/excluir_conta.html", {"tipo_menu": tipo_menu})