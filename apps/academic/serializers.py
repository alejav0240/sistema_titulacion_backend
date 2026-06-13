from rest_framework import serializers

from apps.academic.models import EstudiantesMateria, Materia
from apps.users.models import Rol, Usuario


class MateriaSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.CharField(
        source='docente_a_cargo.nombre', read_only=True, default=None
    )
    num_estudiantes = serializers.IntegerField(read_only=True, default=0)
    progreso = serializers.SerializerMethodField()
    codigo = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        fields = [
            'id', 'codigo', 'nombre', 'semestre', 'grupo', 'docente_a_cargo',
            'docente_nombre', 'num_estudiantes', 'progreso',
        ]
        read_only_fields = ['id']

    def get_codigo(self, obj):
        return f"INF-{400 + obj.id}"

    def get_progreso(self, obj):
        """% de versiones aprobadas entre los proyectos de los inscritos."""
        total = getattr(obj, '_total_versiones', None)
        aprobadas = getattr(obj, '_versiones_aprobadas', None)
        if total is None or not total:
            return 0
        return round(100 * aprobadas / total)


class InscripcionSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    estudiante_email = serializers.CharField(source='estudiante.email', read_only=True)

    class Meta:
        model = EstudiantesMateria
        fields = ['id', 'materia', 'estudiante', 'estudiante_nombre', 'estudiante_email']
        read_only_fields = ['id', 'materia']

    def validate_estudiante(self, value):
        if value.rol != Rol.ESTUDIANTE:
            raise serializers.ValidationError('El usuario no es un estudiante.')
        return value
