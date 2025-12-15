"""
ViewSets para la aplicación de cuentas de usuario.

Expone endpoints REST para:
- Listar usuarios
- Consultar detalles de usuarios
- Obtener información del usuario autenticado
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer
)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para usuarios.
    
    Endpoints:
    - GET /users/ - Listar usuarios
    - GET /users/{id}/ - Detalle de usuario
    - GET /users/me/ - Usuario autenticado actual
    """
    
    queryset = User.objects.filter(is_active=True).order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # En producción: IsAuthenticated
    
    def get_queryset(self):
        """
        Permite filtrar usuarios por query params.
        
        Query Parameters:
            - role: Filtrar por rol (admin, service, external)
            - email: Buscar por email (parcial)
            - username: Buscar por username (parcial)
        """
        queryset = super().get_queryset()
        
        role = self.request.query_params.get('role')
        email = self.request.query_params.get('email')
        username = self.request.query_params.get('username')
        
        if role:
            queryset = queryset.filter(role=role)
        
        if email:
            queryset = queryset.filter(email__icontains=email)
        
        if username:
            queryset = queryset.filter(username__icontains=username)
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def me(self, request):
        """
        Retorna información del usuario autenticado actual.
        
        Custom endpoint: GET /users/me/
        
        Returns:
            200: Información del usuario
            401: No autenticado (en producción con IsAuthenticated)
        """
        # En desarrollo con AllowAny, verificar si hay usuario
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'message': 'Usuario no autenticado'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Retorna estadísticas de usuarios.
        
        Custom endpoint: GET /users/stats/
        
        Returns:
            200: Estadísticas de usuarios
        """
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        stats_by_role = {
            'admin': User.objects.filter(role='admin').count(),
            'service': User.objects.filter(role='service').count(),
            'external': User.objects.filter(role='external').count(),
        }
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'by_role': stats_by_role
        })


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet completo para gestión de usuarios (CRUD).
    
    Este ViewSet está separado del ReadOnlyModelViewSet
    para tener control fino sobre los permisos de escritura.
    
    Endpoints:
    - POST /user-management/ - Crear usuario
    - GET /user-management/ - Listar usuarios
    - GET /user-management/{id}/ - Detalle de usuario
    - PUT/PATCH /user-management/{id}/ - Actualizar usuario
    - DELETE /user-management/{id}/ - Desactivar usuario
    - POST /user-management/{id}/change-password/ - Cambiar password
    """
    
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [AllowAny]  # En producción: IsAdminUser
    
    def get_serializer_class(self):
        """
        Retorna el serializer apropiado según la acción.
        """
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        else:
            return UserSerializer
    
    def destroy(self, request, *args, **kwargs):
        """
        Desactiva un usuario en lugar de eliminarlo (soft delete).
        
        Returns:
            200: Usuario desactivado
            404: Usuario no encontrado
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        
        return Response(
            {
                'message': 'Usuario desactivado exitosamente',
                'user_id': user.id,
                'username': user.username
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Cambia la contraseña de un usuario.
        
        Custom endpoint: POST /user-management/{id}/change-password/
        
        Body:
            - old_password: Contraseña actual
            - new_password: Nueva contraseña
            - new_password_confirm: Confirmación de nueva contraseña
        
        Returns:
            200: Contraseña cambiada exitosamente
            400: Datos inválidos o contraseña actual incorrecta
            404: Usuario no encontrado
        """
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            # Verificar contraseña actual
            if not user.check_password(serializer.data.get('old_password')):
                return Response(
                    {'old_password': ['Contraseña actual incorrecta']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Establecer nueva contraseña
            user.set_password(serializer.data.get('new_password'))
            user.save()
            
            return Response(
                {'message': 'Contraseña cambiada exitosamente'},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activa un usuario desactivado.
        
        Custom endpoint: POST /user-management/{id}/activate/
        
        Returns:
            200: Usuario activado
            404: Usuario no encontrado
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response(
            {
                'message': 'Usuario activado exitosamente',
                'user_id': user.id,
                'username': user.username
            },
            status=status.HTTP_200_OK
        )
