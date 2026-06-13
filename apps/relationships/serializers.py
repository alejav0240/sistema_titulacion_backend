from rest_framework import serializers

from apps.relationships.models import TutorTribunal
from apps.users.models import Rol, Usuario


class TutorTribunalSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    docente_nombre = serializers.CharField(source='docente.nombre', read_only=True)

    class Meta:
        model = TutorTribunal
        fields = [
            'id', 'estudiante', 'estudiante_nombre', 'docente', 'docente_nombre',
            'relacion', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        estudiante = attrs.get('estudiante')
        docente = attrs.get('docente')
        if estudiante and estudiante.rol != Rol.ESTUDIANTE:
            raise serializers.ValidationError(
                {'estudiante': 'El usuario seleccionado no es un estudiante.'}
            )
        if docente and docente.rol == Rol.ESTUDIANTE:
            raise serializers.ValidationError(
                {'docente': 'El usuario seleccionado no puede revisar proyectos.'}
            )
        return attrs
