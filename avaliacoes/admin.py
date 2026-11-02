"""
Este arquivo fica **vazio de propósito**.

`Avaliacao` e `Favorito` usam chave primária composta
`(id_comerciante, id_fornecedor)`, e o Django Admin recusa o registro de um
model assim:

    ImproperlyConfigured: The model Avaliacao has a composite primary key,
    so it cannot be registered with admin.

Não existe `admin.register()` aqui, e não deve existir. A gestão desses dados é:

  - **RF-018 (avaliar)**: `avaliacoes/views.py::avaliar_fornecedor` — o
    comerciante avalia pelo portfólio do fornecedor;
  - **RF-028 a RF-030 (favoritos)**: `avaliacoes/views.py::lista_favoritos`,
    `alternar_favorito` e `remover_favorito`;
  - **CU22 A1 (moderação das avaliações)**: a fila em
    `moderacao/views.py::fila_avaliacoes_view`, protegida por `admin_required` —
    é a "view customizada" que este arquivo sugeria criar. Ela também implementa
    as ações de manter/remover, que o Admin não permitiria mesmo registrando o
    model.

O arquivo continua existindo porque o Django espera um `admin.py` em cada app
com `INSTALLED_APPS`; sem ele, o `autodiscover()` apenas não encontra nada — o
que também funcionaria. Manter o arquivo documenta o porquê, que é a informação
mais valiosa dele.
"""

from django.contrib import admin  # noqa: F401  (mantido: Django espera o módulo)
