from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Rol(models.TextChoices):
    DOCENTE = 'DOCENTE'
    TRIBUNAL = 'TRIBUNAL'
    TUTOR = 'TUTOR'
    ESTUDIANTE = 'ESTUDIANTE'
    DIRECTOR = 'DIRECTOR'
    DTC = 'DTC'


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, password, rol, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, rol=rol, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', Rol.DIRECTOR)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True')

        return self.create_user(email, nombre, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ESTUDIANTE)
    # Flags informativos del perfil (p.ej. "TIEMPO_COMPLETO"); los roles efectivos
    # de tutor/tribunal se derivan de TutorTribunal y de las materias a cargo
    capacidades = models.JSONField(default=list, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_staff = models.BooleanField(default=False)
    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return f"{self.nombre} ({self.email})"
