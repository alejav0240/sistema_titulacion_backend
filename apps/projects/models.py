import re

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


class EtapaProyecto(models.TextChoices):
    PROPUESTA = 'PROPUESTA'
    ANTEPROYECTO = 'ANTEPROYECTO'
    DESARROLLO = 'DESARROLLO'
    REVISION = 'REVISION'
    DEFENSA = 'DEFENSA'


ETAPAS_ORDEN = [
    EtapaProyecto.PROPUESTA,
    EtapaProyecto.ANTEPROYECTO,
    EtapaProyecto.DESARROLLO,
    EtapaProyecto.REVISION,
    EtapaProyecto.DEFENSA,
]


class EstadoDefensa(models.TextChoices):
    PROGRAMADA = 'PROGRAMADA'
    REALIZADA = 'REALIZADA'
    CANCELADA = 'CANCELADA'


class ResultadoDefensa(models.TextChoices):
    APROBADO = 'APROBADO'
    APROBADO_CON_OBSERVACIONES = 'APROBADO_CON_OBSERVACIONES'
    REPROBADO = 'REPROBADO'


DRIVE_ID_PATTERNS = [
    re.compile(r'/d/([-\w]{20,})'),
    re.compile(r'[?&]id=([-\w]{20,})'),
]


def extract_drive_file_id(url):
    for pattern in DRIVE_ID_PATTERNS:
        match = pattern.search(url or '')
        if match:
            return match.group(1)
    return None


def is_direct_pdf_url(url):
    url = (url or '').strip()
    return url.startswith(('http://', 'https://')) and url.lower().endswith('.pdf')


class ProyectoGrado(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default='')
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
    etapa = models.CharField(
        max_length=20,
        choices=EtapaProyecto.choices,
        default=EtapaProyecto.PROPUESTA
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
    numero_version = models.IntegerField()
    url_pdf = models.CharField(max_length=255)
    nombre_archivo = models.CharField(max_length=255, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoVersion.choices,
        default=EstadoVersion.EN_REVISION
    )
    revisada_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versiones_revisadas',
    )
    revisada_el = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'versiones'
        unique_together = ('proyecto', 'numero_version')
        ordering = ['-numero_version']

    @property
    def drive_file_id(self):
        return extract_drive_file_id(self.url_pdf)

    def __str__(self):
        return f"{self.proyecto.titulo} - Version {self.numero_version}"


class Defensa(models.Model):
    proyecto = models.OneToOneField(
        ProyectoGrado,
        on_delete=models.CASCADE,
        related_name='defensa',
    )
    fecha_hora = models.DateTimeField()
    lugar = models.CharField(max_length=255, blank=True, default='')
    estado = models.CharField(
        max_length=20,
        choices=EstadoDefensa.choices,
        default=EstadoDefensa.PROGRAMADA,
    )
    calificacion = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    resultado = models.CharField(
        max_length=30, choices=ResultadoDefensa.choices, blank=True, default=''
    )
    acta_url = models.URLField(blank=True, default='')
    observaciones = models.TextField(blank=True, default='')
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='defensas_programadas',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'defensas'
        verbose_name = 'Defensa'
        verbose_name_plural = 'Defensas'

    def __str__(self):
        return f"Defensa de {self.proyecto.titulo} ({self.estado})"
