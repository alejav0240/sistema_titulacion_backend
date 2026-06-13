import logging
import re

import requests as http_requests

from django.db import transaction
from django.db.models import Max, Prefetch, Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import CategoriaNotificacion, Prioridad
from apps.notifications.services import notify, notify_many, revisores_de
from apps.projects.models import (
    Defensa,
    ETAPAS_ORDEN,
    EstadoDefensa,
    EstadoProyecto,
    EstadoVersion,
    EtapaProyecto,
    ProyectoGrado,
    ResultadoDefensa,
    Version,
    is_direct_pdf_url,
)
from apps.projects.serializers import (
    DefensaSerializer,
    ProyectoGradoCreateSerializer,
    ProyectoGradoSerializer,
    ProyectoGradoUpdateSerializer,
    VersionCreateSerializer,
    VersionSerializer,
)
from apps.relationships.models import TutorTribunal
from apps.users.models import Rol
from apps.users.permissions import (
    ADMIN_ROLES,
    DOCENTE_ROLES,
    IsAuthenticated,
    es_revisor_de,
    puede_ver_proyecto,
)


logger = logging.getLogger(__name__)


def get_active_project(user):
    return (
        ProyectoGrado.objects.filter(estudiante=user)
        .exclude(estado=EstadoProyecto.CONCLUIDO)
        .order_by('-created_at')
        .first()
    )


def proyectos_para(user):
    """Queryset de proyectos visibles según el rol del usuario."""
    qs = ProyectoGrado.objects.select_related('estudiante', 'defensa').prefetch_related(
        Prefetch(
            'versiones',
            queryset=Version.objects.prefetch_related('anotaciones'),
        ),
        Prefetch(
            'estudiante__tutores_asignados',
            queryset=TutorTribunal.objects.filter(is_active=True).select_related(
                'docente'
            ),
            to_attr='_tutores_prefetch',
        ),
    )
    if user.rol == Rol.ESTUDIANTE:
        return qs.filter(estudiante=user)
    if user.rol in ADMIN_ROLES:
        return qs
    if user.rol in DOCENTE_ROLES:
        return qs.filter(
            Q(estudiante__tutores_asignados__docente=user,
              estudiante__tutores_asignados__is_active=True)
            | Q(estudiante__materias_inscritas__materia__docente_a_cargo=user)
        ).distinct()
    return qs.none()


class ProjectsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200


class ProyectoGradoListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = proyectos_para(request.user).order_by('-updated_at')

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(titulo__icontains=search)
                | Q(estudiante__nombre__icontains=search)
                | Q(estudiante__email__icontains=search)
            )
        etapa = request.query_params.get('etapa')
        if etapa:
            qs = qs.filter(etapa=etapa)
        tutor = request.query_params.get('tutor')
        if tutor:
            qs = qs.filter(
                estudiante__tutores_asignados__docente_id=tutor,
                estudiante__tutores_asignados__is_active=True,
            )

        # Filtro por estado de revisión (columna kanban) — derivado de la última versión
        estado = request.query_params.get('estado')
        if estado:
            proyectos = [
                p for p in qs
                if ProyectoGradoSerializer().get_estado_revision(p) == estado
            ]
        else:
            proyectos = list(qs)

        paginator = ProjectsPagination()
        page = paginator.paginate_queryset(proyectos, request)
        serializer = ProyectoGradoSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.rol != Rol.ESTUDIANTE:
            return Response(
                {'detail': 'Solo los estudiantes pueden registrar proyectos.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        unexpected_fields = set(request.data.keys()) - {'titulo', 'descripcion'}
        if unexpected_fields:
            return Response(
                {'detail': 'Solo se permite registrar el titulo y la descripción del proyecto.'},
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
                descripcion=serializer.validated_data.get('descripcion', ''),
                estudiante=request.user,
                estado=EstadoProyecto.EN_REVISION,
            )

        return Response(
            ProyectoGradoSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


def validar_transicion_etapa(user, project, nueva_etapa):
    """Devuelve un mensaje de error si la transición no está permitida."""
    if nueva_etapa not in EtapaProyecto.values:
        return 'Etapa inválida.'
    idx_actual = ETAPAS_ORDEN.index(project.etapa)
    idx_nueva = ETAPAS_ORDEN.index(nueva_etapa)
    es_admin = user.rol in ADMIN_ROLES
    if idx_nueva < idx_actual and not es_admin:
        return 'Solo la Dirección puede retroceder la etapa de un proyecto.'
    if idx_nueva > idx_actual + 1:
        return (
            f'No se puede saltar de {project.get_etapa_display()} a '
            f'{nueva_etapa}: las etapas avanzan de una en una.'
        )
    if (
        idx_nueva > idx_actual
        and nueva_etapa == EtapaProyecto.DEFENSA
        and not project.versiones.filter(estado=EstadoVersion.APROBADO).exists()
    ):
        return 'Para pasar a DEFENSA el proyecto necesita al menos una versión aprobada.'
    return None


class ProyectoGradoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        project = proyectos_para(request.user).filter(pk=pk).first()
        return project

    def get(self, request, pk):
        project = self.get_object(request, pk)
        if not project:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ProyectoGradoSerializer(project).data)

    def patch(self, request, pk):
        project = self.get_object(request, pk)
        if not project:
            return Response(status=status.HTTP_404_NOT_FOUND)
        es_dueno = project.estudiante_id == request.user.id
        if not es_dueno and not es_revisor_de(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # El estudiante solo puede cambiar título y descripción
        if es_dueno and request.user.rol == Rol.ESTUDIANTE:
            data = {
                k: v for k, v in request.data.items()
                if k in ('titulo', 'descripcion')
            }
        else:
            data = request.data

        nueva_etapa = data.get('etapa')
        if nueva_etapa and nueva_etapa != project.etapa:
            error = validar_transicion_etapa(request.user, project, nueva_etapa)
            if error:
                return Response({'etapa': [error]}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProyectoGradoUpdateSerializer(project, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProyectoGradoSerializer(project).data)


class ProyectoGradoActiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.rol != Rol.ESTUDIANTE:
            return Response(
                {'detail': 'Solo los estudiantes pueden consultar su proyecto activo.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        project = (
            proyectos_para(request.user)
            .exclude(estado=EstadoProyecto.CONCLUIDO)
            .order_by('-created_at')
            .first()
        )
        return Response({
            'project': ProyectoGradoSerializer(project).data if project else None,
        })


class VersionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        project = ProyectoGrado.objects.filter(pk=pk).first()
        if not project or not puede_ver_proyecto(request.user, project):
            return Response(status=status.HTTP_404_NOT_FOUND)
        versiones = project.versiones.prefetch_related('anotaciones').all()
        return Response(VersionSerializer(versiones, many=True).data)

    def post(self, request, pk):
        project = ProyectoGrado.objects.filter(pk=pk).first()
        if not project:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if project.estudiante_id != request.user.id:
            return Response(
                {'detail': 'Solo el estudiante dueño puede subir versiones.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = VersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            ultimo = project.versiones.aggregate(n=Max('numero_version'))['n'] or 0
            version = Version.objects.create(
                proyecto=project,
                numero_version=ultimo + 1,
                url_pdf=serializer.validated_data['url_pdf'],
                nombre_archivo=serializer.validated_data.get('nombre_archivo', ''),
                estado=EstadoVersion.EN_REVISION,
            )
            project.estado = EstadoProyecto.EN_REVISION
            project.save(update_fields=['estado', 'updated_at'])

        notify_many(
            revisores_de(project),
            f"{request.user.nombre} subió la versión V{version.numero_version} "
            f"de \"{project.titulo}\".",
            titulo='Nueva entrega',
            categoria=CategoriaNotificacion.ENTREGA,
            link=f"/revision/{version.id}",
            emisor=request.user,
        )

        return Response(
            VersionSerializer(version).data, status=status.HTTP_201_CREATED
        )


class VersionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        version = (
            Version.objects.select_related('proyecto__estudiante')
            .prefetch_related('anotaciones')
            .filter(pk=pk)
            .first()
        )
        if not version or not puede_ver_proyecto(request.user, version.proyecto):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(VersionSerializer(version).data)

    def delete(self, request, pk):
        version = (
            Version.objects.select_related('proyecto__estudiante')
            .filter(pk=pk)
            .first()
        )
        if not version or not puede_ver_proyecto(request.user, version.proyecto):
            return Response(status=status.HTTP_404_NOT_FOUND)
        if version.proyecto.estudiante_id != request.user.id:
            return Response(
                {'detail': 'Solo el estudiante dueño puede eliminar sus versiones.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        ultima = version.proyecto.versiones.order_by('-numero_version').first()
        if ultima and version.id != ultima.id:
            return Response(
                {'detail': 'Solo puedes eliminar la última versión subida.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if version.estado != EstadoVersion.EN_REVISION:
            return Response(
                {'detail': 'No puedes eliminar una versión que ya fue revisada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if version.anotaciones.exists():
            return Response(
                {'detail': 'No puedes eliminar una versión que ya tiene observaciones.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.info(
            'Versión V%s del proyecto %s eliminada por %s',
            version.numero_version, version.proyecto_id, request.user.email,
        )
        version.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VersionReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        version = (
            Version.objects.select_related('proyecto__estudiante')
            .filter(pk=pk)
            .first()
        )
        if not version:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not es_revisor_de(request.user, version.proyecto):
            return Response(
                {'detail': 'No tienes permisos para revisar esta versión.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        accion = request.data.get('accion')
        if accion not in ('APROBAR', 'OBSERVAR'):
            return Response(
                {'detail': "La acción debe ser 'APROBAR' u 'OBSERVAR'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        version.estado = (
            EstadoVersion.APROBADO if accion == 'APROBAR' else EstadoVersion.OBSERVADO
        )
        version.revisada_por = request.user
        version.revisada_el = timezone.now()
        version.save(update_fields=['estado', 'revisada_por', 'revisada_el'])
        logger.info(
            'Versión %s del proyecto %s %s por %s',
            version.numero_version, version.proyecto_id,
            version.estado, request.user.email,
        )

        notify(
            version.proyecto.estudiante,
            f"Tu versión V{version.numero_version} de "
            f"\"{version.proyecto.titulo}\" fue "
            f"{'aprobada' if accion == 'APROBAR' else 'observada'} por "
            f"{request.user.nombre}.",
            titulo='Versión aprobada' if accion == 'APROBAR' else 'Versión observada',
            categoria=CategoriaNotificacion.OBSERVACION,
            prioridad=Prioridad.ALTA,
            link=f"/revision/{version.id}",
            emisor=request.user,
        )

        return Response(VersionSerializer(version).data)


DRIVE_DOWNLOAD_URL = 'https://drive.usercontent.google.com/download'
MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB
DRIVE_TIMEOUT = 30
# Las páginas intermedias de confirmación de Drive pesan unos pocos KB.
INTERSTITIAL_MAX_BYTES = 1024 * 1024
# UA de navegador: Drive entrega contenido distinto (o páginas de bot) ante UAs raros.
BROWSER_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)
_HIDDEN_INPUT_RE = re.compile(
    r'<input[^>]*\btype="hidden"[^>]*\bname="([^"]+)"[^>]*\bvalue="([^"]*)"',
    re.IGNORECASE,
)
_FORM_ACTION_RE = re.compile(r'<form[^>]*\baction="([^"]+)"', re.IGNORECASE)


class _ProxyError(Exception):
    """Error con mensaje listo para el usuario y código HTTP asociado."""

    def __init__(self, detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY):
        super().__init__(detail)
        self.detail = detail
        self.status = status_code


class VersionPdfProxyView(APIView):
    """Descarga el PDF desde Google Drive y lo sirve al frontend (evita CORS).

    Maneja la pantalla intermedia de advertencia antivirus que Drive muestra para
    archivos grandes (extrae el token de confirmación y reintenta), y devuelve
    mensajes de error específicos según la causa real del fallo.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        version = (
            Version.objects.select_related('proyecto__estudiante')
            .filter(pk=pk)
            .first()
        )
        if not version or not puede_ver_proyecto(request.user, version.proyecto):
            return Response(status=status.HTTP_404_NOT_FOUND)

        file_id = version.drive_file_id
        if not file_id and not is_direct_pdf_url(version.url_pdf):
            return Response(
                {'detail': 'El link de Google Drive de esta versión no es válido.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        session = http_requests.Session()
        session.headers.update({'User-Agent': BROWSER_USER_AGENT})
        try:
            upstream, iterator, first_chunk = self._open_pdf_stream(
                session, version, file_id
            )
        except _ProxyError as err:
            session.close()
            return Response({'detail': err.detail}, status=err.status)
        except http_requests.Timeout:
            session.close()
            return Response(
                {'detail': 'Google Drive tardó demasiado en responder. '
                           'Intenta de nuevo en unos minutos.'},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except http_requests.ConnectionError:
            session.close()
            return Response(
                {'detail': 'No se pudo conectar con Google Drive. '
                           'Revisa la conexión del servidor.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except http_requests.RequestException:
            session.close()
            logger.exception('Error descargando el PDF de la versión %s', version.id)
            return Response(
                {'detail': 'No se pudo descargar el documento desde Google Drive.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        def stream():
            total = len(first_chunk)
            try:
                yield first_chunk
                for chunk in iterator:
                    total += len(chunk)
                    if total > MAX_PDF_BYTES:
                        logger.warning(
                            'PDF de la versión %s supera 50MB sin declararlo; '
                            'stream cortado', version.id,
                        )
                        return
                    yield chunk
            finally:
                upstream.close()
                session.close()

        response = StreamingHttpResponse(stream(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="{version.nombre_archivo or f"version_{version.id}.pdf"}"'
        )
        response['Cache-Control'] = 'private, max-age=3600'
        return response

    # -- helpers de descarga ------------------------------------------------

    def _open_pdf_stream(self, session, version, file_id):
        """Devuelve (upstream, iterator, first_chunk) listos para retransmitir.

        Lanza _ProxyError (mensaje específico) si Drive no entrega un PDF.
        """
        if file_id:
            upstream = session.get(
                DRIVE_DOWNLOAD_URL,
                params={'id': file_id, 'export': 'download'},
                stream=True,
                timeout=DRIVE_TIMEOUT,
            )
        else:
            upstream = session.get(
                version.url_pdf, stream=True, timeout=DRIVE_TIMEOUT
            )

        upstream, iterator, first_chunk = self._peek(upstream)
        if first_chunk.startswith(b'%PDF'):
            return upstream, iterator, first_chunk

        # Para archivos grandes, Drive responde una página HTML de confirmación
        # antivirus en vez de los bytes; extraemos el token y reintentamos.
        if file_id and self._looks_like_html(upstream, first_chunk):
            html = self._read_text(iterator, first_chunk)
            upstream.close()
            params = self._extract_confirm_params(html)
            if not params:
                raise _ProxyError(
                    'Google Drive no entregó el PDF: el archivo puede ser privado '
                    'o requerir inicio de sesión. Compártelo como «Cualquier '
                    'persona con el enlace».'
                )
            action = params.pop('_action', DRIVE_DOWNLOAD_URL)
            upstream = session.get(
                action, params=params, stream=True, timeout=DRIVE_TIMEOUT
            )
            upstream, iterator, first_chunk = self._peek(upstream)
            if first_chunk.startswith(b'%PDF'):
                return upstream, iterator, first_chunk
            upstream.close()
            raise _ProxyError(
                'El enlace de Google Drive no entregó un PDF tras la confirmación. '
                'Verifica que apunte a un archivo PDF público.'
            )

        upstream.close()
        raise _ProxyError(
            'El archivo no es un PDF accesible. Verifica que el link sea público '
            'y apunte a un PDF.'
        )

    @staticmethod
    def _peek(upstream):
        """Valida status/tamaño y extrae el primer chunk del cuerpo."""
        if upstream.status_code != 200:
            upstream.close()
            raise _ProxyError(
                'Google Drive rechazó la descarga. Verifica que el archivo esté '
                'compartido como «Cualquier persona con el enlace».'
            )

        declared = upstream.headers.get('Content-Length')
        if declared and declared.isdigit() and int(declared) > MAX_PDF_BYTES:
            upstream.close()
            raise _ProxyError(
                'El documento supera el límite de 50 MB. Sube una versión más '
                'liviana.'
            )

        iterator = upstream.iter_content(chunk_size=64 * 1024)
        try:
            first_chunk = next(iterator)
        except StopIteration:
            first_chunk = b''
        return upstream, iterator, first_chunk

    @staticmethod
    def _looks_like_html(upstream, first_chunk):
        ctype = upstream.headers.get('Content-Type', '').lower()
        if 'text/html' in ctype:
            return True
        head = first_chunk.lstrip()[:512].lower()
        return head.startswith(b'<!doctype html') or head.startswith(b'<html')

    @staticmethod
    def _read_text(iterator, first_chunk):
        """Acumula el cuerpo (HTML pequeño) sin reventar memoria."""
        buf = bytearray(first_chunk)
        for chunk in iterator:
            buf.extend(chunk)
            if len(buf) > INTERSTITIAL_MAX_BYTES:
                break
        return buf.decode('utf-8', errors='replace')

    @staticmethod
    def _extract_confirm_params(html):
        """Extrae los campos del formulario de descarga de la página intermedia."""
        params = {name: value for name, value in _HIDDEN_INPUT_RE.findall(html)}
        if not params:
            return None
        action_match = _FORM_ACTION_RE.search(html)
        action = action_match.group(1) if action_match else DRIVE_DOWNLOAD_URL
        params['_action'] = action.replace('&amp;', '&')
        return params


class DefensaView(APIView):
    """Programación y registro del resultado de la defensa de un proyecto."""

    permission_classes = [IsAuthenticated]

    def _get_project(self, request, pk):
        project = ProyectoGrado.objects.filter(pk=pk).first()
        if not project or not puede_ver_proyecto(request.user, project):
            return None
        return project

    def get(self, request, pk):
        project = self._get_project(request, pk)
        if not project:
            return Response(status=status.HTTP_404_NOT_FOUND)
        defensa = Defensa.objects.filter(proyecto=project).first()
        if not defensa:
            return Response(None)
        return Response(DefensaSerializer(defensa).data)

    def post(self, request, pk):
        project = self._get_project(request, pk)
        if not project:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if request.user.rol not in ADMIN_ROLES:
            return Response(
                {'detail': 'Solo la Dirección puede programar defensas.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if Defensa.objects.filter(proyecto=project).exists():
            return Response(
                {'detail': 'Este proyecto ya tiene una defensa. Edítala en lugar de crear otra.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not project.versiones.filter(estado=EstadoVersion.APROBADO).exists():
            return Response(
                {'detail': 'Para programar la defensa el proyecto necesita al menos '
                           'una versión aprobada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DefensaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        defensa = serializer.save(proyecto=project, creado_por=request.user)

        if project.etapa != EtapaProyecto.DEFENSA:
            project.etapa = EtapaProyecto.DEFENSA
            project.save(update_fields=['etapa', 'updated_at'])

        tribunal = [
            rel.docente
            for rel in project.estudiante.tutores_asignados.filter(
                relacion='TRIBUNAL', is_active=True
            ).select_related('docente')
        ]
        fecha = timezone.localtime(defensa.fecha_hora).strftime('%d/%m/%Y %H:%M')
        notify_many(
            [project.estudiante, *tribunal],
            f'La defensa de "{project.titulo}" fue programada para el {fecha}'
            + (f' en {defensa.lugar}.' if defensa.lugar else '.'),
            titulo='Defensa programada',
            categoria=CategoriaNotificacion.RECORDATORIO,
            prioridad=Prioridad.ALTA,
            link=f'/proyectos/{project.id}',
            emisor=request.user,
        )
        logger.info('Defensa programada para el proyecto %s por %s', project.id, request.user.email)
        return Response(DefensaSerializer(defensa).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        project = self._get_project(request, pk)
        if not project:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if request.user.rol not in ADMIN_ROLES:
            return Response(
                {'detail': 'Solo la Dirección puede actualizar la defensa.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        defensa = Defensa.objects.filter(proyecto=project).first()
        if not defensa:
            return Response(
                {'detail': 'Este proyecto aún no tiene una defensa programada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DefensaSerializer(defensa, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        nuevo_estado = serializer.validated_data.get('estado', defensa.estado)
        if nuevo_estado == EstadoDefensa.REALIZADA:
            calificacion = serializer.validated_data.get('calificacion', defensa.calificacion)
            resultado = serializer.validated_data.get('resultado', defensa.resultado)
            if calificacion is None or not resultado:
                return Response(
                    {'detail': 'Para marcar la defensa como realizada debes registrar '
                               'la calificación y el resultado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        defensa = serializer.save()

        if defensa.estado == EstadoDefensa.REALIZADA:
            aprobada = defensa.resultado in (
                ResultadoDefensa.APROBADO,
                ResultadoDefensa.APROBADO_CON_OBSERVACIONES,
            )
            if aprobada and project.estado != EstadoProyecto.CONCLUIDO:
                project.estado = EstadoProyecto.CONCLUIDO
                project.etapa = EtapaProyecto.DEFENSA
                project.save(update_fields=['estado', 'etapa', 'updated_at'])
            notify(
                project.estudiante,
                f'Tu defensa de "{project.titulo}" fue registrada: '
                f'{defensa.get_resultado_display()} con nota {defensa.calificacion}.',
                titulo='Resultado de defensa',
                categoria=CategoriaNotificacion.SISTEMA,
                prioridad=Prioridad.ALTA,
                link=f'/proyectos/{project.id}',
                emisor=request.user,
            )
            logger.info(
                'Defensa del proyecto %s registrada como %s (%s) por %s',
                project.id, defensa.resultado, defensa.calificacion, request.user.email,
            )

        return Response(DefensaSerializer(defensa).data)
