from django.db import models
from django.conf import settings

class ProyectoGrado(models.Model):
    ESTADO_CHOICES = [
        ('en revision', 'En revisión'),
        ('rechazado', 'Rechazado'),
        ('aprovado', 'Aprobado'),
    ]
    
    titulo = models.CharField(max_length=255)
    estudiante = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='proyecto_grado'
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='en revision')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'proyecto de grado'
        verbose_name = 'proyecto de grado'
        verbose_name_plural = 'proyectos de grado'

    def __str__(self):
        return self.titulo

class Version(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('revisando', 'Revisando'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('observado', 'Observado'),
    ]
    
    proyecto = models.ForeignKey(ProyectoGrado, on_delete=models.CASCADE, related_name='versiones')
    numero_version = models.IntegerField(db_column='numero de version')
    url_pdf = models.FileField(upload_to='proyectos/pdfs/')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'versiones'
        verbose_name = 'versión'
        verbose_name_plural = 'versiones'

    def __str__(self):
        return f"{self.proyecto.titulo} - V{self.numero_version}"

class NotaComentario(models.Model):
    pagina = models.IntegerField()
    x = models.FloatField()
    y = models.FloatField()
    ancho = models.FloatField()
    alto = models.FloatField()
    comentario = models.CharField(max_length=255)

    class Meta:
        db_table = 'nota_comentario'
        verbose_name = 'nota comentario'
        verbose_name_plural = 'notas comentarios'

class Anotacion(models.Model):
    ESTADO_CHOICES = [
        ('abierto', 'Abierto (Pendiente)'),
        ('resuelto', 'Resuelto (Corregido)'),
    ]
    
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name='anotaciones', db_column='version _id')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierto')
    accion_correctiva = models.CharField(max_length=255, blank=True, null=True)
    nota_observacion = models.ForeignKey(
        NotaComentario, 
        on_delete=models.CASCADE, 
        related_name='observacion_de'
    )
    nota_correccion = models.ForeignKey(
        NotaComentario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='correccion_de'
    )
    creado_el = models.DateTimeField(auto_now_add=True)
    coregido_el = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'anotacion'
        verbose_name = 'anotación'
        verbose_name_plural = 'anotaciones'
