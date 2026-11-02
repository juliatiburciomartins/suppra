from django.urls import path

from portfolio import views


urlpatterns = [
    # --- Fornecedor: gerenciar o próprio portfólio (CU10) -------------------
    path("cadastrar/produto", views.cadastrar_produto, name="cadastrar_produto"),
    path("portfolio/", views.gerenciar_portfolio, name="gerenciar_portfolio"),
    path(
        "portfolio/produto/<int:produto_id>/editar/",
        views.editar_produto,
        name="editar_produto",
    ),
    path(
        "portfolio/produto/<int:produto_id>/status/",
        views.alternar_status_produto,
        name="alternar_status_produto",
    ),
    # RF-008: remoção permanente (só por POST, ver a view)
    path(
        "portfolio/produto/<int:produto_id>/remover/",
        views.remover_produto,
        name="remover_produto",
    ),

    # --- Público/autenticado: listagem e detalhe (CU04, CU05, CU06) ---------
    path("fornecedores/", views.listar_fornecedores, name="listar_fornecedores"),
    path(
        "fornecedores/<int:fornecedor_id>/",
        views.detalhes_fornecedor,
        name="detalhes_fornecedor",
    ),
]