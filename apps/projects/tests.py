from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.projects.models import (
    Defensa,
    EstadoDefensa,
    EstadoProyecto,
    EstadoVersion,
    EtapaProyecto,
    ProyectoGrado,
    Version,
    extract_drive_file_id,
)
from apps.relationships.models import TipoRelacion, TutorTribunal
from apps.users.models import Rol, Usuario

DRIVE_URL = 'https://drive.google.com/file/d/1aBcDeFgHiJkLmNoPqRsTuVw/view'


def crear_actores():
    """Estudiante con proyecto, tutor asignado y director."""
    estudiante = Usuario.objects.create_user(
        email='est@example.com', nombre='Estudiante', password='password123',
        rol=Rol.ESTUDIANTE,
    )
    tutor = Usuario.objects.create_user(
        email='tutor@example.com', nombre='Tutor', password='password123',
        rol=Rol.TUTOR,
    )
    director = Usuario.objects.create_user(
        email='dir@example.com', nombre='Director', password='password123',
        rol=Rol.DIRECTOR,
    )
    proyecto = ProyectoGrado.objects.create(
        titulo='Proyecto demo', estudiante=estudiante,
        estado=EstadoProyecto.EN_REVISION,
    )
    TutorTribunal.objects.create(
        estudiante=estudiante, docente=tutor, relacion=TipoRelacion.TUTOR,
    )
    return estudiante, tutor, director, proyecto


