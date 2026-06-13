import re
from collections import Counter
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import ExtractHour, TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academic.models import Materia
from apps.annotations.models import Anotacion, EstadoAnotacion
from apps.projects.models import EstadoVersion, ProyectoGrado, Version
from apps.relationships.models import TipoRelacion, TutorTribunal
from apps.users.permissions import IsDirectorOrDTC

STOPWORDS_ES = {
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al',
    'a', 'en', 'y', 'o', 'u', 'que', 'se', 'su', 'sus', 'con', 'por', 'para',
    'no', 'es', 'son', 'ser', 'esta', 'este', 'esto', 'estas', 'estos', 'como',
    'mas', 'más', 'pero', 'si', 'sí', 'ya', 'le', 'les', 'lo', 'debe', 'deben',
    'hay', 'fue', 'han', 'ha', 'tiene', 'tienen', 'entre', 'sobre', 'segun',
    'según', 'cap', 'pagina', 'página', 'revisar', 'corregir', 'falta',
    'sección', 'seccion', 'capitulo', 'capítulo', 'documento', 'tesis',
}

TOKEN_RE = re.compile(r"[a-záéíóúñü]{3,}", re.IGNORECASE)


def nube_de_palabras(textos, top=30):
    contador = Counter()
    for texto in textos:
        for token in TOKEN_RE.findall((texto or '').lower()):
            if token not in STOPWORDS_ES:
                contador[token] += 1
    return [
        {'palabra': palabra, 'total': total}
        for palabra, total in contador.most_common(top)
    ]


class AnalyticsView(APIView):
    permission_classes = [IsDirectorOrDTC]

    def get(self, request):
        ahora = timezone.now()
        hace_6m = ahora - timedelta(days=183)

        versiones = Version.objects.all()
        total_versiones = versiones.count()
        aprobadas = versiones.filter(estado=EstadoVersion.APROBADO).count()
        tasa_aprobacion = round(100 * aprobadas / total_versiones) if total_versiones else 0

        anotaciones = Anotacion.objects.all()
        total_anotaciones = anotaciones.count()
        resueltas = anotaciones.filter(estado=EstadoAnotacion.APROBADA)
        obs_resueltas_pct = (
            round(100 * resueltas.count() / total_anotaciones)
            if total_anotaciones else 0
        )

        suma_dias, n = 0, 0
        for anotacion in anotaciones.filter(corregido_el__isnull=False).only(
            'creado_el', 'corregido_el'
        )[:500]:
            suma_dias += (anotacion.corregido_el - anotacion.creado_el).total_seconds()
            n += 1
        tiempo_resolucion = round(suma_dias / n / 86400, 1) if n else 0

        # Evolución de entregas por mes
        mensual = (
            versiones.filter(created_at__gte=hace_6m)
            .annotate(mes=TruncMonth('created_at'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )
        evolucion = [
            {'mes': item['mes'].strftime('%b'), 'total': item['total']}
            for item in mensual
        ]

        # Radar de competencias (métricas proxy normalizadas 0-100)
        rapidez = max(0, 100 - int(tiempo_resolucion * 10))
        competencias = [
            {'eje': 'Claridad', 'valor': obs_resueltas_pct},
            {'eje': 'Calidad', 'valor': tasa_aprobacion},
            {'eje': 'Rapidez', 'valor': rapidez},
            {'eje': 'Disponibilidad', 'valor': min(
                100,
                TutorTribunal.objects.filter(is_active=True).count() * 10,
            )},
        ]

        # Proyectos por estado y materia (barras apiladas)
        por_materia = []
        for materia in Materia.objects.all()[:6]:
            estudiante_ids = list(
                materia.estudiantes.values_list('estudiante_id', flat=True)
            )
            ultimas = {}
            for version in Version.objects.filter(
                proyecto__estudiante_id__in=estudiante_ids
            ).order_by('proyecto_id', '-numero_version').values(
                'proyecto_id', 'estado'
            ):
                ultimas.setdefault(version['proyecto_id'], version['estado'])
            conteo = Counter(ultimas.values())
            por_materia.append({
                'materia': materia.nombre,
                'aprobado': conteo.get('APROBADO', 0),
                'en_revision': conteo.get('EN REVISION', 0),
                'observado': conteo.get('OBSERVADO', 0),
            })

        # Ranking de tutores: % de observaciones aprobadas de sus estudiantes
        ranking = []
        tutores = (
            TutorTribunal.objects.filter(
                is_active=True, relacion=TipoRelacion.TUTOR
            )
            .values('docente__nombre', 'docente_id')
            .annotate(estudiantes=Count('estudiante', distinct=True))
        )
        for tutor in tutores:
            propias = Anotacion.objects.filter(autor_id=tutor['docente_id'])
            total_t = propias.count()
            ok = propias.filter(estado=EstadoAnotacion.APROBADA).count()
            ranking.append({
                'nombre': tutor['docente__nombre'],
                'estudiantes': tutor['estudiantes'],
                'efectividad': round(100 * ok / total_t) if total_t else 0,
            })
        ranking.sort(key=lambda item: -item['efectividad'])

        # Observaciones promedio por materia
        obs_por_materia = []
        for materia in Materia.objects.all()[:5]:
            estudiante_ids = list(
                materia.estudiantes.values_list('estudiante_id', flat=True)
            )
            n_proyectos = ProyectoGrado.objects.filter(
                estudiante_id__in=estudiante_ids
            ).count()
            n_obs = Anotacion.objects.filter(
                version__proyecto__estudiante_id__in=estudiante_ids
            ).count()
            obs_por_materia.append({
                'materia': materia.nombre,
                'promedio': round(n_obs / n_proyectos, 1) if n_proyectos else 0,
            })

        # Actividad por hora (anotaciones + versiones)
        actividad_horas = [0] * 24
        for item in (
            Anotacion.objects.annotate(hora=ExtractHour('creado_el'))
            .values('hora')
            .annotate(total=Count('id'))
        ):
            actividad_horas[item['hora']] += item['total']
        for item in (
            Version.objects.annotate(hora=ExtractHour('created_at'))
            .values('hora')
            .annotate(total=Count('id'))
        ):
            actividad_horas[item['hora']] += item['total']

        # Nube de observaciones
        textos = list(
            Anotacion.objects.filter(nota_observacion__isnull=False).values_list(
                'nota_observacion__comentario', flat=True
            )[:1000]
        ) + list(Anotacion.objects.values_list('accion_a_realizar', flat=True)[:1000])

        return Response({
            'kpis': {
                'tasa_aprobacion': tasa_aprobacion,
                'tiempo_resolucion_dias': tiempo_resolucion,
                'obs_resueltas_pct': obs_resueltas_pct,
                'total_observaciones': total_anotaciones,
            },
            'evolucion_entregas': evolucion,
            'competencias': competencias,
            'proyectos_por_materia': por_materia,
            'ranking_tutores': ranking[:5],
            'obs_por_materia': obs_por_materia,
            'actividad_por_hora': actividad_horas,
            'nube_observaciones': nube_de_palabras(textos),
        })
