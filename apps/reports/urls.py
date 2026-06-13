from django.urls import path

from apps.reports.analytics import AnalyticsView
from apps.reports.exports import ProjectsExportView, ReportExportView
from apps.reports.views import (
    DirectorDashboardView,
    StudentDashboardView,
    TeacherDashboardView,
)

urlpatterns = [
    path('dashboard/student/', StudentDashboardView.as_view(), name='dashboard_student'),
    path('dashboard/teacher/', TeacherDashboardView.as_view(), name='dashboard_teacher'),
    path('dashboard/director/', DirectorDashboardView.as_view(), name='dashboard_director'),
    path('reports/analytics/', AnalyticsView.as_view(), name='reports_analytics'),
    path('reports/export/', ReportExportView.as_view(), name='reports_export'),
    path('projects/export/', ProjectsExportView.as_view(), name='projects_export'),
]
