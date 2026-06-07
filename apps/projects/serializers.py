from rest_framework import serializers

from apps.projects.models import ProyectoGrado


class ProyectoGradoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)

    class Meta:
        model = ProyectoGrado
        fields = ['id', 'titulo', 'estudiante', 'estudiante_nombre', 'estado', 'created_at']
        read_only_fields = fields


class ProyectoGradoCreateSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=255)

