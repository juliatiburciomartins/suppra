from django.urls import path

from suporte import views


urlpatterns = [
    # RF-019 / CU19 — abrir chamado no canal de suporte interno
    path("suporte/", views.suporte_view, name="suporte"),
    # Pós-condição do CU19: acompanhar o andamento pelo canal indicado
    path("suporte/chamados/", views.meus_chamados_view, name="meus_chamados"),
]