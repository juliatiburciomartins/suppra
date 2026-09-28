from django.shortcuts import render

def home_view(request):
    """
    {% url 'home' %} é referenciada incondicionalmente em base.html
    (logo + rodapé), então precisa existir no namespace global.
    """
    # Checagem segura: verifica se o usuário existe na requisição e está autenticado
    user = getattr(request, 'user', None)

    if user and getattr(user, 'is_authenticated', False):
        tipo_menu = getattr(user, 'tipo_perfil', None)  # 'fornecedor' ou 'comerciante'
        return render(request, "home_autenticado.html", {"tipo_menu": tipo_menu})

    return render(request, "home_visitante.html")


def faq_view(request):
    user = getattr(request, 'user', None)
    is_auth = user and getattr(user, 'is_authenticated', False)

    tipo_menu = getattr(user, 'tipo_perfil', None) if is_auth else None
    return render(request, "core/faq.html", {"tipo_menu": tipo_menu})
