from django.db import models


class PublicoObjetivo(models.TextChoices):
    ESTUDIANTES = 'ESTUDIANTES'
    DOCENTES = 'DOCENTES'


class Cronograma(models.Model):
    publico_objetivo = models.CharField(
        max_length=20,
        choices=PublicoObjetivo.choices,
        default=PublicoObjetivo.ESTUDIANTES
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    descripcion = models.CharField(max_length=255)
    semestre = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cronograma'
        ordering = ['fecha_inicio']

    def __str__(self):
        return f"{self.descripcion} ({self.fecha_inicio} - {self.fecha_fin})"