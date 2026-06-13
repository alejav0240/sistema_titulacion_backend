from rest_framework import serializers

from apps.annotations.models import (
    Anotacion,
    AnotacionEvento,
    NotaComentario,
    Severidad,
)


class NotaComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaComentario
        fields = ['id', 'pagina', 'x', 'y', 'ancho', 'alto', 'comentario']


class AnotacionEventoSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre', read_only=True)

    class Meta:
        model = AnotacionEvento
        fields = ['id', 'tipo', 'texto', 'autor', 'autor_nombre', 'created_at']
        read_only_fields = fields


class AnotacionSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre', read_only=True)
    codigo_display = serializers.CharField(read_only=True)
    nota_observacion = NotaComentarioSerializer(read_only=True)
    nota_correccion = NotaComentarioSerializer(read_only=True)

    class Meta:
        model = Anotacion
        fields = [
            'id', 'codigo', 'codigo_display', 'version', 'autor', 'autor_nombre',
            'estado', 'severidad', 'accion_a_realizar', 'accion_realizada',
            'nota_observacion', 'nota_correccion', 'creado_el', 'subsanada_el',
            'corregido_el',
        ]
        read_only_fields = fields


class AnotacionCreateSerializer(serializers.Serializer):
    pagina = serializers.IntegerField(min_value=1)
    x = serializers.DecimalField(max_digits=10, decimal_places=6)
    y = serializers.DecimalField(max_digits=10, decimal_places=6)
    ancho = serializers.DecimalField(max_digits=10, decimal_places=6)
    alto = serializers.DecimalField(max_digits=10, decimal_places=6)
    comentario = serializers.CharField()
    severidad = serializers.ChoiceField(
        choices=Severidad.choices, default=Severidad.SUGERENCIA
    )
    accion_a_realizar = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=''
    )


class AnotacionUpdateSerializer(serializers.Serializer):
    comentario = serializers.CharField(required=False)
    severidad = serializers.ChoiceField(choices=Severidad.choices, required=False)
    accion_a_realizar = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )


class SubsanarSerializer(serializers.Serializer):
    comentario = serializers.CharField()
    pagina = serializers.IntegerField(min_value=1, required=False)
    x = serializers.DecimalField(max_digits=10, decimal_places=6, required=False)
    y = serializers.DecimalField(max_digits=10, decimal_places=6, required=False)
    ancho = serializers.DecimalField(max_digits=10, decimal_places=6, required=False)
    alto = serializers.DecimalField(max_digits=10, decimal_places=6, required=False)


class FeedbackSerializer(serializers.Serializer):
    feedback = serializers.CharField(required=False, allow_blank=True, default='')
