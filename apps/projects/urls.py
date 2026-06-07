from django.urls import path

from apps.projects.views import ProyectoGradoActiveView, ProyectoGradoListCreateView

urlpatterns = [
    path('projects/', ProyectoGradoListCreateView.as_view(), name='projects'),
    path('projects/active/', ProyectoGradoActiveView.as_view(), name='active_project'),
]

