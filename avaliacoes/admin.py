from django.contrib import admin  # noqa: F401
# from .models import Avaliacao, Favorito
#
# OBS: Avaliacao e Favorito usam chave primaria composta
# (id_comerciante, id_fornecedor), e o Django admin ainda nao
# suporta registrar models com CompositePrimaryKey diretamente.
# Se quiserem gerenciar esses dados num painel, criem uma view
# customizada em vez de admin.register() para esses dois models.
