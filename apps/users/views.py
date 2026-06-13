import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.users.models import Usuario
from apps.users.permissions import IsDirectorOrDTC, IsAuthenticated
from apps.users.serializers import UsuarioSerializer, UsuarioCreateSerializer, UsuarioUpdateSerializer, UsuarioImportSerializer

logger = logging.getLogger(__name__)


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()

    def get_queryset(self):
        queryset = Usuario.objects.all().order_by('-created_at')
        rol = self.request.query_params.get('rol')
        estado = self.request.query_params.get('estado')
        busqueda = self.request.query_params.get('search')

        if rol:
            queryset = queryset.filter(rol=rol)
        if estado:
            queryset = queryset.filter(is_active=(estado == 'activo'))
        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda) | Q(email__icontains=busqueda)
            )

        return queryset.order_by('-created_at')
        
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'import_users']:
            return [IsDirectorOrDTC()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UsuarioUpdateSerializer
        if self.action == 'import_users':
            return UsuarioImportSerializer
        return UsuarioSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_users(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = serializer.process_csv(request.data['file'])
        return Response(results, status=status.HTTP_201_CREATED)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request):
        nombre = str(request.data.get('nombre') or '').strip()
        if not nombre:
            return Response({'nombre': ['El nombre no puede estar vacío.']}, status=status.HTTP_400_BAD_REQUEST)
        request.user.nombre = nombre
        request.user.save(update_fields=['nombre'])
        return Response(UsuarioSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password') or ''
        new_password = request.data.get('new_password') or ''
        if not request.user.check_password(old_password):
            return Response(
                {'old_password': ['La contraseña actual es incorrecta.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as exc:
            return Response({'new_password': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        logger.info('Contraseña actualizada por el usuario %s', request.user.email)
        return Response({'detail': 'Contraseña actualizada correctamente.'})


RESPUESTA_FORGOT = {
    'detail': 'Si el correo está registrado, recibirás un enlace para restablecer tu contraseña.'
}


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'forgot'

    def post(self, request):
        email = str(request.data.get('email') or '').strip()
        if not email:
            return Response(RESPUESTA_FORGOT)
        try:
            user = Usuario.objects.get(email__iexact=email, is_active=True)
        except Usuario.DoesNotExist:
            return Response(RESPUESTA_FORGOT)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f'{settings.FRONTEND_URL}/auth/reset-password?uid={uid}&token={token}'
        try:
            html = render_to_string('emails/password_reset.html', {
                'reset_url': reset_url,
                'expiration': '1 hora',
            })
            send_mail(
                subject='Restablecer contraseña - AcademicFlow',
                message=f'Restablece tu contraseña en: {reset_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html,
            )
            logger.info('Email de restablecimiento enviado a %s', user.email)
        except Exception:
            logger.exception('No se pudo enviar el email de restablecimiento a %s', user.email)
        return Response(RESPUESTA_FORGOT)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    ERROR_LINK = {'detail': 'El enlace no es válido o ya expiró. Solicita uno nuevo.'}

    def post(self, request):
        uid = request.data.get('uid') or ''
        token = request.data.get('token') or ''
        new_password = request.data.get('new_password') or ''
        try:
            user = Usuario.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
        except (Usuario.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(self.ERROR_LINK, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, token):
            return Response(self.ERROR_LINK, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({'new_password': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        logger.info('Contraseña restablecida vía email para %s', user.email)
        return Response({'detail': 'Contraseña restablecida. Ya puedes iniciar sesión.'})
