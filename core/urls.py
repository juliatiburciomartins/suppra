from django.urls import path

from core import views
from .views import home_view, faq_view

urlpatterns = [
    path("", views.home_view, name="home"),
    path("faq/", faq_view, name="faq"),

    # RF-014 / CU17 — o tutorial fica só em `usuarios/urls.py` (`name="tutorial"`),
    # que é a rota usada pelo redirect pós-cadastro. Registrá-lo aqui duplicaria
    # a mesma página em dois Include, sem ganho.

    # Documentos legais (RNF-007, RNF-015). O CU01, passo 4 exige que os termos
    # e a política sejam exibidos no cadastro; essas são as páginas públicas.
    path("termos-de-uso/", views.termos_uso_view, name="termos_uso"),
    path(
        "politica-de-privacidade/",
        views.politica_privacidade_view,
        name="politica_privacidade",
    ),
]