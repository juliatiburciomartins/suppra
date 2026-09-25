"""
URL configuration for hub_fecc project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    # Cada app abaixo tem seu próprio urls.py. Nenhum usa app_name/namespace
    # por opção de projeto: os templates chamam os names diretamente
    # (ex: {% url 'login' %}, {% url 'home' %}), então todos vivem no namespace global.
    path("", include("core.urls")),
    path("", include("usuarios.urls")),
    path("", include("portfolio.urls")),
    path("", include("demandas.urls")),
    path("", include("avaliacoes.urls")),
    path("", include("assinaturas.urls")),
    path("", include("moderacao.urls")),
    path("", include("suporte.urls")),
]

# Servir arquivos de mídia (uploads) em ambiente de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
