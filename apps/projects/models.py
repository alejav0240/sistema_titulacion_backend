from django.db import models
from apps.users.models import Usuario


class EstadoProyecto(models.TextChoices):
    EN_CURSO = 'EN CURSO'
    EN_REVISION = 'EN REVISION'
    CONCLUIDO = 'CONCLUIDO'


class EstadoVersion(models.TextChoices):
    APROBADO = 'APROBADO'
    EN_REVISION = 'EN REVISION'
    OBSERVADO = 'OBSERVADO'


class ProyectoGrado(models.Model):
    titulo = models.CharField(max_length=255)
    estudiante = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='proyectos'
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoProyecto.choices,
        default=EstadoProyecto.EN_REVISION
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Proyecto de grado'
        verbose_name = 'Proyecto de Grado'
        verbose_name_plural = 'Proyectos de Grado'

    def __str__(self):
        return self.titulo


class Version(models.Model):
    proyecto = models.ForeignKey(
        ProyectoGrado,
        on_delete=models.CASCADE,
        related_name='versiones'
    )
    numero_version = models.IntegerField(editable=False)
    url_pdf = models.CharField(max_length=500)
    nombre_archivo = models.CharField(max_length=255, blank=True, default='')
    estado = models.CharField(
        max_length=20,
        choices=EstadoVersion.choices,
        default=EstadoVersion.EN_REVISION
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'versiones'
        unique_together = ('proyecto', 'numero_version')
        ordering = ['-numero_version']

    def save(self, *args, **kwargs):
        if self.numero_version is None or self._state.adding:
            max_version = Version.objects.filter(
                proyecto=self.proyecto
            ).aggregate(max_v=models.Max('numero_version'))['max_v']
            self.numero_version = (max_version or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.proyecto.titulo} - Version {self.numero_version}"
