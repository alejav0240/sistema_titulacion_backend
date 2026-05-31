from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('tutor', 'Tutor'),
        ('tribunal', 'Tribunal'),
        ('admin', 'Administrador'),
    ]
    
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=255)
    isActive = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    rol = models.CharField(max_length=50, choices=ROLE_CHOICES, blank=True, null=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

class Notificacion(models.Model):
    PRIORIDAD_CHOICES = [
        ('nivel1', 'Nivel 1'),
        ('nivel2', 'Nivel 2'),
        ('nivel3', 'Nivel 3'),
    ]
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='nivel1')
    mensaje = models.CharField(max_length=255)
    leida = models.BooleanField(default=False)
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones'
        verbose_name = 'notificación'
        verbose_name_plural = 'notificaciones'
