from rest_framework import permissions


DOCENTE_ROLES = ['DOCENTE', 'TUTOR', 'TRIBUNAL']
ADMIN_ROLES = ['DIRECTOR', 'DTC']


class IsDirectorOrDTC(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol in ADMIN_ROLES


class IsDirector(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'DIRECTOR'


class IsDocenteLike(permissions.BasePermission):
    """Cualquier rol con capacidad de revisión/gestión (no estudiante)."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.rol in DOCENTE_ROLES + ADMIN_ROLES
        )


class IsEstudiante(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'ESTUDIANTE'


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated


def es_revisor_de(user, proyecto):
    """True si el usuario puede revisar (anotar) el proyecto."""
    from apps.relationships.models import TutorTribunal
    from apps.academic.models import EstudiantesMateria

    if user.rol in ADMIN_ROLES:
        return True
    if user.rol not in DOCENTE_ROLES:
        return False
    if TutorTribunal.objects.filter(
        docente=user, estudiante=proyecto.estudiante, is_active=True
    ).exists():
        return True
    return EstudiantesMateria.objects.filter(
        estudiante=proyecto.estudiante, materia__docente_a_cargo=user
    ).exists()


def puede_ver_proyecto(user, proyecto):
    """True si el usuario participa del proyecto (dueño, revisor o admin)."""
    if proyecto.estudiante_id == user.id:
        return True
    return es_revisor_de(user, proyecto)
