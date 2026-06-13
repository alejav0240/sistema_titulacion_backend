from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.users.views import UsuarioViewSet, user_me

router = DefaultRouter()

router.register('users', UsuarioViewSet)


urlpatterns = [
    path('users/me/', user_me, name='user_me'),
    *router.urls,
]