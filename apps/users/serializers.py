import logging
import secrets
from rest_framework import serializers
from apps.users.models import Usuario, Rol
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

class UsuarioSerializer(serializers.ModelSerializer):
    roles_efectivos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'email', 'nombre', 'rol', 'capacidades', 'roles_efectivos',
            'is_active', 'is_staff', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'roles_efectivos', 'created_at', 'updated_at']

    def get_roles_efectivos(self, obj):
        """Rol principal + roles derivados de asignaciones activas."""
        roles = [obj.rol]
        if obj.rol == 'ESTUDIANTE':
            return roles
        relaciones = set(
            obj.estudiantes_tutorados.filter(is_active=True).values_list(
                'relacion', flat=True
            )
        )
        for relacion in ('TUTOR', 'TRIBUNAL'):
            if relacion in relaciones and relacion not in roles:
                roles.append(relacion)
        if obj.materias_impartidas.exists() and 'DOCENTE' not in roles:
            roles.append('DOCENTE')
        return roles

class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    generated_password = serializers.CharField(read_only=True, default=None)
    email_enviado = serializers.BooleanField(read_only=True, default=False)
    sendEmail = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'rol', 'capacidades', 'password', 'is_active', 'generated_password', 'email_enviado', 'sendEmail']

    def create(self, validated_data):
        send_email = validated_data.pop('sendEmail', False)
        password = validated_data.pop('password', None)
        auto_generate = password is None
        if auto_generate:
            password = secrets.token_urlsafe(16)
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()

        user.email_enviado = False
        if send_email:
            try:
                html = render_to_string('emails/welcome.html', {
                    'nombre': user.nombre,
                    'email': user.email,
                    'password': password,
                })
                send_mail(
                    subject='Bienvenido/a al Sistema de Titulación',
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html,
                )
                user.email_enviado = True
            except Exception:
                logger.exception('No se pudo enviar el email de bienvenida a %s', user.email)

        # La contraseña solo viaja en la respuesta cuando el director debe
        # entregarla manualmente (no llegó por email).
        user.generated_password = password if (auto_generate and not user.email_enviado) else None
        return user


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'rol', 'capacidades', 'is_active', 'password']
        extra_kwargs = {
            'email': {'required': False},
            'nombre': {'required': False},
            'rol': {'required': False},
            'capacidades': {'required': False},
            'is_active': {'required': False},
        }

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class UsuarioImportSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError('Solo se permiten archivos CSV')
        return value

    def process_csv(self, file):
        import csv
        from io import TextIOWrapper

        results = {'created': [], 'errors': []}
        decoded = TextIOWrapper(file, encoding='utf-8')
        reader = csv.DictReader(decoded)

        for i, row in enumerate(reader, start=2):
            try:
                email = row.get('email', '').strip()
                nombre = row.get('nombre', '').strip()
                rol = row.get('rol', '').strip().upper()

                if not email or not nombre or not rol:
                    results['errors'].append({'row': i, 'error': 'Campos obligatorios faltantes'})
                    continue

                if rol not in dict(Rol.choices):
                    results['errors'].append({'row': i, 'error': f'Rol invalido: {rol}'})
                    continue

                if Usuario.objects.filter(email=email).exists():
                    results['errors'].append({'row': i, 'error': f'Email ya existe: {email}'})
                    continue

                password = secrets.token_urlsafe(16)
                user = Usuario.objects.create(
                    email=email,
                    nombre=nombre,
                    rol=rol,
                )
                user.set_password(password)
                user.save()

                email_enviado = False
                try:
                    html = render_to_string('emails/welcome.html', {
                        'nombre': nombre,
                        'email': email,
                        'password': password,
                    })
                    send_mail(
                        subject='Bienvenido/a al Sistema de Titulación',
                        message='',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        html_message=html,
                    )
                    email_enviado = True
                except Exception:
                    logger.exception('No se pudo enviar el email de bienvenida a %s', email)

                fila = {
                    'email': email,
                    'nombre': nombre,
                    'rol': rol,
                    'email_enviado': email_enviado,
                }
                if not email_enviado:
                    fila['password'] = password
                results['created'].append(fila)
            except Exception as e:
                results['errors'].append({'row': i, 'error': str(e)})

        return results
