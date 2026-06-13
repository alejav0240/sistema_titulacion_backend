from django.contrib import admin
from .models import Materia, EstudiantesMateria


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'semestre', 'docente_a_cargo', 'grupo')
    list_filter = ('semestre', 'grupo')
    search_fields = ('nombre',)


@admin.register(EstudiantesMateria)
class EstudiantesMateriaAdmin(admin.ModelAdmin):
    list_display = ('materia', 'estudiante')
    list_filter = ('materia',)