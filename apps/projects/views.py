from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import EstadoProyecto, ProyectoGrado
from apps.projects.serializers import (
    ProyectoGradoCreateSerializer,
    ProyectoGradoSerializer,
)
from apps.users.models import Rol
from apps.users.permissions import IsAuthenticated


def get_active_project(user):
    return (
        ProyectoGrado.objects.filter(estudiante=user)
        .exclude(estado=EstadoProyecto.CONCLUIDO)
        .order_by('-created_at')
        .first()
    )


class ProyectoGradoListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.rol != Rol.ESTUDIANTE:
            return Response(
                {'detail': 'Solo los estudiantes pueden registrar proyectos.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        unexpected_fields = set(request.data.keys()) - {'titulo'}
        if unexpected_fields:
            return Response(
                {'detail': 'Solo se permite registrar el titulo del proyecto.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProyectoGradoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            if get_active_project(request.user):
                return Response(
                    {'detail': 'Ya tienes un proyecto activo registrado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            project = ProyectoGrado.objects.create(
                titulo=serializer.validated_data['titulo'],
                estudiante=request.user,
                estado=EstadoProyecto.EN_REVISION,
            )

        return Response(
            ProyectoGradoSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProyectoGradoActiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.rol != Rol.ESTUDIANTE:
            return Response(
                {'detail': 'Solo los estudiantes pueden consultar su proyecto activo.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        project = get_active_project(request.user)
        return Response({
            'project': ProyectoGradoSerializer(project).data if project else None,
        })

