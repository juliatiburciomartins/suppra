"""
Mixins de controle de acesso por perfil para views baseadas em classe
(RF-004, RNF-006). Usam a mesma regra dos decorators (`usuarios/decorators.py`).

    class MinhasDemandasView(ComercianteRequiredMixin, ListView): ...
"""

from usuarios.decorators import verificar_acesso


class LoginUsuarioRequiredMixin:
    """Exige usuário autenticado; se `perfis_permitidos` estiver definido, restringe por tipo_perfil."""

    perfis_permitidos = ()
    exigir_admin = False
    raise_exception = False

    def dispatch(self, request, *args, **kwargs):
        negado = verificar_acesso(
            request,
            perfis=tuple(self.perfis_permitidos),
            exigir_admin=self.exigir_admin,
            raise_exception=self.raise_exception,
        )
        if negado is not None:
            return negado
        return super().dispatch(request, *args, **kwargs)


class ComercianteRequiredMixin(LoginUsuarioRequiredMixin):
    perfis_permitidos = ("comerciante",)


class FornecedorRequiredMixin(LoginUsuarioRequiredMixin):
    perfis_permitidos = ("fornecedor",)


class AdminRequiredMixin(LoginUsuarioRequiredMixin):
    exigir_admin = True
