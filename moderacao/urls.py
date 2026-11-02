from django.urls import path

from moderacao import views


urlpatterns = [
    # RF-025 / CU14 — Denunciar conteúdo de portfólio ou demanda
    path("denunciar/", views.denunciar_view, name="denunciar"),

    # CU22 A1 — fila de avaliações (admin). `Avaliacao` tem PK composta, então
    # não cabe no Django Admin e é uma view com `@admin_required`.
    path("painel/avaliacoes/", views.fila_avaliacoes_view, name="fila_avaliacoes"),
    path(
        "painel/avaliacoes/<int:id_comerciante>/<int:id_fornecedor>/decidir/",
        views.decidir_avaliacao_view,
        name="decidir_avaliacao",
    ),
]