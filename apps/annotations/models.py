from django.db import models
from apps.users.models import Usuario
from apps.projects.models import Version


class EstadoAnotacion(models.TextChoices):
    PENDIENTE = 'PENDIENTE'
    SUBSANADA = 'SUBSANADA'
    APROBADA = 'APROBADA'


class Severidad(models.TextChoices):
    CRITICO = 'CRITICO'
    SUGERENCIA = 'SUGERENCIA'


class TipoEvento(models.TextChoices):
    CREACION = 'CREACION'
    SUBSANACION = 'SUBSANACION'
    APROBACION = 'APROBACION'
    REOBSERVACION = 'REOBSERVACION'


class NotaComentario(models.Model):
    pagina = models.IntegerField()
    # Coordenadas normalizadas (0-1) relativas al tamaño de la página del PDF
    x = models.DecimalField(max_digits=10, decimal_places=6)
    y = models.DecimalField(max_digits=10, decimal_places=6)
    ancho = models.DecimalField(max_digits=10, decimal_places=6)
    alto = models.DecimalField(max_digits=10, decimal_places=6)
    comentario = models.TextField()

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
    # Correlativo por versión: se muestra como OBS-01, OBS-02...
    codigo = models.IntegerField(default=0)
    estado = models.CharField(
        max_length=20,
        choices=EstadoAnotacion.choices,
        default=EstadoAnotacion.PENDIENTE
    )
    severidad = models.CharField(
        max_length=20,
        choices=Severidad.choices,
        default=Severidad.SUGERENCIA
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
    subsanada_el = models.DateTimeField(null=True, blank=True)
    corregido_el = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'anotacion'
        ordering = ['-creado_el']

    @property
    def codigo_display(self):
        return f"OBS-{self.codigo:02d}"

    def __str__(self):
        return f"Anotacion {self.id} - {self.version}"


class AnotacionEvento(models.Model):
    anotacion = models.ForeignKey(
        Anotacion,
        on_delete=models.CASCADE,
        related_name='eventos'
    )
    autor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='eventos_anotacion'
    )
    tipo = models.CharField(max_length=20, choices=TipoEvento.choices)
    texto = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'anotacion_evento'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.tipo} en anotacion {self.anotacion_id}"
