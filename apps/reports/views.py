from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academic.models import EstudiantesMateria, Materia
from apps.annotations.models import Anotacion, AnotacionEvento, EstadoAnotacion
from apps.annotations.serializers import AnotacionSerializer
from apps.projects.models import (
    EstadoProyecto,
    EstadoVersion,
    EtapaProyecto,
    ProyectoGrado,
    Version,
)
from apps.projects.serializers import ProyectoGradoSerializer, VersionSerializer
from apps.projects.views import proyectos_para
from apps.relationships.models import TipoRelacion, TutorTribunal
from apps.schedules.serializers import CronogramaSerializer
from apps.schedules.views import cronogramas_para
from apps.users.models import Rol, Usuario
from apps.users.permissions import (
    IsAuthenticated,
    IsDirectorOrDTC,
    IsDocenteLike,
    IsEstudiante,
)

PROGRESO_POR_ETAPA = {
    EtapaProyecto.PROPUESTA: 10,
    EtapaProyecto.ANTEPROYECTO: 30,
    EtapaProyecto.DESARROLLO: 55,
    EtapaProyecto.REVISION: 80,
    EtapaProyecto.DEFENSA: 95,
}


def proximos_eventos(user, limit=4):
    hoy = timezone.now().date()
    qs = cronogramas_para(user).filter(fecha_fin__gte=hoy).order_by('fecha_inicio')
    return CronogramaSerializer(qs[:limit], many=True).data


class StudentDashboardView(APIView):
    permission_classes = [IsEstudiante]

    def get(self, request):
        proyecto = (
            proyectos_para(request.user)
            .exclude(estado=EstadoProyecto.CONCLUIDO)
            .order_by('-created_at')
            .first()
        )

        relaciones = TutorTribunal.objects.filter(
            estudiante=request.user, is_active=True
        ).select_related('docente')
        tutor = next(
            (r.docente.nombre for r in relaciones if r.relacion == TipoRelacion.TUTOR),
            None,
        )
        tribunal = [
            r.docente.nombre for r in relaciones if r.relacion == TipoRelacion.TRIBUNAL
        ]

        data = {
            'proyecto': None,
            'progreso': 0,
            'tutor': tutor,
            'tribunal': tribunal,
            'versiones': [],
            'observaciones': [],
            'proximos_eventos': proximos_eventos(request.user),
        }

        if proyecto:
            versiones = list(
                proyecto.versiones.prefetch_related('anotaciones').all()
            )
            data['proyecto'] = ProyectoGradoSerializer(proyecto).data
            progreso = PROGRESO_POR_ETAPA.get(proyecto.etapa, 10)
            if proyecto.estado == EstadoProyecto.CONCLUIDO:
                progreso = 100
            data['progreso'] = progreso
            data['versiones'] = VersionSerializer(versiones, many=True).data

            pendientes = (
                Anotacion.objects.filter(
                    version__proyecto=proyecto,
                )
                .exclude(estado=EstadoAnotacion.APROBADA)
                .select_related('autor', 'nota_observacion', 'nota_correccion')
                .order_by('-creado_el')[:10]
            )
            data['observaciones'] = AnotacionSerializer(pendientes, many=True).data

        return Response(data)


class TeacherDashboardView(APIView):
    permission_classes = [IsDocenteLike]

    def get(self, request):
        user = request.user
        relaciones = TutorTribunal.objects.filter(
            docente=user, is_active=True
        ).select_related('estudiante')
        tutorados_ids = [
            r.estudiante_id for r in relaciones if r.relacion == TipoRelacion.TUTOR
        ]
        tribunal_ids = [
            r.estudiante_id for r in relaciones if r.relacion == TipoRelacion.TRIBUNAL
        ]

        def proyectos_de(estudiante_ids):
            qs = (
                ProyectoGrado.objects.filter(estudiante_id__in=estudiante_ids)
                .exclude(estado=EstadoProyecto.CONCLUIDO)
                .select_related('estudiante')
                .prefetch_related('versiones__anotaciones')
                .order_by('-updated_at')
            )
            return ProyectoGradoSerializer(qs, many=True).data

        # Revisiones pendientes en materias a cargo (entregas EN REVISION)
        materia_estudiantes = EstudiantesMateria.objects.filter(
            materia__docente_a_cargo=user
        ).select_related('estudiante', 'materia')
        ids_materia = [em.estudiante_id for em in materia_estudiantes]
        materia_por_estudiante = {
            em.estudiante_id: em.materia.nombre for em in materia_estudiantes
        }
        pendientes_materia = []
        versiones_pendientes = (
            Version.objects.filter(
                proyecto__estudiante_id__in=ids_materia,
                estado=EstadoVersion.EN_REVISION,
            )
            .select_related('proyecto__estudiante')
            .order_by('created_at')[:9]
        )
        for version in versiones_pendientes:
            estudiante = version.proyecto.estudiante
            pendientes_materia.append({
                'version_id': version.id,
                'estudiante': estudiante.nombre,
                'proyecto': version.proyecto.titulo,
                'materia': materia_por_estudiante.get(estudiante.id, ''),
                'numero_version': version.numero_version,
                'created_at': version.created_at,
            })

        # Revisiones (anotaciones propias) por día — últimos 7 días
        hace_7 = timezone.now() - timedelta(days=6)
        por_dia_qs = (
            Anotacion.objects.filter(autor=user, creado_el__gte=hace_7)
            .annotate(dia=TruncDate('creado_el'))
            .values('dia')
            .annotate(total=Count('id'))
        )
        conteos = {item['dia']: item['total'] for item in por_dia_qs}
        revisiones_por_dia = []
        for offset in range(7):
            dia = (hace_7 + timedelta(days=offset)).date()
            revisiones_por_dia.append({'dia': dia, 'total': conteos.get(dia, 0)})

        # Actividad reciente sobre proyectos relacionados
        ids_relacionados = set(tutorados_ids) | set(tribunal_ids) | set(ids_materia)
        eventos = (
            AnotacionEvento.objects.filter(
                anotacion__version__proyecto__estudiante_id__in=ids_relacionados
            )
            .select_related('autor', 'anotacion__version__proyecto')
            .order_by('-created_at')[:6]
        )
        actividad = [
            {
                'tipo': e.tipo,
                'autor': e.autor.nombre if e.autor else None,
                'proyecto': e.anotacion.version.proyecto.titulo,
                'version_id': e.anotacion.version_id,
                'created_at': e.created_at,
            }
            for e in eventos
        ]

        return Response({
            'tutorias': proyectos_de(tutorados_ids),
            'tribunales': proyectos_de(tribunal_ids),
            'pendientes_materia': pendientes_materia,
            'revisiones_por_dia': revisiones_por_dia,
            'actividad': actividad,
            'proximos_eventos': proximos_eventos(request.user),
        })


