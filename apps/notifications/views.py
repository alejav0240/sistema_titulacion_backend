from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import CategoriaNotificacion, Notificacion
from apps.notifications.serializers import (
    EnviarNotificacionSerializer,
    NotificacionSerializer,
)
from apps.notifications.services import notify
from apps.users.models import Usuario
from apps.users.permissions import IsAuthenticated, IsDocenteLike


class NotificacionesPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificacionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notificacion.objects.filter(usuario=request.user).select_related('emisor')
        categoria = request.query_params.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)
        leido = request.query_params.get('leido')
        if leido is not None and leido != '':
            qs = qs.filter(leido=leido.lower() in ('true', '1'))

        paginator = NotificacionesPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NotificacionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notificacion.objects.filter(usuario=request.user, leido=False).count()
        return Response({'count': count})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        updated = Notificacion.objects.filter(pk=pk, usuario=request.user).update(
            leido=True
        )
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response({'ok': True})


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notificacion.objects.filter(usuario=request.user, leido=False).update(
            leido=True
        )
        return Response({'ok': True})


class EnviarNotificacionView(APIView):
    permission_classes = [IsDocenteLike]

    def post(self, request):
        serializer = EnviarNotificacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        destinatarios = Usuario.objects.filter(
            id__in=data['destinatarios'], is_active=True
        )
        if not destinatarios.exists():
            return Response(
                {'detail': 'No se encontraron destinatarios válidos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        creadas = [
            notify(
                usuario,
                data['mensaje'],
                titulo=data['titulo'],
                categoria=CategoriaNotificacion.SISTEMA,
                prioridad=data['prioridad'],
                emisor=request.user,
            )
            for usuario in destinatarios
        ]
        return Response(
            {'enviadas': len(creadas)}, status=status.HTTP_201_CREATED
        )
