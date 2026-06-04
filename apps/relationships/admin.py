from django.contrib import admin
from .models import TutorTribunal


@admin.register(TutorTribunal)
class TutorTribunalAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'docente', 'relacion','is_active', 'created_at')
    list_filter = ('relacion', 'created_at')
    search_fields = ('estudiante__nombre', 'docente__nombre')