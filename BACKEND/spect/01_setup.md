Crea un proyecto Django completo para un middleware de videollamadas integrado con Google Meet. Debe usar PostgreSQL como base de datos, exponer APIs REST con Django REST Framework y soportar tareas en segundo plano con Celery + Redis. Primero hazlo funcionar localmente, luego dockerízalo.

El alcance core del middleware es:
- Crear reuniones de Google Meet vía API.
- Registrar en BD la reunión y sus participantes.
- Registrar información básica de grabaciones/seguimiento.
- Exponer endpoints REST limpios y versionados (API-first, sin templates HTML).

## PASO 1: Crear estructura básica del proyecto

meet_middleware/
├── app/
│ ├── init.py
│ ├── asgi.py
│ ├── settings.py
│ ├── urls.py
│ └── wsgi.py
│
├── accounts/
│ ├── init.py
│ ├── admin.py
│ ├── apps.py
│ ├── models.py
│ ├── serializers.py
│ ├── tests.py
│ └── views.py
│
├── meetings/
│ ├── init.py
│ ├── admin.py
│ ├── apps.py
│ ├── models.py
│ ├── serializers.py
│ ├── services.py # Lógica de negocio para creación de reuniones
│ ├── tasks.py # Tareas Celery
│ ├── tests.py
│ └── views.py
│
├── integrations/
│ ├── init.py
│ ├── apps.py
│ ├── google_client.py # Autenticación y peticiones a Google APIs
│ ├── services.py # Servicios de integración Google
│ └── tests.py
│
├── core/
│ ├── init.py
│ ├── utils.py
│ └── exceptions.py
│
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md



### Notas sobre esta estructura

