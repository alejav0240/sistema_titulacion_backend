from apps.notifications.models import CategoriaNotificacion, Notificacion, Prioridad


def notify(usuario, mensaje, titulo='', categoria=CategoriaNotificacion.SISTEMA,
           prioridad=Prioridad.MEDIA, link='', emisor=None):
    return Notificacion.objects.create(
        usuario=usuario,
        titulo=titulo,
        mensaje=mensaje,
        categoria=categoria,
        prioridad=prioridad,
        link=link,
        emisor=emisor,
    )


def notify_many(usuarios, mensaje, **kwargs):
    return [notify(usuario, mensaje, **kwargs) for usuario in usuarios]


def revisores_de(proyecto):
    """Docentes con relación activa de tutor/tribunal sobre el estudiante."""
    from apps.relationships.models import TutorTribunal

    return [
        rel.docente
        for rel in TutorTribunal.objects.filter(
            estudiante=proyecto.estudiante, is_active=True
        ).select_related('docente')
    ]
