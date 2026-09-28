"""
Expõe o perfil do usuário logado aos templates (RF-004): permite montar menus
específicos de fornecedor / comerciante / administrador sem cada view precisar
passar `tipo_menu` manualmente. Valores passados pela view têm precedência.
"""


def perfil_usuario(request):
    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return {
            "perfil_atual": None,
            "is_fornecedor": False,
            "is_comerciante": False,
            "is_admin": False,
            "tipo_menu": None,
        }

    is_admin = bool(getattr(user, "is_admin", False))
    perfil = getattr(user, "tipo_perfil", None)

    return {
        "perfil_atual": perfil,
        "is_fornecedor": perfil == "fornecedor",
        "is_comerciante": perfil == "comerciante",
        "is_admin": is_admin,
        # Administradores usam o menu "admin" (templates/menus/*.html).
        "tipo_menu": "admin" if is_admin else perfil,
    }
