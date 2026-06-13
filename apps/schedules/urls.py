from django.urls import path

from apps.schedules.views import CronogramaDetailView, CronogramaListCreateView

urlpatterns = [
    path('schedules/', CronogramaListCreateView.as_view(), name='schedules'),
    path('schedules/<int:pk>/', CronogramaDetailView.as_view(), name='schedule_detail'),
]
