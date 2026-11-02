"""
Fluxo de recuperação de senha por e-mail (RF-023 / CU03).

Centralizado aqui porque o mesmo par "gerar token -> montar link -> enviar
e-mail" é usado tanto pelo visitante comum (view `recuperar_senha_view`) quanto
por qualquer ponto do painel que precise reenviar o link. A view fica só com
HTML e mensagens.

Segurança (RNF-002/RNF-003):
  - o token é o `default_token_generator` do Django (hash do pk, do timestamp e
    da senha com PBKDF2/SHA256): é de uso único e expira sozinho;
  - o link carrega o pk em base64 apenas para localizar o usuário — nunca a
    senha;
  - o e-mail nunca confirma se o endereço existe (fluxo principal, passo 7 do
    CU03), para não vazar cadastro.

As mensagens do CU03 E1 (token já usado) e E2 (expirado) são a mesma na tela:
"link inválido ou já foi usado" — não revelamos qual dos dois foi.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from usuarios.models import Usuario

# Endpoint que valida o token e mostra o formulário de nova senha.
URL_REDEFINICAO = "redefinir_senha"

ASSUNTO = "Recuperação de senha - suppra"

# Par do CU03, passo 7: resposta neutra, vale para e-mail cadastrado ou não.
MENSAGEM_NEUTRA = (
    "Se o e-mail estiver cadastrado, um link foi enviado. "
    "Confira também a pasta de spam."
)


def gerar_uid(usuario):
    """Pk do usuário codificado em base64, como manda o padrão do Django."""
    return urlsafe_base64_encode(force_bytes(usuario.pk))


def montar_link(request, usuario):
    """Link absoluto de redefinição, já com uid e token de uso único."""
    uid = gerar_uid(usuario)
    token = default_token_generator.make_token(usuario)
    caminho = reverse(URL_REDEFINICAO, kwargs={"uidb64": uid, "token": token})
    return request.build_absolute_uri(caminho)


def usuario_por_uid(uidb64):
    """Devolve o Usuario do uidb64, ou None se o base64 estiver corrompido."""
    try:
        pk = force_str(urlsafe_base64_decode(uidb64))
        return Usuario.objects.get(pk=pk)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        return None


def token_valido(usuario, token):
    """True se o token pertence ao usuário e ainda não expirou/não foi usado."""
    if usuario is None:
        return False
    return default_token_generator.check_token(usuario, token)


def enviar_link_recuperacao(request, usuario):
    """
    Gera o token, monta o link e envia o e-mail.

    Devolve True se o e-mail foi despachado. `fail_silently=True` mantém a tela
    de resposta neutra mesmo com SMTP fora do ar (em desenvolvimento o
    `settings.py` já usa o backend de console, que imprime o link no terminal).
    """
    link = montar_link(request, usuario)
    contexto = {
        "usuario": usuario,
        "link": link,
        "expira_em_horas": 24,
        "projeto": "suppra",
    }

    corpo_html = render_to_string(
        "registration/emails/password_reset_email.html", contexto
    )
    corpo_texto = (
        f"Olá, {usuario.nome}.\n\n"
        "Recebemos uma solicitação para redefinir sua senha no suppra.\n\n"
        "Acesse o link abaixo para criar uma nova senha:\n"
        f"{link}\n\n"
        "O link é de uso único e expira em 24 horas.\n"
        "Se você não solicitou a recuperação, ignore este e-mail.\n"
    )

    return send_mail(
        ASSUNTO,
        corpo_texto,
        settings.DEFAULT_FROM_EMAIL,
        [usuario.email],
        html_message=corpo_html,
        fail_silently=True,
    )


def conta_pode_receber_link(usuario):
    """
    Só conta ativa recebe link.

    Conta suspensa pela moderação (RF-025) ou já excluída/anonimizada (RF-016)
    não tem mais um e-mail real de titular, então o fluxo termina em "solicitado"
    sem enviar nada — mesma resposta neutra para o usuário (CU02 E2 manda
    orientar o contato com o suporte, tratado na view de login).
    """
    return bool(usuario and usuario.is_active and not usuario.conta_excluida)