from django.contrib import admin
from .models import Anotacion, NotaComentario


@admin.register(NotaComentario)
class NotaComentarioAdmin(admin.ModelAdmin):
    list_display = ('pagina', 'comentario', 'x', 'y')
    list_filter = ('pagina',)


@admin.register(Anotacion)
class AnotacionAdmin(admin.ModelAdmin):
    list_display = ('autor', 'version', 'estado', 'creado_el')
    list_filter = ('estado', 'creado_el')
    search_fields = ('autor__nombre', 'version__proyecto__titulo')