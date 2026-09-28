from django.urls import path
from demandas import views

urlpatterns = [
    path("demandas/minhas/", views.minhas_demandas_view, name="minhas_demandas"),
    path("demandas/publicar/", views.publicar_demanda_view, name="publicar_demanda"),
    path("demandas/<int:pk>/editar/", views.editar_demanda_view, name="editar_demanda"),
    path("demandas/<int:pk>/encerrar/", views.encerrar_demanda_view, name="encerrar_demanda"),
]