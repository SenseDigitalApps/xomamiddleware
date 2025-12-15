"""
Vistas utilitarias y transversales del proyecto.

Incluye:
- Health check endpoint
- Endpoints de información del sistema
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.conf import settings
import sys


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint de health check para verificar que el sistema está funcionando.
    
    URL: GET /api/v1/health/
    
    Verifica:
    - API está respondiendo
    - Base de datos está accesible
    
    Returns:
        200: Sistema funcionando correctamente
        503: Sistema con problemas
    """
    health_status = {
        'status': 'ok',
        'api': 'running',
        'database': 'unknown',
    }
    
    # Verificar conexión a base de datos
    try:
        connection.ensure_connection()
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['status'] = 'degraded'
        health_status['database'] = 'disconnected'
        health_status['database_error'] = str(e)
        
        return Response(
            health_status,
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return Response(health_status, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def system_info(request):
    """
    Endpoint con información del sistema.
    
    URL: GET /api/v1/info/
    
    Returns:
        200: Información del sistema
    """
    info = {
        'project': 'Meet Middleware',
        'description': 'API para integración de Google Meet con XOMA',
        'version': '1.0.0',
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'django_version': settings.VERSION if hasattr(settings, 'VERSION') else 'Unknown',
        'debug_mode': settings.DEBUG,
        'environment': 'development' if settings.DEBUG else 'production',
        'api_base_url': '/api/v1/',
        'docs_url': '/api/v1/docs/',
    }
    
    return Response(info, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    Endpoint raíz de la API con enlaces a recursos disponibles.
    
    URL: GET /api/v1/
    
    Returns:
        200: Enlaces a recursos de la API
    """
    return Response({
        'message': 'Meet Middleware API - XOMA Integration',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/v1/health/',
            'info': '/api/v1/info/',
            'docs': '/api/v1/docs/',
            'meetings': '/api/v1/meetings/',
            'users': '/api/v1/users/',
            'recordings': '/api/v1/recordings/',
            'participants': '/api/v1/participants/',
        },
        'documentation': {
            'integration_guide': 'Ver XOMA_INTEGRATION_GUIDE.md',
            'models': 'Ver MODELS_DOCUMENTATION.md',
            'serializers': 'Ver SERIALIZERS_DOCUMENTATION.md',
        }
    }, status=status.HTTP_200_OK)
