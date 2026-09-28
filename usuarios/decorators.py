"""
Controle de acesso por perfil (RF-004, RNF-006).

Decorators para views baseadas em função:

    from usuarios.decorators import (
        login_usuario_requerido, comerciante_required, fornecedor_required, admin_required,
    )

    @fornecedor_required
    def gerenciar_portfolio(request): ...

Regras (mesma lógica usada pelos mixins em `usuarios/mixins.py`):

  - visitante (não autenticado)  -> redireciona para o login (?next=...) com mensagem;
  - perfil errado (ex.: comerciante numa view de fornecedor) -> redireciona para o
    painel do próprio perfil com mensagem de erro;
  - `admin_required` (equipe gestora, ver Usuario.is_admin) -> visitante vai para o
    login; usuário comum recebe HTTP 403.

`perfil_required(..., raise_exception=True)` devolve HTTP 403 em vez de redirecionar.

`request.user` vem do AuthenticationMiddleware padrão do Django (AUTH_USER_MODEL =
usuarios.Usuario). Contas suspensas/excluídas já chegam como AnonymousUser.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

MSG_LOGIN = "Faça login para acessar esta página."
MSG_FORNECEDOR = "Esta área é exclusiva para fornecedores."
MSG_COMERCIANTE = "Esta área é exclusiva para comerciantes."
MSG_ADMIN = "Você não tem permissão para acessar esta área."

_MENSAGENS_PERFIL = {
    "fornecedor": MSG_FORNECEDOR,
    "comerciante": MSG_COMERCIANTE,
}


def url_painel(usuario):
    """Nome da URL do painel do perfil do usuário."""
    return "dashboard_fornecedor" if usuario.tipo_perfil == "fornecedor" else "dashboard_comerciante"


def verificar_acesso(request, perfis=None, exigir_admin=False, raise_exception=False):
    """
    Retorna None se o acesso é permitido; senão, um HttpResponse de negação
    (redirect com mensagem) ou levanta PermissionDenied (HTTP 403).
    """
    user = request.user

    if not user.is_authenticated:
        messages.warning(request, MSG_LOGIN)
        return redirect_to_login(request.get_full_path())

    if exigir_admin:
        if not getattr(user, "is_admin", False):
            raise PermissionDenied(MSG_ADMIN)
        return None

    if perfis and user.tipo_perfil not in perfis:
        if raise_exception:
            raise PermissionDenied(_MENSAGENS_PERFIL.get(perfis[0], MSG_ADMIN))
        messages.error(request, _MENSAGENS_PERFIL.get(perfis[0], MSG_ADMIN))
        return redirect(url_painel(user))

    return None


def perfil_required(*perfis, raise_exception=False):
    """Exige usuário autenticado com `tipo_perfil` em `perfis`. Sem perfis: qualquer autenticado."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            negado = verificar_acesso(request, perfis=perfis, raise_exception=raise_exception)
            if negado is not None:
                return negado
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(view_func):
    """Exige administrador (equipe gestora). Visitante -> login; usuário comum -> HTTP 403."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        negado = verificar_acesso(request, exigir_admin=True)
        if negado is not None:
            return negado
        return view_func(request, *args, **kwargs)

    return wrapper


# Qualquer usuário autenticado (fornecedor ou comerciante).
login_usuario_requerido = perfil_required()
comerciante_required = perfil_required("comerciante")
fornecedor_required = perfil_required("fornecedor")

# Nomes anteriores, mantidos para não quebrar as views já existentes.
comerciante_logado = comerciante_required
fornecedor_logado = fornecedor_required
