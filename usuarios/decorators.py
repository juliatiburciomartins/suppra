"""
Contrato de sessão/autenticação do Hub FECC.

Isso fecha, de uma vez, o "combinado" que todo o resto do projeto (views
de portfólio, demandas, avaliações, assinaturas, moderação, suporte) deve
seguir daqui pra frente:

  - A ÚNICA chave de sessão usada para indicar "usuário logado" é
    `SESSION_KEY_USUARIO_ID` (valor: "usuario_id").
    -> `request.session[SESSION_KEY_USUARIO_ID] = usuario.pk` no login
    -> `request.session.flush()` (ou `.pop(SESSION_KEY_USUARIO_ID)`) no logout

  - `request.user` já vem populado pelo `UsuarioSessionMiddleware`
    (ver `usuarios/middleware.py`), com uma instância de `Usuario` (se
    logado) ou de `UsuarioAnonimo` (se não). Os decorators abaixo usam
    `request.user`, não a sessão diretamente — não duplique a lógica de
    resolver o usuário fora daqui.

Uso:

    from usuarios.decorators import login_usuario_requerido, fornecedor_logado, comerciante_logado

    @login_usuario_requerido
    def minha_view(request):
        ...

    @fornecedor_logado
    def gerenciar_portfolio(request):
        ...  # aqui request.user já é garantidamente um Usuario tipo_perfil='fornecedor'
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

# Nome da chave de sessão usada em todo o projeto para indicar o usuário logado.
SESSION_KEY_USUARIO_ID = "usuario_id"


def login_usuario_requerido(view_func):
    """Exige que exista um Usuario logado (qualquer tipo_perfil)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            url_login = reverse("login")
            return redirect(f"{url_login}?next={request.path}")
        return view_func(request, *args, **kwargs)

    return wrapper


def fornecedor_logado(view_func):
    """Exige Usuario logado com tipo_perfil == 'fornecedor'."""

    @wraps(view_func)
    @login_usuario_requerido
    def wrapper(request, *args, **kwargs):
        if request.user.tipo_perfil != "fornecedor":
            messages.error(request, "Esta área é exclusiva para fornecedores.")
            return redirect("dashboard_comerciante")
        return view_func(request, *args, **kwargs)

    return wrapper


def comerciante_logado(view_func):
    """Exige Usuario logado com tipo_perfil == 'comerciante'."""

    @wraps(view_func)
    @login_usuario_requerido
    def wrapper(request, *args, **kwargs):
        if request.user.tipo_perfil != "comerciante":
            messages.error(request, "Esta área é exclusiva para comerciantes.")
            return redirect("dashboard_fornecedor")
        return view_func(request, *args, **kwargs)

    return wrapper
