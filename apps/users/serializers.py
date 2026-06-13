import secrets
from rest_framework import serializers
from apps.users.models import Usuario, Rol
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'nombre', 'rol', 'is_active', 'is_staff', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    generated_password = serializers.CharField(read_only=True)
    sendEmail = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'rol', 'password', 'is_active', 'generated_password', 'sendEmail']

    def create(self, validated_data):
        send_email = validated_data.pop('sendEmail', False)
        password = validated_data.pop('password', None)
        auto_generate = password is None
        if auto_generate:
            password = secrets.token_urlsafe(16)
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        
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
            except Exception:
                pass
        user.generated_password = password
        return user


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'rol', 'is_active', 'password']
        extra_kwargs = {
            'email': {'required': False},
            'nombre': {'required': False},
            'rol': {'required': False},
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

                results['created'].append({
                    'email': email,
                    'nombre': nombre,
                    'rol': rol,
                    'password': password,
                })

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
                except Exception:
                    pass
            except Exception as e:
                results['errors'].append({'row': i, 'error': str(e)})

        return results
