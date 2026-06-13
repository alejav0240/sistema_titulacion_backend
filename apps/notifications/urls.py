from django.urls import path

from apps.notifications.views import (
    EnviarNotificacionView,
    MarkAllReadView,
    MarkReadView,
    NotificacionListView,
    UnreadCountView,
)

urlpatterns = [
    path('notifications/', NotificacionListView.as_view(), name='notifications'),
    path('notifications/unread-count/', UnreadCountView.as_view(), name='notifications_unread'),
    path('notifications/read-all/', MarkAllReadView.as_view(), name='notifications_read_all'),
    path('notifications/send/', EnviarNotificacionView.as_view(), name='notifications_send'),
    path('notifications/<int:pk>/read/', MarkReadView.as_view(), name='notification_read'),
]
