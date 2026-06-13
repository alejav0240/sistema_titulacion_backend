from django.contrib import admin
from .models import ProyectoGrado, Version


@admin.register(ProyectoGrado)
class ProyectoGradoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'estudiante', 'estado', 'created_at')
    list_filter = ('estado', 'created_at')
    search_fields = ('titulo', 'estudiante__nombre')


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'numero_version', 'estado', 'created_at')
    list_filter = ('estado', 'created_at')
    search_fields = ('proyecto__titulo',)