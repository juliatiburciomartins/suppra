from django.urls import path

from avaliacoes import views


urlpatterns = [
    # CU09 — Registrar/editar avaliação de um fornecedor (RF-018)
    path(
        "fornecedores/<int:fornecedor_id>/avaliar/",
        views.avaliar_fornecedor,
        name="avaliar_fornecedor",
    ),

    # CU08 — Favoritos (RF-028, RF-029, RF-030)
    path("favoritos/", views.lista_favoritos, name="lista_favoritos"),
    path("favoritos/alternar/", views.alternar_favorito, name="alternar_favorito"),
    path(
        "favoritos/<int:fornecedor_id>/remover/",
        views.remover_favorito,
        name="remover_favorito",
    ),
]