from django.db import models
from django.conf import settings

class Materia(models.Model):
    nombre = models.CharField(max_length=255)
    semestre = models.IntegerField()
    docente_acargo = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='materias_dictadas'
    )
    grupo = models.CharField(max_length=255)

    class Meta:
        db_table = 'materia'

    def __str__(self):
        return f"{self.nombre} - Grupo {self.grupo}"

class EstudiantesMateria(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='estudiantes')
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='materias_inscritas'
    )

    class Meta:
        db_table = 'estudiantes_materia'
        verbose_name = 'estudiante por materia'
        verbose_name_plural = 'estudiantes por materia'
        unique_together = ('materia', 'estudiante')

class TutorTribunales(models.Model):
    RELACION_CHOICES = [
        ('tutor', 'Tutor'),
        ('tribunal', 'Tribunal'),
    ]
    
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='mentores_asignados'
    )
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='estudiantes_guiados'
    )
    relacion = models.CharField(max_length=20, choices=RELACION_CHOICES, default='tribunal', db_column='relacion ')

    class Meta:
        db_table = 'tutor_tribunales'
        verbose_name = 'tutor/tribunal'
        verbose_name_plural = 'tutores y tribunales'

class Cronograma(models.Model):
    PUBLICO_CHOICES = [
        ('estudiantes', 'Estudiantes'),
        ('tutor', 'Tutor'),
        ('tribunal', 'Tribunal'),
        ('documento', 'Documento'),
    ]
    
    publico_objetivo = models.CharField(max_length=20, choices=PUBLICO_CHOICES, default='documento')
    fecha_inicio = models.DateField()
    fecha_final = models.DateField()
    descripcion = models.CharField(max_length=255)
    version = models.IntegerField()
    semestre = models.IntegerField()

    class Meta:
        db_table = 'cronograma'

    def __str__(self):
        return f"{self.descripcion} ({self.publico_objetivo})"
