from django.urls import path

from apps.academic.views import (
    InscripcionDetailView,
    MateriaDetailView,
    MateriaEstudiantesView,
    MateriaListCreateView,
)

urlpatterns = [
    path('materias/', MateriaListCreateView.as_view(), name='materias'),
    path('materias/<int:pk>/', MateriaDetailView.as_view(), name='materia_detail'),
    path('materias/<int:pk>/estudiantes/', MateriaEstudiantesView.as_view(), name='materia_estudiantes'),
    path(
        'materias/<int:pk>/estudiantes/<int:inscripcion_id>/',
        InscripcionDetailView.as_view(),
        name='materia_inscripcion',
    ),
]
