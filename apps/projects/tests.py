from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.projects.models import EstadoProyecto, ProyectoGrado
from apps.users.models import Rol, Usuario


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
