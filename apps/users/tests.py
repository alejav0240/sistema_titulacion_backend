from django.test import TestCase

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
