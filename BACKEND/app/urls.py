"""
Configuración de URLs principal del proyecto Meet Middleware.

Incluye:
- Django Admin
- API v1 con Django REST Framework
- Documentación automática (Swagger/ReDoc)
- Endpoints de utilidades
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

# Importar ViewSets de Meetings
from meetings.views import (
    MeetingViewSet,
    ParticipantViewSet,
    MeetingRecordingViewSet
)

# Importar ViewSets de Accounts
from accounts.views import UserViewSet, UserManagementViewSet

# Importar vistas de utilidades
from core import views as core_views


# ===== Configurar Router de Django REST Framework =====

router = DefaultRouter()

# Registrar ViewSets de Meetings
router.register(r'meetings', MeetingViewSet, basename='meeting')
router.register(r'participants', ParticipantViewSet, basename='participant')
router.register(r'recordings', MeetingRecordingViewSet, basename='recording')

# Registrar ViewSets de Users
router.register(r'users', UserViewSet, basename='user')
router.register(r'user-management', UserManagementViewSet, basename='user-management')


# ===== Configurar URLpatterns =====

urlpatterns = [
    # ===== Django Admin =====
    path('admin/', admin.site.urls),
    
    # ===== API v1 - Root =====
    path('api/v1/', core_views.api_root, name='api-root'),
    
    # ===== API v1 - Utilidades =====
    path('api/v1/health/', core_views.health_check, name='health-check'),
    path('api/v1/info/', core_views.system_info, name='system-info'),
    
    # ===== API v1 - Documentación (drf-spectacular) =====
    # Schema OpenAPI 3.0 (JSON)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI - Documentación interactiva
    path(
        'api/v1/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    
    # ReDoc - Documentación limpia
    path(
        'api/v1/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),
    
    # ===== API v1 - Endpoints del Router =====
    # Esto incluye todos los ViewSets registrados:
    # - /api/v1/meetings/
    # - /api/v1/participants/
    # - /api/v1/recordings/
    # - /api/v1/users/
    # - /api/v1/user-management/
    path('api/v1/', include(router.urls)),
]


# ===== Serving de archivos estáticos y media en desarrollo =====

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
