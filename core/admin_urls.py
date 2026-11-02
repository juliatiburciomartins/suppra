"""
Rotas do painel administrativo (RF-017 / CU20 a CU24).

Ficam em um arquivo separado de `urls.py` porque não são do app `core` como um
todo — são o painel da equipe gestora, que é o CU20 a CU24. Separar deixa claro
qual parte do `core` é pública (home, FAQ, políticas legais) e qual exige perfil
de administrador.

O acesso é controlado dentro das views (`@admin_required`), e não aqui, para
ficar do lado da lógica de autorização — a mesma regra dos outros painéis do
projeto (ver `usuarios/decorators.py`).
"""

from django.urls import path

from core import admin_views

urlpatterns = [
    # CU24 — indicadores da plataforma
    path("painel/", admin_views.painel_admin_view, name="painel_admin"),

    # CU21 — log de auditoria (RF-024)
    path("painel/log/", admin_views.log_auditoria_view, name="log_auditoria"),
    path(
        "painel/log/<int:log_id>/",
        admin_views.detalhe_log_view,
        name="detalhe_log",
    ),
]