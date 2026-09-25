from django.urls import path
from core import views
from .views import home_view, faq_view

urlpatterns = [
    path("", views.home_view, name="home"),
    path("faq/", faq_view, name="faq"),
]
