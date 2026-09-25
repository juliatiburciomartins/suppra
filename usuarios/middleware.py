"""
Middleware de autenticação própria do Hub FECC.

O projeto NÃO usa django.contrib.auth (o model `Usuario` é uma tabela
própria, mapeada em `banco.sql`, sem relação com auth_user). A sessão de
login é controlada manualmente pela chave `SESSION_KEY_USUARIO_ID`
(ver `usuarios/decorators.py`).

Só que os templates (base.html, menus.html, home/painel.html, dashboards,
excluir_conta.html, editar_perfil.html...) já foram construídos usando a
interface padrão do Django (`user.is_authenticated`, `request.user.email`,
`request.user.tipo_perfil`). Este middleware existe só para "emprestar"
esse formato: ele roda DEPOIS do AuthenticationMiddleware (que deixaria
request.user como AnonymousUser do próprio Django) e sobrescreve
`request.user` com:

  - uma instância real de `Usuario`, se houver uma sessão válida; ou
  - `UsuarioAnonimo()`, caso contrário.

IMPORTANTE: para isso funcionar, `usuarios.middleware.UsuarioSessionMiddleware`
precisa estar em MIDDLEWARE, DEPOIS de
'django.contrib.auth.middleware.AuthenticationMiddleware' (ver settings.py).
"""

from usuarios.decorators import SESSION_KEY_USUARIO_ID
from usuarios.models import Usuario


class UsuarioAnonimo:
    """
    Substitui o AnonymousUser do Django para o restante do site não
    precisar checar `is None`, só `is_authenticated`, igual ao padrão Django.
    """

    id_usuario = None
    nome = ""
    email = ""
    tipo_perfil = None
    status_conta = None
    is_authenticated = False
    is_anonymous = True

    def __str__(self):
        return "Visitante"


class UsuarioSessionMiddleware:
    """Injeta `request.user` a partir da sessão (`session['usuario_id']`)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = self._resolver_usuario(request)
        return self.get_response(request)

    @staticmethod
    def _resolver_usuario(request):
        usuario_id = request.session.get(SESSION_KEY_USUARIO_ID)
        if not usuario_id:
            return UsuarioAnonimo()

        usuario = Usuario.objects.filter(pk=usuario_id).first()
        if usuario is None or usuario.status_conta == "suspensa":
            # sessão órfã (usuário excluído/anonimizado) ou conta suspensa
            # entre o login e o request atual: derruba a sessão.
            request.session.pop(SESSION_KEY_USUARIO_ID, None)
            return UsuarioAnonimo()

        return usuario
