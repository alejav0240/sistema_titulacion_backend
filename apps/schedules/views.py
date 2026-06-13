from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schedules.models import Cronograma, PublicoObjetivo
from apps.schedules.serializers import CronogramaSerializer
from apps.users.models import Rol
from apps.users.permissions import ADMIN_ROLES, IsAuthenticated


def cronogramas_para(user):
    qs = Cronograma.objects.all()
    if user.rol in ADMIN_ROLES:
        return qs
    if user.rol == Rol.ESTUDIANTE:
        return qs.filter(
            Q(publico_objetivo=PublicoObjetivo.ESTUDIANTES)
            | Q(publico_objetivo=PublicoObjetivo.TODOS)
        )
    return qs.filter(
        Q(publico_objetivo=PublicoObjetivo.DOCENTES)
        | Q(publico_objetivo=PublicoObjetivo.TODOS)
    )


class CronogramaListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = cronogramas_para(request.user)
        desde = request.query_params.get('from')
        if desde:
            qs = qs.filter(fecha_fin__gte=desde)
        hasta = request.query_params.get('to')
        if hasta:
            qs = qs.filter(fecha_inicio__lte=hasta)
        semestre = request.query_params.get('semestre')
        if semestre:
            qs = qs.filter(semestre=semestre)
        tipo = request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        return Response(CronogramaSerializer(qs, many=True).data)

    def post(self, request):
        if request.user.rol not in ADMIN_ROLES:
            return Response(
                {'detail': 'Solo el director puede crear eventos del cronograma.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CronogramaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evento = serializer.save()
        return Response(
            CronogramaSerializer(evento).data, status=status.HTTP_201_CREATED
        )


class CronogramaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.rol not in ADMIN_ROLES:
            return Response(status=status.HTTP_403_FORBIDDEN)
        evento = Cronograma.objects.filter(pk=pk).first()
        if not evento:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CronogramaSerializer(evento, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if request.user.rol not in ADMIN_ROLES:
            return Response(status=status.HTTP_403_FORBIDDEN)
        evento = Cronograma.objects.filter(pk=pk).first()
        if not evento:
            return Response(status=status.HTTP_404_NOT_FOUND)
        evento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
