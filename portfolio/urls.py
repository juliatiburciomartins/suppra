from django.urls import path
from portfolio import views


urlpatterns = [
     path("cadastrar/produto", views.cadastrar_produto, name="cadastrar_produto"),
     path("portfolio/", views.gerenciar_portfolio, name="gerenciar_portfolio"),
     path("portfolio/produto/<int:produto_id>/editar/", views.editar_produto, name="editar_produto"),
	 path("portfolio/produto/<int:produto_id>/status/", views.alternar_status_produto, name="alternar_status_produto"),
]
