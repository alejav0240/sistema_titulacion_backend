from django.db import models
from apps.users.models import Usuario


class TipoRelacion(models.TextChoices):
    TUTOR = 'TUTOR'
    TRIBUNAL = 'TRIBUNAL'


class TutorTribunal(models.Model):
    estudiante = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='tutores_asignados'
    )
    docente = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='estudiantes_tutorados'
    )
    relacion = models.CharField(
        max_length=20,
        choices=TipoRelacion.choices
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tutor_tribunales'
        unique_together = ('estudiante', 'docente', 'relacion')

    def __str__(self):
        return f"{self.docente.nombre} es {self.relacion} de {self.estudiante.nombre}"