from datetime import timedelta
from typing import Any

from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.users.permissions import IsAuthenticated


class CookieTokenObtainPairSerializer(TokenObtainPairSerializer):
    rememberMe = serializers.BooleanField(required=False, default=False)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        if email:
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    raise AuthenticationFailed('Tu cuenta ha sido desactivada. Contacta al administrador.')
                if not user.check_password(password):
                    raise AuthenticationFailed('Credenciales inválidas')
            except User.DoesNotExist:
                raise AuthenticationFailed('Credenciales inválidas')
        
        data = super().validate(attrs)
        remember = attrs.get('rememberMe', False)
        if remember:
            refresh = RefreshToken(data['refresh'])
            refresh.set_exp(lifetime=timedelta(days=30))
            data['refresh'] = str(refresh)
            
        return data


class CookieTokenObtainPairView(TokenObtainPairView):
    serializer_class = CookieTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                'access_token',
                access_token,
                httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTPONLY', True),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
                max_age=int(settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME').total_seconds()),
            )

            remember = request.data.get('rememberMe', False)
            max_age_refresh = 30 * 24 * 60 * 60 if remember else int(settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME').total_seconds())
            
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTPONLY', True),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
                max_age=max_age_refresh
            )
            
            
            response.data.pop('access', None)
            response.data.pop('refresh', None)
        
        return response


# Pal refresh

class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    refresh = serializers.CharField(required = False)
    def validate(self, attrs) :
        attrs['refresh'] = self.context['request'].COOKIES.get('refresh_token')
        return super().validate(attrs)

class CookieTokenRefreshView(TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer
    
    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie('access_token', access_token)
            if refresh_token:
                response.set_cookie('refresh_token', refresh_token)

            response.data.pop('access', None)
            response.data.pop('refresh', None)
        return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def logout(request):
    response = Response({'message': "Sesión Cerrada"})
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response
