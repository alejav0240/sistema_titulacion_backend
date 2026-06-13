from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import CategoriaNotificacion
from apps.notifications.services import notify
from apps.relationships.models import TutorTribunal
from apps.relationships.serializers import TutorTribunalSerializer
from apps.users.models import Rol
from apps.users.permissions import ADMIN_ROLES, IsAuthenticated, IsDirectorOrDTC


class TutorTribunalListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TutorTribunal.objects.select_related('estudiante', 'docente')
        if request.user.rol == Rol.ESTUDIANTE:
            qs = qs.filter(estudiante=request.user, is_active=True)
        elif request.user.rol not in ADMIN_ROLES:
            qs = qs.filter(docente=request.user, is_active=True)

        estudiante = request.query_params.get('estudiante')
        if estudiante:
            qs = qs.filter(estudiante_id=estudiante)
        docente = request.query_params.get('docente')
        if docente:
            qs = qs.filter(docente_id=docente)
        relacion = request.query_params.get('relacion')
        if relacion:
            qs = qs.filter(relacion=relacion)

        return Response(TutorTribunalSerializer(qs, many=True).data)

    def post(self, request):
        if request.user.rol not in ADMIN_ROLES:
            return Response(
                {'detail': 'Solo el director puede asignar tutores/tribunales.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = TutorTribunalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        existente = TutorTribunal.objects.filter(
            estudiante=serializer.validated_data['estudiante'],
            docente=serializer.validated_data['docente'],
            relacion=serializer.validated_data['relacion'],
        ).first()
        if existente:
            existente.is_active = True
            existente.save(update_fields=['is_active', 'updated_at'])
            return Response(TutorTribunalSerializer(existente).data)
        relacion = serializer.save()

        notify(
            relacion.docente,
            f"Fuiste asignado como {relacion.relacion.lower()} de "
            f"{relacion.estudiante.nombre}.",
            titulo='Nueva asignación',
            categoria=CategoriaNotificacion.SISTEMA,
            emisor=request.user,
        )
        notify(
            relacion.estudiante,
            f"{relacion.docente.nombre} fue asignado como tu "
            f"{relacion.relacion.lower()}.",
            titulo='Nueva asignación',
            categoria=CategoriaNotificacion.SISTEMA,
            emisor=request.user,
        )

        return Response(
            TutorTribunalSerializer(relacion).data, status=status.HTTP_201_CREATED
        )


class TutorTribunalDetailView(APIView):
    permission_classes = [IsDirectorOrDTC]

    def delete(self, request, pk):
        relacion = TutorTribunal.objects.filter(pk=pk).first()
        if not relacion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        relacion.is_active = False
        relacion.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