class DirectorDashboardView(APIView):
    permission_classes = [IsDirectorOrDTC]

    def get(self, request):
        ahora = timezone.now()
        proyectos = ProyectoGrado.objects.all()
        total = proyectos.count()

        ultima_por_proyecto = {}
        for version in Version.objects.order_by(
            'proyecto_id', '-numero_version'
        ).values('proyecto_id', 'estado', 'numero_version'):
            ultima_por_proyecto.setdefault(
                version['proyecto_id'], version['estado']
            )
        estados = {'APROBADO': 0, 'EN REVISION': 0, 'OBSERVADO': 0, 'BORRADOR': 0}
        for proyecto_id in proyectos.values_list('id', flat=True):
            estado = ultima_por_proyecto.get(proyecto_id, 'BORRADOR')
            estados[estado] = estados.get(estado, 0) + 1

        observaciones_activas = Anotacion.objects.exclude(
            estado=EstadoAnotacion.APROBADA
        ).count()
        tutores_activos = (
            TutorTribunal.objects.filter(is_active=True)
            .values('docente')
            .distinct()
            .count()
        )

        # Tiempo promedio de resolución de observaciones (días)
        resueltas = Anotacion.objects.filter(corregido_el__isnull=False)
        total_dias, n = 0, 0
        for anotacion in resueltas.only('creado_el', 'corregido_el')[:500]:
            total_dias += (anotacion.corregido_el - anotacion.creado_el).days
            n += 1
        dias_promedio = round(total_dias / n, 1) if n else 0

        # Actividad mensual (últimos 6 meses): entregas de versiones
        hace_6m = ahora - timedelta(days=183)
        mensual = (
            Version.objects.filter(created_at__gte=hace_6m)
            .annotate(mes=TruncMonth('created_at'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )
        actividad_mensual = [
            {'mes': item['mes'].strftime('%b'), 'total': item['total']}
            for item in mensual
        ]

        # Distribución por materia
        distribucion = (
            Materia.objects.annotate(
                proyectos=Count(
                    'estudiantes__estudiante__proyectos', distinct=True
                )
            )
            .values('nombre', 'proyectos')
            .order_by('-proyectos')[:6]
        )

        # Heatmap carga docente: anotaciones por docente por semana (8 semanas)
        docentes = Usuario.objects.filter(
            rol__in=['DOCENTE', 'TUTOR', 'TRIBUNAL'], is_active=True
        )[:8]
        inicio_heatmap = ahora - timedelta(weeks=8)
        carga = []
        for docente in docentes:
            anotaciones = Anotacion.objects.filter(
                autor=docente, creado_el__gte=inicio_heatmap
            ).values_list('creado_el', flat=True)
            semanas = [0] * 8
            for fecha in anotaciones:
                idx = min(7, (fecha - inicio_heatmap).days // 7)
                semanas[idx] += 1
            carga.append({'docente': docente.nombre, 'semanas': semanas})

        # Alertas: proyectos sin actividad hace más de 10 días
        limite = ahora - timedelta(days=10)
        en_riesgo = (
            proyectos.exclude(estado=EstadoProyecto.CONCLUIDO)
            .filter(updated_at__lt=limite)
            .count()
        )

        # Actividad reciente global
        eventos = (
            AnotacionEvento.objects.select_related(
                'autor', 'anotacion__version__proyecto'
            ).order_by('-created_at')[:5]
        )
        actividad_reciente = [
            {
                'tipo': e.tipo,
                'autor': e.autor.nombre if e.autor else None,
                'proyecto': e.anotacion.version.proyecto.titulo,
                'created_at': e.created_at,
            }
            for e in eventos
        ]

        return Response({
            'kpis': {
                'total_proyectos': total,
                'aprobados': estados.get('APROBADO', 0),
                'pendientes': estados.get('EN REVISION', 0),
                'observaciones_activas': observaciones_activas,
                'tutores_activos': tutores_activos,
                'dias_promedio_revision': dias_promedio,
            },
            'estado_proyectos': estados,
            'actividad_mensual': actividad_mensual,
            'distribucion_materia': list(distribucion),
            'carga_docente': carga,
            'alertas': {'proyectos_en_riesgo': en_riesgo},
            'vencimientos': proximos_eventos(request.user, limit=3),
            'actividad_reciente': actividad_reciente,
        })
