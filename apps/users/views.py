from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

from apps.users.models import Usuario
from apps.users.permissions import IsDirectorOrDTC, IsAuthenticated
from apps.users.serializers import UsuarioSerializer, UsuarioCreateSerializer, UsuarioUpdateSerializer, UsuarioImportSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()

    def get_queryset(self):
        queryset = Usuario.objects.all()
        rol = self.request.query_params.get('rol')
        estado = self.request.query_params.get('estado')
        busqueda = self.request.query_params.get('search')
        
        if rol:
            queryset = queryset.filter(rol=rol)
        if estado:
            queryset = queryset.filter(is_active=(estado == 'activo'))
        if busqueda:
            queryset = queryset.filter(nombre__icontains=busqueda, email__icontains=busqueda)
            
        return queryset
        
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'import_users']:
            return [IsDirectorOrDTC()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UsuarioUpdateSerializer
        if self.action == 'import_users':
            return UsuarioImportSerializer
        return UsuarioSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_users(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = serializer.process_csv(request.data['file'])
        return Response(results, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_me(request):
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)
