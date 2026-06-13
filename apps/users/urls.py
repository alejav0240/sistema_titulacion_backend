from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.users.views import (
    UsuarioViewSet,
    MeView,
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
)

router = DefaultRouter()

router.register('users', UsuarioViewSet)


urlpatterns = [
    path('users/me/', MeView.as_view(), name='user_me'),
    path('users/me/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    *router.urls,
]
