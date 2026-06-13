import csv
from io import TextIOWrapper

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academic.models import EstudiantesMateria, Materia
from apps.academic.serializers import InscripcionSerializer, MateriaSerializer
from apps.users.models import Rol, Usuario
from apps.users.permissions import (
    ADMIN_ROLES,
    IsAuthenticated,
    IsDirectorOrDTC,
)


def materias_para(user):
    qs = Materia.objects.select_related('docente_a_cargo').annotate(
        num_estudiantes=Count('estudiantes', distinct=True),
    )
    if user.rol in ADMIN_ROLES:
        return qs
    if user.rol == Rol.ESTUDIANTE:
        return qs.filter(estudiantes__estudiante=user)
    return qs.filter(docente_a_cargo=user)


def _con_progreso(materias):
    """Calcula el progreso (versiones aprobadas / total) por materia."""
    from apps.projects.models import Version

    for materia in materias:
        estudiante_ids = list(
            materia.estudiantes.values_list('estudiante_id', flat=True)
        )
        versiones = Version.objects.filter(
            proyecto__estudiante_id__in=estudiante_ids
        )
        materia._total_versiones = versiones.count()
        materia._versiones_aprobadas = versiones.filter(estado='APROBADO').count()
    return materias


class MateriaListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = materias_para(request.user)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) | Q(grupo__icontains=search)
            )
        semestre = request.query_params.get('semestre')
        if semestre:
            qs = qs.filter(semestre=semestre)
        materias = _con_progreso(list(qs))
        return Response(MateriaSerializer(materias, many=True).data)

    def post(self, request):
        if request.user.rol not in ADMIN_ROLES:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = MateriaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        materia = serializer.save()
        materia.num_estudiantes = 0
        return Response(
            MateriaSerializer(materia).data, status=status.HTTP_201_CREATED
        )


class MateriaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        materia = materias_para(request.user).filter(pk=pk).first()
        if not materia:
            return Response(status=status.HTTP_404_NOT_FOUND)
        _con_progreso([materia])
        return Response(MateriaSerializer(materia).data)

    def patch(self, request, pk):
        if request.user.rol not in ADMIN_ROLES:
            return Response(status=status.HTTP_403_FORBIDDEN)
        materia = Materia.objects.filter(pk=pk).first()
        if not materia:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = MateriaSerializer(materia, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if request.user.rol not in ADMIN_ROLES:
            return Response(status=status.HTTP_403_FORBIDDEN)
        materia = Materia.objects.filter(pk=pk).first()
        if not materia:
            return Response(status=status.HTTP_404_NOT_FOUND)
        materia.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MateriaEstudiantesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        materia = materias_para(request.user).filter(pk=pk).first()
        if not materia:
            return Response(status=status.HTTP_404_NOT_FOUND)
        inscripciones = materia.estudiantes.select_related('estudiante')
        return Response(InscripcionSerializer(inscripciones, many=True).data)

    def post(self, request, pk):
        if request.user.rol not in ADMIN_ROLES:
            return Response(status=status.HTTP_403_FORBIDDEN)
        materia = Materia.objects.filter(pk=pk).first()
        if not materia:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Inscripción masiva por CSV (columna email)
        if 'file' in request.FILES:
            return self._importar_csv(request, materia)

        serializer = InscripcionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estudiante = serializer.validated_data['estudiante']
        inscripcion, created = EstudiantesMateria.objects.get_or_create(
            materia=materia, estudiante=estudiante
        )
        return Response(
            InscripcionSerializer(inscripcion).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _importar_csv(self, request, materia):
        resultados = {'inscritos': [], 'errors': []}
        decoded = TextIOWrapper(request.FILES['file'], encoding='utf-8')
        reader = csv.DictReader(decoded)
        for i, row in enumerate(reader, start=2):
            email = (row.get('email') or '').strip()
            if not email:
                resultados['errors'].append({'row': i, 'error': 'Email faltante'})
                continue
            estudiante = Usuario.objects.filter(
                email=email, rol=Rol.ESTUDIANTE
            ).first()
            if not estudiante:
                resultados['errors'].append(
                    {'row': i, 'error': f'Estudiante no encontrado: {email}'}
                )
                continue
            _, created = EstudiantesMateria.objects.get_or_create(
                materia=materia, estudiante=estudiante
            )
            if created:
                resultados['inscritos'].append(email)
        return Response(resultados)


class InscripcionDetailView(APIView):
    permission_classes = [IsDirectorOrDTC]

    def delete(self, request, pk, inscripcion_id):
        inscripcion = EstudiantesMateria.objects.filter(
            pk=inscripcion_id, materia_id=pk
        ).first()
        if not inscripcion:
            return Response(status=status.HTTP_404_NOT_FOUND)
        inscripcion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
