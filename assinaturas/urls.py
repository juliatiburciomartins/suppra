from django.urls import path
from . import views


urlpatterns = [
    path(
        "planos/",
        views.planos_assinatura,
        name="planos_assinatura"
    ),

    path(
        "contratar/<str:plano>/",
        views.confirmar_contratacao,
        name="confirmar_contratacao"
    ),
]