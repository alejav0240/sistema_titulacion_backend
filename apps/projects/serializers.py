from rest_framework import serializers

from apps.projects.models import (
    Defensa,
    ProyectoGrado,
    Version,
    extract_drive_file_id,
    is_direct_pdf_url,
)


class VersionSerializer(serializers.ModelSerializer):
    anotaciones_pendientes = serializers.SerializerMethodField()
    anotaciones_total = serializers.SerializerMethodField()
    proyecto_titulo = serializers.CharField(source='proyecto.titulo', read_only=True)
    estudiante_nombre = serializers.CharField(
        source='proyecto.estudiante.nombre', read_only=True
    )
    revisada_por_nombre = serializers.CharField(
        source='revisada_por.nombre', read_only=True, default=None
    )

    class Meta:
        model = Version
        fields = [
            'id', 'proyecto', 'proyecto_titulo', 'estudiante_nombre',
            'numero_version', 'url_pdf', 'nombre_archivo', 'estado',
            'revisada_por_nombre', 'revisada_el',
            'anotaciones_pendientes', 'anotaciones_total', 'created_at',
        ]
        read_only_fields = fields

    def get_anotaciones_pendientes(self, obj):
        return sum(1 for a in obj.anotaciones.all() if a.estado == 'PENDIENTE')

    def get_anotaciones_total(self, obj):
        return len(obj.anotaciones.all())


class VersionCreateSerializer(serializers.Serializer):
    url_pdf = serializers.CharField(max_length=255)
    nombre_archivo = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=''
    )

    def validate_url_pdf(self, value):
        if not extract_drive_file_id(value) and not is_direct_pdf_url(value):
            raise serializers.ValidationError(
                'El link de Google Drive no es válido. Usa el formato '
                'https://drive.google.com/file/d/<ID>/view y verifica que el '
                'archivo esté compartido como "Cualquier persona con el enlace".'
            )
        return value


class ProyectoGradoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    estudiante_email = serializers.CharField(source='estudiante.email', read_only=True)
    codigo = serializers.SerializerMethodField()
    ultima_version = serializers.SerializerMethodField()
    estado_revision = serializers.SerializerMethodField()
    observaciones_pendientes = serializers.SerializerMethodField()
    tutor_nombre = serializers.SerializerMethodField()

    defensa = serializers.SerializerMethodField()

    class Meta:
        model = ProyectoGrado
        fields = [
            'id', 'codigo', 'titulo', 'descripcion', 'estudiante', 'estudiante_nombre',
            'estudiante_email', 'estado', 'etapa', 'estado_revision',
            'ultima_version', 'observaciones_pendientes', 'tutor_nombre',
            'defensa', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_defensa(self, obj):
        try:
            defensa = obj.defensa
        except Defensa.DoesNotExist:
            return None
        return {
            'id': defensa.id,
            'fecha_hora': defensa.fecha_hora,
            'lugar': defensa.lugar,
            'estado': defensa.estado,
            'calificacion': defensa.calificacion,
            'resultado': defensa.resultado,
        }

    def get_codigo(self, obj):
        return f"PROY-{obj.created_at.year}-{obj.id:03d}"

    def _ultima(self, obj):
        versiones = list(obj.versiones.all())
        return versiones[0] if versiones else None

    def get_ultima_version(self, obj):
        version = self._ultima(obj)
        if not version:
            return None
        return {
            'id': version.id,
            'numero_version': version.numero_version,
            'estado': version.estado,
            'nombre_archivo': version.nombre_archivo,
            'created_at': version.created_at,
        }

    def get_estado_revision(self, obj):
        version = self._ultima(obj)
        return version.estado if version else 'BORRADOR'

    def get_observaciones_pendientes(self, obj):
        version = self._ultima(obj)
        if not version:
            return 0
        return sum(1 for a in version.anotaciones.all() if a.estado == 'PENDIENTE')

    def get_tutor_nombre(self, obj):
        tutores = getattr(obj.estudiante, '_tutores_prefetch', None)
        if tutores is None:
            rel = obj.estudiante.tutores_asignados.filter(
                relacion='TUTOR', is_active=True
            ).select_related('docente').first()
            return rel.docente.nombre if rel else None
        for rel in tutores:
            if rel.relacion == 'TUTOR' and rel.is_active:
                return rel.docente.nombre
        return None


class ProyectoGradoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProyectoGrado
        fields = ['titulo', 'descripcion', 'estado', 'etapa']
        extra_kwargs = {
            'titulo': {'required': False},
            'descripcion': {'required': False},
            'estado': {'required': False},
            'etapa': {'required': False},
        }


class ProyectoGradoCreateSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=255)
    descripcion = serializers.CharField(required=False, allow_blank=True, default='')


class DefensaSerializer(serializers.ModelSerializer):
    tribunal = serializers.SerializerMethodField()
    creado_por_nombre = serializers.CharField(
        source='creado_por.nombre', read_only=True, default=None
    )
    proyecto_titulo = serializers.CharField(source='proyecto.titulo', read_only=True)

    class Meta:
        model = Defensa
        fields = [
            'id', 'proyecto', 'proyecto_titulo', 'fecha_hora', 'lugar', 'estado',
            'calificacion', 'resultado', 'acta_url', 'observaciones',
            'tribunal', 'creado_por_nombre', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'proyecto', 'proyecto_titulo', 'tribunal', 'creado_por_nombre',
            'created_at', 'updated_at',
        ]

    def get_tribunal(self, obj):
        relaciones = (
            obj.proyecto.estudiante.tutores_asignados
            .filter(relacion='TRIBUNAL', is_active=True)
            .select_related('docente')
        )
        return [
            {'id': rel.docente_id, 'nombre': rel.docente.nombre}
            for rel in relaciones
        ]
