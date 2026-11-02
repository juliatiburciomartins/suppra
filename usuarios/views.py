from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import url_has_allowed_host_and_scheme
from portfolio.models import Produto

from core.services import registrar_log
from usuarios.onboarding import (
    ja_visualizou,
    registrar_conclusao,
    registrar_ignoracao,
    situacao,
)
from usuarios.decorators import (
    comerciante_required,
    fornecedor_required,
    login_usuario_requerido,
    url_painel,
)
from usuarios.forms import CadastroForm, EditarPerfilForm
from usuarios.models import Usuario
from usuarios.password_reset import (
    MENSAGEM_NEUTRA,
    conta_pode_receber_link,
    enviar_link_recuperacao,
    token_valido,
    usuario_por_uid,
)
from usuarios.services import anonimizar_usuario

AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _url_dashboard(usuario):
    return url_painel(usuario)


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
            messages.success(request, "Conta criada com sucesso! Bem-vindo(a) ao suppra.")

            # CU01, pós-condição: "o usuário é redirecionado para o tutorial de
            # onboarding e, em seguida, para o painel correspondente ao seu perfil".
            if not ja_visualizou(request, usuario):
                return redirect("tutorial")
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

        # Resposta sempre neutra (CU03, passo 7): não revelamos se o e-mail
        # existe. Só conta ativa e não anonimizada recebe link.
        if conta_pode_receber_link(usuario):
            enviar_link_recuperacao(request, usuario)

        messages.info(request, MENSAGEM_NEUTRA)
        return redirect("recuperar_senha_enviado")

    return render(request, "registration/password_reset_form.html")


def redefinicao_senha_enviado_view(request):
    return render(request, "registration/password_reset_done.html")


def redefinir_senha_view(request, uidb64, token):
    usuario = usuario_por_uid(uidb64)

    # CU03 E1 (token já usado) e E2 (expirado): mesma tela, sem dizer qual foi.
    if not token_valido(usuario, token):
        return render(request, "registration/password_reset_confirm.html", {"validlink": False})

    if request.method == "POST":
        senha1 = request.POST.get("new_password1", "")
        senha2 = request.POST.get("new_password2", "")

        if not senha1 or not senha2:
            return render(request, "registration/password_reset_confirm.html", {
                "validlink": True,
                "erro_senha": "Preencha os dois campos de senha.",
            })

        # CU03 E3: as senhas não coincidem -> destaca o erro e pede de novo.
        if senha1 != senha2:
            return render(request, "registration/password_reset_confirm.html", {
                "validlink": True,
                "erro_senha": "As novas senhas não coincidem. Preencha os campos novamente.",
            })

        try:
            validate_password(senha1, user=usuario)
        except ValidationError as erro:
            return render(request, "registration/password_reset_confirm.html", {
                "validlink": True,
                "erro_senha": " ".join(erro.messages),
            })

        usuario.set_password(senha1)  # RNF-002
        # Grava `senha` (coluna do banco.sql) e invalida o token usado, porque
        # o hash da senha entra no cálculo do token.
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
    from assinaturas.services import assinatura_em_vigor, expirar_vencidas

    expirar_vencidas()

    produtos = Produto.objects.filter(id_fornecedor=request.user).select_related("id_categoria")
    assinatura = assinatura_em_vigor(request.user)

    return render(request, "usuarios/dashboard_fornecedor.html", {
        "tipo_menu": "fornecedor",
        "produtos": produtos,
        "total_produtos": produtos.count(),
        "produtos_ativos": produtos.filter(status="ativo").count(),
        # RF-020/RF-022: o selo mostra o plano contratado; sem assinatura em
        # vigor o fornecedor está no plano gratuito.
        "assinatura": assinatura,
        "plano_nome": assinatura.id_plano.nome_plano if assinatura else "Grátis",
        "plano_nivel": assinatura.id_plano.nivel if assinatura else None,
    })


@comerciante_required
def dashboard_comerciante_view(request):
    from avaliacoes.models import Favorito
    from demandas.models import Demanda

    demandas_qs = Demanda.objects.filter(id_comerciante=request.user).select_related("id_categoria")

    return render(request, "usuarios/dashboard_comerciante.html", {
        "tipo_menu": "comerciante",
        "total_demandas": demandas_qs.count(),
        "demandas_publicadas": demandas_qs.filter(status="publicada").count(),
        "demandas_recentes": demandas_qs.order_by("-data_publicacao")[:5],
        "total_favoritos": Favorito.objects.filter(id_comerciante=request.user).count(),
        "total_fornecedores": Usuario.objects.filter(
            tipo_perfil="fornecedor", status_conta="ativa"
        ).count(),
    })


# --------------------------------------------------------------------------
# RF-014 / CU17 — Tutorial de onboarding
# --------------------------------------------------------------------------

@login_usuario_requerido
def tutorial_view(request):
    """
    Tutorial interativo de onboarding (RF-014 / CU17).

    Fica acessível por dois caminhos, como o CU17 descreve na pré-condição:

    1. **automático**, logo após o cadastro (`cadastro_view` redireciona aqui);
    2. **voluntário**, quando o usuário acessa o endereço de novo a partir do
       painel.

    No POST (botão "Concluir"), registra a conclusão e vai para o painel do
    perfil. O botão de pular registra a *ignição* (CU17 A1) — por isso ele também
    precisa ser POST; se fosse um link GET, o estado nunca seria gravado.
    """
    if request.method == "POST":
        registrar_conclusao(request, request.user)
        messages.success(request, "Tutorial concluído. Bons negócios!")
        return redirect(_url_dashboard(request.user))

    return render(
        request,
        "usuarios/tutorial.html",
        {"tipo_menu": request.user.tipo_perfil},
    )


@login_usuario_requerido
def pular_tutorial_view(request):
    """
    CU17, fluxo alternativo A1 — "Em qualquer etapa do tutorial, o usuário opta
    por pular o onboarding": registra a ignição e redireciona para o painel.

    Só por POST. A decisão precisa ser explícita e com token CSRF; aceitar GET
    permitiria que um link colado no chat de alguém pulasse o tutorial dele sem
    ele ter clicado em nada.
    """
    if request.method != "POST":
        return redirect("tutorial")

    registrar_ignoracao(request, request.user)
    messages.info(request, "Tutorial pulado. Você pode vê-lo de novo quando quiser.")
    return redirect(_url_dashboard(request.user))


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

    return render(
        request,
        "usuarios/editar_perfil.html",
        {
            "form": form,
            "tipo_menu": tipo_menu,
            # CU17: a pré-condição permite acessar o tutorial voluntariamente.
            "situacao_tutorial": situacao(request, usuario),
        },
    )


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
