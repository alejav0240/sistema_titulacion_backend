from rest_framework import status
from rest_framework.test import APITestCase

from apps.annotations.models import EstadoAnotacion, Severidad
from apps.projects.models import EstadoProyecto, EstadoVersion, ProyectoGrado, Version
from apps.relationships.models import TipoRelacion, TutorTribunal
from apps.users.models import Rol, Usuario

DRIVE_URL = 'https://drive.google.com/file/d/1aBcDeFgHiJkLmNoPqRsTuVw/view'

RECT = {
    'pagina': 3,
    'x': '0.120000',
    'y': '0.340000',
    'ancho': '0.250000',
    'alto': '0.060000',
}


class AnotacionLifecycleTests(APITestCase):
    def setUp(self):
        self.estudiante = Usuario.objects.create_user(
            email='est@example.com', nombre='Estudiante', password='password123',
            rol=Rol.ESTUDIANTE,
        )
        self.otro_estudiante = Usuario.objects.create_user(
            email='otro@example.com', nombre='Otro', password='password123',
            rol=Rol.ESTUDIANTE,
        )
        self.tutor = Usuario.objects.create_user(
            email='tutor@example.com', nombre='Tutor', password='password123',
            rol=Rol.TUTOR,
        )
        self.proyecto = ProyectoGrado.objects.create(
            titulo='Proyecto demo', estudiante=self.estudiante,
            estado=EstadoProyecto.EN_REVISION,
        )
        TutorTribunal.objects.create(
            estudiante=self.estudiante, docente=self.tutor,
            relacion=TipoRelacion.TUTOR,
        )
        self.version = Version.objects.create(
            proyecto=self.proyecto, numero_version=1,
            url_pdf=DRIVE_URL, estado=EstadoVersion.EN_REVISION,
        )
        self.annotations_url = f'/api/versions/{self.version.id}/annotations/'

    def _crear_anotacion(self):
        self.client.force_authenticate(user=self.tutor)
        response = self.client.post(
            self.annotations_url,
            {**RECT, 'comentario': 'Revisar la bibliografía.', 'severidad': Severidad.CRITICO},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data['id']

    def test_full_lifecycle_with_history(self):
        anotacion_id = self._crear_anotacion()
        base = f'/api/annotations/{anotacion_id}/'

        # Estudiante subsana
        self.client.force_authenticate(user=self.estudiante)
        subsanar = self.client.post(
            base + 'subsanar/', {'comentario': 'Bibliografía corregida.'}, format='json'
        )
        self.assertEqual(subsanar.status_code, status.HTTP_200_OK)
        self.assertEqual(subsanar.data['estado'], EstadoAnotacion.SUBSANADA)

        # Tutor reobserva → vuelve a pendiente
        self.client.force_authenticate(user=self.tutor)
        reobservar = self.client.post(
            base + 'reobservar/', {'feedback': 'Falta la fuente principal.'}, format='json'
        )
        self.assertEqual(reobservar.status_code, status.HTTP_200_OK)
        self.assertEqual(reobservar.data['estado'], EstadoAnotacion.PENDIENTE)

        # Estudiante vuelve a subsanar y el tutor aprueba
        self.client.force_authenticate(user=self.estudiante)
        self.client.post(base + 'subsanar/', {'comentario': 'Fuente añadida.'}, format='json')
        self.client.force_authenticate(user=self.tutor)
        aprobar = self.client.post(base + 'aprobar/', {'feedback': 'Correcto.'}, format='json')
        self.assertEqual(aprobar.status_code, status.HTTP_200_OK)
        self.assertEqual(aprobar.data['estado'], EstadoAnotacion.APROBADA)

        # Historial completo: creación, subsanación, reobservación, subsanación, aprobación
        historial = self.client.get(base + 'historial/')
        self.assertEqual(historial.status_code, status.HTTP_200_OK)
        self.assertEqual(len(historial.data), 5)
        tipos = [evento['tipo'] for evento in historial.data]
        self.assertIn('CREACION', tipos)
        self.assertIn('REOBSERVACION', tipos)
        self.assertIn('APROBACION', tipos)

    def test_cannot_approve_pending_annotation(self):
        anotacion_id = self._crear_anotacion()
        self.client.force_authenticate(user=self.tutor)
        response = self.client.post(
            f'/api/annotations/{anotacion_id}/aprobar/', {}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_create_annotation(self):
        self.client.force_authenticate(user=self.estudiante)
        response = self.client.post(
            self.annotations_url,
            {**RECT, 'comentario': 'x', 'severidad': Severidad.SUGERENCIA},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_foreign_student_cannot_see_annotations(self):
        self._crear_anotacion()
        self.client.force_authenticate(user=self.otro_estudiante)
        response = self.client.get(self.annotations_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_owner_can_subsanar(self):
        anotacion_id = self._crear_anotacion()
        self.client.force_authenticate(user=self.tutor)
        response = self.client.post(
            f'/api/annotations/{anotacion_id}/subsanar/',
            {'comentario': 'no soy el dueño'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
