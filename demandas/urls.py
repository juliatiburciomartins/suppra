from django.urls import path

from demandas import views

urlpatterns = [
    # CU07 — MANAGEMENT pelo comerciante (RF-009)
    path("demandas/minhas/", views.minhas_demandas_view, name="minhas_demandas"),
    path("demandas/publicar/", views.publicar_demanda_view, name="publicar_demanda"),
    path("demandas/<int:pk>/editar/", views.editar_demanda_view, name="editar_demanda"),
    # CU07 A2 oferece encerrar (mantém o registro) OU remover (exclui de vez).
    path(
        "demandas/<int:pk>/encerrar/",
        views.encerrar_demanda_view,
        name="encerrar_demanda",
    ),
    path(
        "demandas/<int:pk>/remover/",
        views.remover_demanda_view,
        name="remover_demanda",
    ),

    # RF-011 / RF-027 — Listagem pública e detalhe (CU04, CU11)
    path("demandas/", views.listar_demandas, name="listar_demandas"),
    path("demandas/<int:pk>/", views.detalhes_demanda, name="detalhes_demanda"),
]