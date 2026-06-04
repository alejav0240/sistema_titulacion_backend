from django.db import models
from apps.users.models import Usuario
from apps.projects.models import Version


class EstadoAnotacion(models.TextChoices):
    CORREGIDA = 'CORREGIDA'
    SIN_CORREGIR = 'SIN CORREGIR'


class NotaComentario(models.Model):
    pagina = models.IntegerField()
    x = models.DecimalField(max_digits=10, decimal_places=2)
    y = models.DecimalField(max_digits=10, decimal_places=2)
    ancho = models.DecimalField(max_digits=10, decimal_places=2)
    alto = models.DecimalField(max_digits=10, decimal_places=2)
    comentario = models.CharField(max_length=255)

    class Meta:
        db_table = 'nota_comentario'

    def __str__(self):
        return f"Pagina {self.pagina}: {self.comentario[:50]}"


class Anotacion(models.Model):
    autor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='anotaciones'
    )
    version = models.ForeignKey(
        Version,
        on_delete=models.CASCADE,
        related_name='anotaciones'
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoAnotacion.choices,
        default=EstadoAnotacion.SIN_CORREGIR
    )
    accion_a_realizar = models.CharField(max_length=255, blank=True)
    nota_observacion = models.ForeignKey(
        NotaComentario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anotaciones_observacion'
    )
    nota_correccion = models.ForeignKey(
        NotaComentario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anotaciones_correccion'
    )
    accion_realizada = models.CharField(max_length=255, blank=True)
    creado_el = models.DateTimeField(auto_now_add=True)
    corregido_el = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'anotacion'
        ordering = ['-creado_el']

    def __str__(self):
        return f"Anotacion {self.id} - {self.version}"