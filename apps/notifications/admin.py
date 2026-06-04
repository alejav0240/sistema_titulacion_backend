from django.contrib import admin
from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'prioridad', 'leido', 'created_at')
    list_filter = ('prioridad', 'leido', 'created_at')
    search_fields = ('usuario__nombre', 'mensaje')