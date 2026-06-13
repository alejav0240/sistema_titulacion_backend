from rest_framework import serializers

from apps.schedules.models import Cronograma


class CronogramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cronograma
        fields = [
            'id', 'publico_objetivo', 'tipo', 'fecha_inicio', 'fecha_fin',
            'descripcion', 'semestre', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        inicio = attrs.get('fecha_inicio') or getattr(
            self.instance, 'fecha_inicio', None
        )
        fin = attrs.get('fecha_fin') or getattr(self.instance, 'fecha_fin', None)
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError(
                {'fecha_fin': 'La fecha fin no puede ser anterior al inicio.'}
            )
        return attrs
