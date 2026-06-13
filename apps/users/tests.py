from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Rol, Usuario


class UsuarioManagerTests(TestCase):
    def test_create_superuser_sets_required_admin_flags_and_role(self):
        user = Usuario.objects.create_superuser(
            email='admin@example.com',
            nombre='Admin',
            password='password123',
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.rol, Rol.DIRECTOR)


class ChangePasswordTests(APITestCase):
    URL = '/api/users/me/change-password/'

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email='ana@example.com',
            nombre='Ana',
            password='ClaveActual99',
            rol=Rol.ESTUDIANTE,
        )
        self.client.force_authenticate(user=self.user)

    def test_rejects_wrong_old_password(self):
        response = self.client.post(
            self.URL,
            {'old_password': 'incorrecta', 'new_password': 'NuevaClave2026'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)

    def test_rejects_weak_new_password(self):
        response = self.client.post(
            self.URL,
            {'old_password': 'ClaveActual99', 'new_password': '123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

    def test_changes_password(self):
        response = self.client.post(
            self.URL,
            {'old_password': 'ClaveActual99', 'new_password': 'NuevaClave2026'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave2026'))


class MeProfileTests(APITestCase):
    URL = '/api/users/me/'

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email='ana@example.com',
            nombre='Ana',
            password='ClaveActual99',
            rol=Rol.ESTUDIANTE,
        )
        self.client.force_authenticate(user=self.user)

    def test_patch_updates_own_name(self):
        response = self.client.patch(self.URL, {'nombre': 'Ana García'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.nombre, 'Ana García')

    def test_patch_rejects_empty_name(self):
        response = self.client.patch(self.URL, {'nombre': '  '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetTests(APITestCase):
    FORGOT_URL = '/api/auth/forgot-password/'
    RESET_URL = '/api/auth/reset-password/'

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email='ana@example.com',
            nombre='Ana',
            password='ClaveActual99',
            rol=Rol.ESTUDIANTE,
        )

    def test_forgot_always_returns_200(self):
        existe = self.client.post(self.FORGOT_URL, {'email': 'ana@example.com'}, format='json')
        no_existe = self.client.post(self.FORGOT_URL, {'email': 'nadie@example.com'}, format='json')
        self.assertEqual(existe.status_code, status.HTTP_200_OK)
        self.assertEqual(no_existe.status_code, status.HTTP_200_OK)
        # Solo el email registrado recibe correo
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/auth/reset-password?uid=', mail.outbox[0].body)

    def test_reset_rejects_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.post(
            self.RESET_URL,
            {'uid': uid, 'token': 'token-invalido', 'new_password': 'NuevaClave2026'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_with_valid_token_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.post(
            self.RESET_URL,
            {'uid': uid, 'token': token, 'new_password': 'NuevaClave2026'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave2026'))
        # El token es de un solo uso
        repetida = self.client.post(
            self.RESET_URL,
            {'uid': uid, 'token': token, 'new_password': 'OtraClave2026'},
            format='json',
        )
        self.assertEqual(repetida.status_code, status.HTTP_400_BAD_REQUEST)


class CrearUsuarioPasswordTests(APITestCase):
    URL = '/api/users/'

    def setUp(self):
        self.director = Usuario.objects.create_user(
            email='director@example.com',
            nombre='Director',
            password='password123',
            rol=Rol.DIRECTOR,
        )
        self.client.force_authenticate(user=self.director)

    def test_password_not_in_response_when_emailed(self):
        response = self.client.post(
            self.URL,
            {'email': 'nuevo@example.com', 'nombre': 'Nuevo', 'rol': 'DOCENTE', 'sendEmail': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['email_enviado'])
        self.assertIsNone(response.data.get('generated_password'))
        self.assertEqual(len(mail.outbox), 1)

    def test_password_returned_once_when_not_emailed(self):
        response = self.client.post(
            self.URL,
            {'email': 'nuevo@example.com', 'nombre': 'Nuevo', 'rol': 'DOCENTE', 'sendEmail': False},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['email_enviado'])
        self.assertTrue(response.data['generated_password'])
        self.assertEqual(len(mail.outbox), 0)
