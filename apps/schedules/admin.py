from django.contrib import admin
from .models import Cronograma


@admin.register(Cronograma)
class CronogramaAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'publico_objetivo', 'fecha_inicio', 'fecha_fin', 'semestre')
    list_filter = ('publico_objetivo', 'semestre', 'fecha_inicio')
    search_fields = ('descripcion',)