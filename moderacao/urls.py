from django.urls import path

# from moderacao import views  # descomentar conforme as views forem implementadas

# Ainda sem views neste app -- urlpatterns vazio de propósito, só para o
# include() em hub_fecc/urls.py não quebrar. Os links do menu que apontam
# para cá (ver templates/menus/menus.html) usam o padrão
# "{% url 'x' as url_x %} ... {{ url_x|default:'#' }}" para não estourar
# NoReverseMatch enquanto as URLs abaixo não existem de verdade.
urlpatterns = [
]
