from django.db import models
from apps.users.models import Usuario


class Prioridad(models.TextChoices):
    BAJA = 'BAJA'
    MEDIA = 'MEDIA'
    ALTA = 'ALTA'


class CategoriaNotificacion(models.TextChoices):
    ENTREGA = 'ENTREGA'
    OBSERVACION = 'OBSERVACION'
    SISTEMA = 'SISTEMA'
    RECORDATORIO = 'RECORDATORIO'


class Notificacion(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    emisor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones_enviadas'
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA
    )
    categoria = models.CharField(
        max_length=20,
        choices=CategoriaNotificacion.choices,
        default=CategoriaNotificacion.SISTEMA
    )
    leido = models.BooleanField(default=False)
    titulo = models.CharField(max_length=255, blank=True)
    mensaje = models.TextField(blank=True)
    # Pa redirección con click
    link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"Notificacion para {self.usuario.nombre} - {self.prioridad}"