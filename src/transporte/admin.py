from django.contrib import admin

from .models import Linha, LinhaParada, Parada


class LinhaParadaInline(admin.TabularInline):
    model = LinhaParada
    extra = 0
    autocomplete_fields = ["parada"]
    ordering = ["sentido", "ordem"]


@admin.register(Linha)
class LinhaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "modal", "destino_ida", "destino_volta", "operadora", "ativa")
    list_filter = ("modal", "ativa", "operadora")
    search_fields = ("codigo", "nome", "destino_ida", "destino_volta")
    inlines = [LinhaParadaInline]


@admin.register(Parada)
class ParadaAdmin(admin.ModelAdmin):
    list_display = ("nome", "eh_terminal", "lat", "lon", "gtfs_stop_id")
    list_filter = ("eh_terminal",)
    search_fields = ("nome", "gtfs_stop_id")
