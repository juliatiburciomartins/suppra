from django.urls import path

from . import views


urlpatterns = [
    # CU12 — Ver planos disponíveis
    path("planos/", views.planos_assinatura, name="planos_assinatura"),

    # CU13 — Contratar plano (resumo + confirmação)
    # O id do plano vem do banco (`plano_assinatura`), não de uma string fixa
    # como "silver"/"gold": os planos são gerenciados pela equipe (CU23).
    path(
        "planos/<int:plano_id>/confirmar/",
        views.confirmar_contratacao,
        name="confirmar_contratacao",
    ),
    path(
        "planos/<int:plano_id>/contratar/",
        views.contratar_plano,
        name="contratar_plano",
    ),

    # RF-022 / CU13 A1 — Gerenciar assinatura ativa
    path("planos/meu-plano/", views.meu_plano, name="meu_plano"),
    path("planos/cancelar/", views.cancelar_assinatura, name="cancelar_assinatura"),
]