- **app/** contiene la configuración principal de Django.
- **accounts/** maneja usuarios internos y externos (Xoma no usa este login, pero es útil para trazabilidad).
- **meetings/** contiene el dominio principal del middleware: reuniones, participantes, grabaciones.
- **integrations/** centraliza toda la lógica relacionada con Google (Calendar, Meet, Drive).
- **core/** incluye utilidades, excepciones y lógica transversal.
- **Dockerfile** y **docker-compose.yml** permiten levantar todo el stack localmente.

Esta estructura mantiene el proyecto modular, escalable y limpio para futuras extensiones.


## PASO 2: Configurar dependencias

Crea requirements.txt con estas dependencias mínimas:
- Django (>=4.2.0)  
- psycopg2-binary (>=2.9.0)  
- djangorestframework (>=3.14.0)  
- django-cors-headers (>=4.0.0)  
- python-dotenv (>=1.0.0)  
- celery (>=5.3.0)  
- redis (>=5.0.0)  
- google-api-python-client (>=2.120.0)  
- google-auth (>=2.30.0)  
- google-auth-httplib2 (>=0.2.0)  
- google-auth-oauthlib (>=1.2.0)  
- drf-spectacular (>=0.27.0)  


## PASO 3: Configuración de la aplicación Django

En este paso configuramos:

- Base de datos PostgreSQL  
- Apps instaladas (incluyendo DRF, CORS y apps del proyecto)  
- Middleware de CORS  
- Modelo de usuario personalizado  
- Django REST Framework  
- Variables para integración con Google  
- Celery + Redis  
- Archivos estáticos  

---

### 3.1. Imports base

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


### 3.2. INSTALLED_APPS

INSTALLED_APPS = [
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'corsheaders',
    'drf_spectacular',

    # Project apps
    'accounts',
    'meetings',
    'integrations',
]

### 3.3. Middleware (incluyendo CORS)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # debe ir arriba
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True


### 3.4. Configuración de la base de datos PostgreSQL

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', 5432),
    }
}

### 3.5. Usuario personalizado

AUTH_USER_MODEL = 'accounts.User'

### 3.6. Configuración Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        # Para producción, cambiar a JWT
    ],

    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

### 3.7. Variables de Google Workspace (Meet/Calendar/Drive)

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
GOOGLE_WORKSPACE_ADMIN_EMAIL = os.getenv('GOOGLE_WORKSPACE_ADMIN_EMAIL')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

### 3.8. Configuración de Celery + Redis

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')

### 3.9. Archivos estáticos y media

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

### 3.10. Configuración adicional recomendada

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True



## PASO 4: Crear modelos básicos

### `accounts/models.py`

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('service', 'Service User'),
        ('external', 'External User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='external')


### `meetings/models.py`

from django.conf import settings
from django.db import models

class Meeting(models.Model):
    STATUS_CHOICES = (
        ('CREATED', 'Created'),
        ('SCHEDULED', 'Scheduled'),
        ('FINISHED', 'Finished'),
        ('CANCELLED', 'Cancelled'),
    )

    google_event_id = models.CharField(max_length=255, unique=True)
    meet_link = models.URLField()

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='organized_meetings'
    )

    invited_emails = models.JSONField(default=list)

    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='CREATED'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Meeting {self.id} ({self.google_event_id})"


### `meetings/models.py — Modelo de Grabación`
class MeetingRecording(models.Model):
    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name='recording'
    )

    drive_file_id = models.CharField(max_length=255, null=True, blank=True)
    drive_file_url = models.URLField(null=True, blank=True)

    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    available_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recording for Meeting {self.meeting.id}"


### `meetings/models.py — Modelo de Participante`

class Participant(models.Model):
    ROLE_CHOICES = (
        ('organizer', 'Organizer'),
        ('guest', 'Guest'),
    )

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='participants'
    )

    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='guest'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} ({self.role})"



## PASO 5: Serializers (Reciben datos desde Xoma)

###meetings/serializers.py

class MeetingCreateSerializer(serializers.Serializer):
    organizer_email = serializers.EmailField()
    invited_emails = serializers.ListField(
        child=serializers.EmailField()
    )
    scheduled_start = serializers.DateTimeField(required=False)
    scheduled_end = serializers.DateTimeField(required=False)
    external_reference = serializers.CharField(required=False)

class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = "__all__"

## PASO 6: Endpoints (API-first)

###meetings/views.py
class MeetingViewSet(viewsets.ViewSet):
    def create(self, request):
        serializer = MeetingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        meeting = meeting_service.create_meeting(serializer.validated_data)
        return Response(MeetingSerializer(meeting).data, status=201)

    def retrieve(self, request, pk=None):
        meeting = get_object_or_404(Meeting, pk=pk)
        return Response(MeetingSerializer(meeting).data)

    def list(self, request):
        queryset = Meeting.objects.all().order_by('-created_at')
        return Response(MeetingSerializer(queryset, many=True).data)

## PASO 7: Integración con Google

En integrations/google_client.py
- Configurar service account
- Crear un evento en Calendar
- Extraer hangoutLink
- Retornar datos para guardarlos en BD

##PASO 8: URLS

router = DefaultRouter()
router.register('meetings', MeetingViewSet, basename='meetings')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/health/', lambda r: JsonResponse({"status": "ok"})),
]


## PASO 9: Verificar funcionamiento local

Ejecutar:
```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Verificar que respondan:

- http://localhost:8000/admin/ (panel de administración)
- http://localhost:8000/api/health/ (endpoint de salud)
- http://localhost:8000/api/docs/ (documentación de API)

## PASO 10: Crear Dockerfile
- Usar imagen Python 3.11-slim
- Instalar dependencias del sistema para PostgreSQL
- Copiar y instalar dependencias de requirements.txt
- Copiar código de la aplicación
- Exponer puerto 8000
- Configurar comando para ejecutar migraciones y servidor

## PASO 11: Crear docker-compose.yml

Configurar servicios:

**Servicio db:**
- PostgreSQL 15
- Variables de entorno: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- Puerto 5432
- Volume para persistencia de datos

**Servicio redis:**
- Redis para Channels y caché

**Servicio web:**
- Build desde Dockerfile
- Puerto 8000
- Variables de entorno para conexión a DB y Redis
- Depende de los servicios db y redis

**Servicio nginx (opcional para producción):**
- Configuración para servir static files y proxy a Django

## PASO 12: Verificar funcionamiento en Docker
Ejecutar:

```bash
docker-compose up --build
```
Verificar que respondan:

- http://localhost:8000/admin/
- http://localhost:8000/api/health/

## PASO 13: Configurar tareas periódicas (Celery)
Para pagos automáticos y otras tareas:
- sincronizar grabaciones
- verificar estados
- obtener metadatos de Drive

## PASO 14: API mínima que Xoma usará

Crear reunión (principal)
POST /api/v1/meetings/

Body:

{
  "organizer_email": "doctor@clinica.com",
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-11-25T15:00:00Z",
  "scheduled_end": "2025-11-25T15:30:00Z",
  "external_reference": "xoma_appointment_1234"
}


Respuesta:

{
  "id": 12,
  "google_event_id": "event123",
  "meet_link": "https://meet.google.com/abc-defg-hij",
  "invited_emails": [...],
  "status": "CREATED"
}

## NOTAS ADICIONALES:
- Diseño API-first, sin HTML.
- recibirá datos directamente desde Xoma.
- meeting_service centraliza la lógica.
- Integración limpia y escalable.

El proyecto debe seguir las mejores prácticas de Django y ser escalable para implementar todas las historias de usuario descritas.