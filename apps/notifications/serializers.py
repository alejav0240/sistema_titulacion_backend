from rest_framework import serializers

from apps.notifications.models import Notificacion, Prioridad


class NotificacionSerializer(serializers.ModelSerializer):
    emisor_nombre = serializers.CharField(
        source='emisor.nombre', read_only=True, default=None
    )

    class Meta:
        model = Notificacion
        fields = [
            'id', 'titulo', 'mensaje', 'categoria', 'prioridad', 'leido',
            'link', 'emisor_nombre', 'created_at',
        ]
        read_only_fields = fields


class EnviarNotificacionSerializer(serializers.Serializer):
    destinatarios = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    titulo = serializers.CharField(max_length=255)
    mensaje = serializers.CharField()
    prioridad = serializers.ChoiceField(
        choices=Prioridad.choices, default=Prioridad.MEDIA
    )