class ProyectoGradoApiTests(APITestCase):
    def setUp(self):
        self.student = Usuario.objects.create_user(
            email='estudiante@example.com',
            nombre='Estudiante Uno',
            password='password123',
            rol=Rol.ESTUDIANTE,
        )
        self.director = Usuario.objects.create_user(
            email='director@example.com',
            nombre='Director Uno',
            password='password123',
            rol=Rol.DIRECTOR,
        )
        self.projects_url = reverse('projects')
        self.active_project_url = reverse('active_project')

    def test_student_can_register_project(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.projects_url,
            {'titulo': 'Optimizacion de procesos academicos'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        project = ProyectoGrado.objects.get()
        self.assertEqual(project.titulo, 'Optimizacion de procesos academicos')
        self.assertEqual(project.estudiante, self.student)
        self.assertEqual(project.estado, EstadoProyecto.EN_REVISION)
        self.assertIsNotNone(project.created_at)
        self.assertEqual(response.data['estudiante'], self.student.id)
        self.assertEqual(response.data['estado'], EstadoProyecto.EN_REVISION)
        self.assertIn('created_at', response.data)

    def test_student_cannot_register_second_active_project(self):
        ProyectoGrado.objects.create(
            titulo='Proyecto existente',
            estudiante=self.student,
            estado=EstadoProyecto.EN_REVISION,
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.projects_url,
            {'titulo': 'Nuevo proyecto'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ProyectoGrado.objects.count(), 1)

    def test_student_can_register_project_after_concluded_project(self):
        ProyectoGrado.objects.create(
            titulo='Proyecto concluido',
            estudiante=self.student,
            estado=EstadoProyecto.CONCLUIDO,
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.projects_url,
            {'titulo': 'Nuevo proyecto'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProyectoGrado.objects.count(), 2)

    def test_non_student_cannot_register_project(self):
        self.client.force_authenticate(user=self.director)

        response = self.client.post(
            self.projects_url,
            {'titulo': 'Proyecto director'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ProyectoGrado.objects.count(), 0)

    def test_active_project_endpoint_returns_current_student_project(self):
        project = ProyectoGrado.objects.create(
            titulo='Proyecto activo',
            estudiante=self.student,
            estado=EstadoProyecto.EN_REVISION,
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.active_project_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['project']['id'], project.id)

    def test_active_project_endpoint_returns_null_without_active_project(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.active_project_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['project'])


class DriveFileIdTests(TestCase):
    def test_extracts_id_from_known_formats(self):
        file_id = '1aBcDeFgHiJkLmNoPqRsTuVw'
        urls = [
            f'https://drive.google.com/file/d/{file_id}/view?usp=sharing',
            f'https://drive.google.com/open?id={file_id}',
            f'https://drive.google.com/uc?export=download&id={file_id}',
        ]
        for url in urls:
            self.assertEqual(extract_drive_file_id(url), file_id, url)

    def test_returns_none_for_invalid_urls(self):
        for url in ['https://example.com/doc.docx', 'no-es-url', '', None]:
            self.assertIsNone(extract_drive_file_id(url))


class EtapaTransitionTests(APITestCase):
    def setUp(self):
        self.estudiante, self.tutor, self.director, self.proyecto = crear_actores()
        self.url = f'/api/projects/{self.proyecto.id}/'

    def _patch_etapa(self, user, etapa):
        self.client.force_authenticate(user=user)
        return self.client.patch(self.url, {'etapa': etapa}, format='json')

    def test_revisor_advances_one_stage(self):
        response = self._patch_etapa(self.tutor, EtapaProyecto.ANTEPROYECTO)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.etapa, EtapaProyecto.ANTEPROYECTO)

    def test_cannot_skip_stages(self):
        response = self._patch_etapa(self.tutor, EtapaProyecto.DESARROLLO)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_admin_can_go_back(self):
        self.proyecto.etapa = EtapaProyecto.DESARROLLO
        self.proyecto.save(update_fields=['etapa'])
        tutor_atras = self._patch_etapa(self.tutor, EtapaProyecto.ANTEPROYECTO)
        self.assertEqual(tutor_atras.status_code, status.HTTP_400_BAD_REQUEST)
        director_atras = self._patch_etapa(self.director, EtapaProyecto.ANTEPROYECTO)
        self.assertEqual(director_atras.status_code, status.HTTP_200_OK)

    def test_defensa_requires_approved_version(self):
        self.proyecto.etapa = EtapaProyecto.REVISION
        self.proyecto.save(update_fields=['etapa'])
        sin_version = self._patch_etapa(self.director, EtapaProyecto.DEFENSA)
        self.assertEqual(sin_version.status_code, status.HTTP_400_BAD_REQUEST)

        Version.objects.create(
            proyecto=self.proyecto, numero_version=1,
            url_pdf=DRIVE_URL, estado=EstadoVersion.APROBADO,
        )
        con_version = self._patch_etapa(self.director, EtapaProyecto.DEFENSA)
        self.assertEqual(con_version.status_code, status.HTTP_200_OK)


class VersionDeleteTests(APITestCase):
    def setUp(self):
        self.estudiante, self.tutor, self.director, self.proyecto = crear_actores()
        self.v1 = Version.objects.create(
            proyecto=self.proyecto, numero_version=1,
            url_pdf=DRIVE_URL, estado=EstadoVersion.OBSERVADO,
        )
        self.v2 = Version.objects.create(
            proyecto=self.proyecto, numero_version=2,
            url_pdf=DRIVE_URL, estado=EstadoVersion.EN_REVISION,
        )

    def test_owner_deletes_last_unreviewed_version(self):
        self.client.force_authenticate(user=self.estudiante)
        response = self.client.delete(f'/api/versions/{self.v2.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Version.objects.filter(pk=self.v2.pk).exists())

    def test_cannot_delete_non_last_version(self):
        self.client.force_authenticate(user=self.estudiante)
        response = self.client.delete(f'/api/versions/{self.v1.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_delete_reviewed_version(self):
        self.v2.estado = EstadoVersion.APROBADO
        self.v2.save(update_fields=['estado'])
        self.client.force_authenticate(user=self.estudiante)
        response = self.client.delete(f'/api/versions/{self.v2.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reviewer_cannot_delete(self):
        self.client.force_authenticate(user=self.tutor)
        response = self.client.delete(f'/api/versions/{self.v2.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class VersionReviewAuditTests(APITestCase):
    def setUp(self):
        self.estudiante, self.tutor, self.director, self.proyecto = crear_actores()
        self.version = Version.objects.create(
            proyecto=self.proyecto, numero_version=1,
            url_pdf=DRIVE_URL, estado=EstadoVersion.EN_REVISION,
        )

    def test_review_records_who_and_when(self):
        self.client.force_authenticate(user=self.tutor)
        response = self.client.post(
            f'/api/versions/{self.version.id}/review/',
            {'accion': 'APROBAR'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.version.refresh_from_db()
        self.assertEqual(self.version.revisada_por, self.tutor)
        self.assertIsNotNone(self.version.revisada_el)


class DefensaTests(APITestCase):
    def setUp(self):
        self.estudiante, self.tutor, self.director, self.proyecto = crear_actores()
        self.url = f'/api/projects/{self.proyecto.id}/defensa/'

    def _aprobar_version(self):
        Version.objects.create(
            proyecto=self.proyecto, numero_version=1,
            url_pdf=DRIVE_URL, estado=EstadoVersion.APROBADO,
        )

    def test_requires_approved_version(self):
        self.client.force_authenticate(user=self.director)
        response = self.client.post(
            self.url, {'fecha_hora': '2026-08-15T10:00:00Z'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_admin_can_schedule(self):
        self._aprobar_version()
        self.client.force_authenticate(user=self.tutor)
        response = self.client.post(
            self.url, {'fecha_hora': '2026-08-15T10:00:00Z'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_schedule_moves_project_to_defensa_stage(self):
        self._aprobar_version()
        self.client.force_authenticate(user=self.director)
        response = self.client.post(
            self.url,
            {'fecha_hora': '2026-08-15T10:00:00Z', 'lugar': 'Auditorio A'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.etapa, EtapaProyecto.DEFENSA)

    def test_realizada_requires_grade_and_result(self):
        self._aprobar_version()
        Defensa.objects.create(
            proyecto=self.proyecto, fecha_hora='2026-08-15T10:00:00Z',
            creado_por=self.director,
        )
        self.client.force_authenticate(user=self.director)
        response = self.client.patch(
            self.url, {'estado': EstadoDefensa.REALIZADA}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approved_defense_concludes_project(self):
        self._aprobar_version()
        Defensa.objects.create(
            proyecto=self.proyecto, fecha_hora='2026-08-15T10:00:00Z',
            creado_por=self.director,
        )
        self.client.force_authenticate(user=self.director)
        response = self.client.patch(
            self.url,
            {
                'estado': EstadoDefensa.REALIZADA,
                'calificacion': '85.00',
                'resultado': 'APROBADO',
                'acta_url': 'https://drive.google.com/file/d/1aBcDeFgHiJkLmNoPqRsTuVw/view',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, EstadoProyecto.CONCLUIDO)
        self.assertEqual(self.proyecto.etapa, EtapaProyecto.DEFENSA)
