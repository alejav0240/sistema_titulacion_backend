from django.urls import path

from apps.projects.views import (
    DefensaView,
    ProyectoGradoActiveView,
    ProyectoGradoDetailView,
    ProyectoGradoListCreateView,
    VersionDetailView,
    VersionListCreateView,
    VersionPdfProxyView,
    VersionReviewView,
)

urlpatterns = [
    path('projects/', ProyectoGradoListCreateView.as_view(), name='projects'),
    path('projects/active/', ProyectoGradoActiveView.as_view(), name='active_project'),
    path('projects/<int:pk>/', ProyectoGradoDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/defensa/', DefensaView.as_view(), name='project_defensa'),
    path('projects/<int:pk>/versions/', VersionListCreateView.as_view(), name='project_versions'),
    path('versions/<int:pk>/', VersionDetailView.as_view(), name='version_detail'),
    path('versions/<int:pk>/review/', VersionReviewView.as_view(), name='version_review'),
    path('versions/<int:pk>/pdf/', VersionPdfProxyView.as_view(), name='version_pdf'),
]
