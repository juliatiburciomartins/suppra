"""
Telas públicas do app `core` (CU04 e CU18).

- `home_view` — landing page. `{% url 'home' %}` é referenciada incondicionalmente
  em `base.html` (logo + rodapé), então precisa existir no namespace global.
- `faq_view` — CU18 / RF-015: FAQ público, sem autenticação.
- `termos_uso_view` e `politica_privacidade_view` — RNF-015: os documentos têm
  de estar disponíveis publicamente e ser exibidos no ato do cadastro (CU01,
  passo 4). São as páginas ligadas no rodapé do `base.html`.
"""

from django.shortcuts import redirect, render

from usuarios.onboarding import ja_visualizou


def home_view(request):
    """
    {% url 'home' %} é referenciada incondicionalmente em base.html
    (logo + rodapé), então precisa existir no namespace global.
    """
    # Checagem segura: verifica se o usuário existe na requisição e está autenticado
    user = getattr(request, 'user', None)

    if user and getattr(user, 'is_authenticated', False):
        tipo_menu = getattr(user, 'tipo_perfil', None)  # 'fornecedor' ou 'comerciante'

        # RF-014 / CU17: quem ainda não concluiu nem ignorou o tutorial é levado
        # para ele no primeiro acesso autenticado.
        if not ja_visualizou(request, user):
            return redirect("tutorial")  # /tutorial/

        return render(request, "home_autenticado.html", {"tipo_menu": tipo_menu})

    return render(request, "home_visitante.html")


def faq_view(request):
    user = getattr(request, 'user', None)
    is_auth = user and getattr(user, 'is_authenticated', False)

    tipo_menu = getattr(user, 'tipo_perfil', None) if is_auth else None
    return render(request, "core/faq.html", {"tipo_menu": tipo_menu})


def _contexto_politica(request):
    """Contexto comum às páginas legais: perfil do visitante + versão vigente."""
    user = getattr(request, "user", None)
    autenticado = bool(user and getattr(user, "is_authenticated", False))

    return {
        "tipo_menu": getattr(user, "tipo_perfil", None) if autenticado else None,
        "autenticado": autenticado,
    }


def termos_uso_view(request):
    """
    Termos de Uso (RNF-015). O texto exibido é o da versão vigente em
    `termo_uso` quando existir; senão cai no conteúdo estático do template.
    """
    from core.models import TermoUso

    contexto = _contexto_politica(request)
    contexto["termo"] = TermoUso.objects.order_by("-data_vigencia", "-id_termo_uso").first()
    return render(request, "politicas/termos_uso.html", contexto)


def politica_privacidade_view(request):
    """Política de Privacidade (RNF-007 / RNF-015)."""
    return render(request, "politicas/politica_privacidade.html", _contexto_politica(request))
