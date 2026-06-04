from django.db import models
from apps.users.models import Usuario


class Materia(models.Model):
    nombre = models.CharField(max_length=255)
    semestre = models.IntegerField()
    docente_a_cargo = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materias_impartidas'
    )
    grupo = models.CharField(max_length=255)

    class Meta:
        db_table = 'materia'
        verbose_name_plural = 'Materias'

    def __str__(self):
        return f"{self.nombre} - {self.grupo}"


class EstudiantesMateria(models.Model):
    materia = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE,
        related_name='estudiantes'
    )
    estudiante = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='materias_inscritas'
    )

    class Meta:
        db_table = 'estudiantes_materia'
        unique_together = ('materia', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.nombre} en {self.materia.nombre}"