from django.contrib import admin
from .models import Demanda


@admin.register(Demanda)
class DemandaAdmin(admin.ModelAdmin):
    list_display = ("id_demanda", "id_comerciante", "id_categoria", "status", "data_publicacao")
    list_filter = ("status", "id_categoria")
