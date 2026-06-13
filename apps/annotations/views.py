from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.annotations.models import (
    Anotacion,
    AnotacionEvento,
    EstadoAnotacion,
    NotaComentario,
    TipoEvento,
)
from apps.annotations.serializers import (
    AnotacionCreateSerializer,
    AnotacionEventoSerializer,
    AnotacionSerializer,
    AnotacionUpdateSerializer,
    FeedbackSerializer,
    SubsanarSerializer,
)
from apps.notifications.models import CategoriaNotificacion, Prioridad
from apps.notifications.services import notify
from apps.projects.models import Version
from apps.users.permissions import (
    IsAuthenticated,
    es_revisor_de,
    puede_ver_proyecto,
)


def get_version_visible(request, pk):
    version = (
        Version.objects.select_related('proyecto__estudiante').filter(pk=pk).first()
    )
    if not version or not puede_ver_proyecto(request.user, version.proyecto):
        return None
    return version


def get_anotacion_visible(request, pk):
    anotacion = (
        Anotacion.objects.select_related(
            'version__proyecto__estudiante', 'autor',
            'nota_observacion', 'nota_correccion',
        )
        .filter(pk=pk)
        .first()
    )
    if not anotacion or not puede_ver_proyecto(
        request.user, anotacion.version.proyecto
    ):
        return None
    return anotacion


class VersionAnotacionesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        version = get_version_visible(request, pk)
        if not version:
            return Response(status=status.HTTP_404_NOT_FOUND)
        anotaciones = version.anotaciones.select_related(
            'autor', 'nota_observacion', 'nota_correccion'
        ).order_by('codigo')
        return Response(AnotacionSerializer(anotaciones, many=True).data)

    def post(self, request, pk):
        version = get_version_visible(request, pk)
        if not version:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not es_revisor_de(request.user, version.proyecto):
            return Response(
                {'detail': 'No tienes permisos para anotar esta versión.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AnotacionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            nota = NotaComentario.objects.create(
                pagina=data['pagina'],
                x=data['x'],
                y=data['y'],
                ancho=data['ancho'],
                alto=data['alto'],
                comentario=data['comentario'],
            )
            ultimo = version.anotaciones.aggregate(n=Max('codigo'))['n'] or 0
            anotacion = Anotacion.objects.create(
                autor=request.user,
                version=version,
                codigo=ultimo + 1,
                severidad=data['severidad'],
                accion_a_realizar=data.get('accion_a_realizar', ''),
                nota_observacion=nota,
            )
            AnotacionEvento.objects.create(
                anotacion=anotacion,
                autor=request.user,
                tipo=TipoEvento.CREACION,
                texto=data['comentario'],
            )

        notify(
            version.proyecto.estudiante,
            f"{request.user.nombre} marcó la observación "
            f"{anotacion.codigo_display} en la V{version.numero_version} de "
            f"\"{version.proyecto.titulo}\".",
            titulo='Nueva observación',
            categoria=CategoriaNotificacion.OBSERVACION,
            prioridad=Prioridad.ALTA,
            link=f"/revision/{version.id}",
            emisor=request.user,
        )

        return Response(
            AnotacionSerializer(anotacion).data, status=status.HTTP_201_CREATED
        )


class AnotacionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        anotacion = get_anotacion_visible(request, pk)
        if not anotacion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if anotacion.autor_id != request.user.id:
            return Response(
                {'detail': 'Solo el autor puede editar la observación.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if anotacion.estado != EstadoAnotacion.PENDIENTE:
            return Response(
                {'detail': 'Solo se pueden editar observaciones pendientes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AnotacionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'comentario' in data and anotacion.nota_observacion:
            anotacion.nota_observacion.comentario = data['comentario']
            anotacion.nota_observacion.save(update_fields=['comentario'])
        if 'severidad' in data:
            anotacion.severidad = data['severidad']
        if 'accion_a_realizar' in data:
            anotacion.accion_a_realizar = data['accion_a_realizar']
        anotacion.save()

        return Response(AnotacionSerializer(anotacion).data)

    def delete(self, request, pk):
        anotacion = get_anotacion_visible(request, pk)
        if not anotacion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if anotacion.autor_id != request.user.id:
            return Response(
                {'detail': 'Solo el autor puede eliminar la observación.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if anotacion.estado != EstadoAnotacion.PENDIENTE:
            return Response(
                {'detail': 'Solo se pueden eliminar observaciones pendientes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        anotacion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubsanarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        anotacion = get_anotacion_visible(request, pk)
        if not anotacion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if anotacion.version.proyecto.estudiante_id != request.user.id:
            return Response(
                {'detail': 'Solo el estudiante dueño puede subsanar.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if anotacion.estado == EstadoAnotacion.APROBADA:
            return Response(
                {'detail': 'La observación ya fue aprobada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubsanarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            rect_keys = ('pagina', 'x', 'y', 'ancho', 'alto')
            if all(k in data for k in rect_keys):
                nota = NotaComentario.objects.create(
                    pagina=data['pagina'],
                    x=data['x'],
                    y=data['y'],
                    ancho=data['ancho'],
                    alto=data['alto'],
                    comentario=data['comentario'],
                )
                anotacion.nota_correccion = nota
            anotacion.accion_realizada = data['comentario'][:255]
            anotacion.estado = EstadoAnotacion.SUBSANADA
            anotacion.subsanada_el = timezone.now()
            anotacion.save()
            AnotacionEvento.objects.create(
                anotacion=anotacion,
                autor=request.user,
                tipo=TipoEvento.SUBSANACION,
                texto=data['comentario'],
            )

        notify(
            anotacion.autor,
            f"{request.user.nombre} subsanó la observación "
            f"{anotacion.codigo_display} de "
            f"\"{anotacion.version.proyecto.titulo}\".",
            titulo='Observación subsanada',
            categoria=CategoriaNotificacion.OBSERVACION,
            link=f"/revision/{anotacion.version_id}",
            emisor=request.user,
        )

        return Response(AnotacionSerializer(anotacion).data)


class AprobarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        anotacion = get_anotacion_visible(request, pk)
        if not anotacion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not es_revisor_de(request.user, anotacion.version.proyecto):
            return Response(
                {'detail': 'No tienes permisos para aprobar esta observación.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if anotacion.estado != EstadoAnotacion.SUBSANADA:
            return Response(
                {'detail': 'Solo se pueden aprobar observaciones subsanadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            anotacion.estado = EstadoAnotacion.APROBADA
            anotacion.corregido_el = timezone.now()
            anotacion.save()
            AnotacionEvento.objects.create(
                anotacion=anotacion,
                autor=request.user,
                tipo=TipoEvento.APROBACION,
                texto=serializer.validated_data.get('feedback', ''),
            )

        notify(
            anotacion.version.proyecto.estudiante,
            f"{request.user.nombre} aprobó la corrección de "
            f"{anotacion.codigo_display}.",
            titulo='Corrección aprobada',
            categoria=CategoriaNotificacion.OBSERVACION,
            link=f"/revision/{anotacion.version_id}",
            emisor=request.user,
        )

        return Response(AnotacionSerializer(anotacion).data)


class ReobservarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        anotacion = get_anotacion_visible(request, pk)
        if not anotacion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not es_revisor_de(request.user, anotacion.version.proyecto):
            return Response(
                {'detail': 'No tienes permisos para reobservar.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if anotacion.estado != EstadoAnotacion.SUBSANADA:
            return Response(
                {'detail': 'Solo se pueden reobservar observaciones subsanadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            anotacion.estado = EstadoAnotacion.PENDIENTE
            anotacion.subsanada_el = None
            anotacion.save()
            AnotacionEvento.objects.create(
                anotacion=anotacion,
                autor=request.user,
                tipo=TipoEvento.REOBSERVACION,
                texto=serializer.validated_data.get('feedback', ''),
            )

        notify(
            anotacion.version.proyecto.estudiante,
            f"{request.user.nombre} volvió a observar "
            f"{anotacion.codigo_display}: la corrección no fue suficiente.",
            titulo='Observación reabierta',
            categoria=CategoriaNotificacion.OBSERVACION,
            prioridad=Prioridad.ALTA,
            link=f"/revision/{anotacion.version_id}",
            emisor=request.user,
        )

        return Response(AnotacionSerializer(anotacion).data)


class HistorialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        anotacion = get_anotacion_visible(request, pk)
        if not anotacion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        eventos = anotacion.eventos.select_related('autor').all()
        return Response(AnotacionEventoSerializer(eventos, many=True).data)
