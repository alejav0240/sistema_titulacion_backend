import re

from rest_framework import serializers

from apps.projects.models import EstadoVersion, ProyectoGrado, Version


class ProyectoGradoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)

    class Meta:
        model = ProyectoGrado
        fields = ['id', 'titulo', 'estudiante', 'estudiante_nombre', 'estado', 'created_at']
        read_only_fields = fields


class ProyectoGradoCreateSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=255)


class VersionSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Version
        fields = [
            'id', 'proyecto', 'numero_version', 'url_pdf',
            'nombre_archivo', 'estado', 'estado_display', 'created_at',
        ]
        read_only_fields = ['id', 'proyecto', 'numero_version', 'estado', 'created_at']


class VersionCreateSerializer(serializers.Serializer):
    url_pdf = serializers.CharField(max_length=500)
    nombre_archivo = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    _GOOGLE_DRIVE_REGEX = re.compile(
        r'^https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/.*$'
    )

    def validate_url_pdf(self, value):
        value = value.strip()

        if not self._GOOGLE_DRIVE_REGEX.match(value):
            raise serializers.ValidationError(
                'Debe proporcionar un enlace válido de Google Drive a un PDF. '
                'Formato esperado: https://drive.google.com/file/d/FILE_ID/view'
            )

        return value

