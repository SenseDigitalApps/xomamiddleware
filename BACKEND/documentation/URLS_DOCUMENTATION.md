# Documentación de URLs - Meet Middleware

## Resumen

Este documento describe la configuración completa de URLs del middleware, incluyendo especificaciones de endpoints, métodos HTTP y parámetros de consulta.

**URL Base del Sistema:** `http://localhost:8000`

---

## Mapa de URLs del Sistema

### Panel de Administración Django

| URL | Descripción |
|-----|-------------|
| /admin/ | Panel de administración de Django |

**Requisito de Acceso:** Usuario con privilegios de superusuario

**Credenciales Actuales:**
- Usuario: admin
- Contraseña: Admin123!

---

### Documentación de API - Versión 1

| URL | Descripción | Herramienta |
|-----|-------------|-------------|
| /api/v1/schema/ | Especificación OpenAPI 3.0 (formato JSON) | drf-spectacular |
| /api/v1/docs/ | Documentación interactiva (Swagger UI) | drf-spectacular |
| /api/v1/redoc/ | Documentación formal (ReDoc) | drf-spectacular |

**Recomendación:** Utilizar /api/v1/docs/ para testing interactivo de endpoints.

---

### Endpoints de Utilidades

| URL | Vista | Método | Descripción |
|-----|-------|--------|-------------|
| /api/v1/ | api_root | GET | Punto de entrada de la API con referencias |
| /api/v1/health/ | health_check | GET | Verificación de estado del sistema |
| /api/v1/info/ | system_info | GET | Información del sistema y versiones |

---

### Endpoints de Gestión de Reuniones

**ViewSet:** MeetingViewSet  
**Basename:** meeting

| URL | Nombre de Ruta | Método | Acción | Descripción |
|-----|---------------|--------|--------|-------------|
| /api/v1/meetings/ | meeting-list | GET | list() | Listado de reuniones |
| /api/v1/meetings/ | meeting-list | POST | create() | Creación de reunión |
| /api/v1/meetings/{id}/ | meeting-detail | GET | retrieve() | Detalle de reunión |
| /api/v1/meetings/{id}/ | meeting-detail | PATCH | partial_update() | Actualización parcial |
| /api/v1/meetings/{id}/ | meeting-detail | DELETE | destroy() | Cancelación de reunión |
| /api/v1/meetings/{id}/recording/ | meeting-recording | GET | recording() | Obtención de grabación |
| /api/v1/meetings/{id}/participants/ | meeting-participants | GET | participants() | Listado de participantes |

**Parámetros de Consulta (list):**

- `organizer` - Filtrado por ID de organizador
- `status` - Filtrado por estado (CREATED, SCHEDULED, FINISHED, CANCELLED)
- `scheduled_start__gte` - Filtrado por fecha mínima
- `scheduled_start__lte` - Filtrado por fecha máxima

**Ejemplos de Uso:**

```bash
# Listado completo
GET /api/v1/meetings/

# Creación de reunión
POST /api/v1/meetings/
{
  "organizer_email": "doctor@clinica.com",
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-11-25T15:00:00Z",
  "scheduled_end": "2025-11-25T15:30:00Z"
}

# Detalle de reunión específica
GET /api/v1/meetings/12/

# Obtención de grabación
GET /api/v1/meetings/12/recording/

# Filtrado por organizador
GET /api/v1/meetings/?organizer=1

# Filtrado por estado
GET /api/v1/meetings/?status=FINISHED
```

---

### Endpoints de Gestión de Participantes

**ViewSet:** ParticipantViewSet  
**Basename:** participant

| URL | Nombre de Ruta | Método | Acción | Descripción |
|-----|---------------|--------|--------|-------------|
| /api/v1/participants/ | participant-list | GET | list() | Listado de participantes |
| /api/v1/participants/{id}/ | participant-detail | GET | retrieve() | Detalle de participante |

**Parámetros de Consulta:**

- `meeting` - Filtrado por ID de reunión

---

### Endpoints de Gestión de Grabaciones

**ViewSet:** MeetingRecordingViewSet  
**Basename:** recording

| URL | Nombre de Ruta | Método | Acción | Descripción |
|-----|---------------|--------|--------|-------------|
| /api/v1/recordings/ | recording-list | GET | list() | Listado de grabaciones |
| /api/v1/recordings/{id}/ | recording-detail | GET | retrieve() | Detalle de grabación |

**Parámetros de Consulta:**

- `meeting` - Filtrado por ID de reunión

---

### Endpoints de Gestión de Usuarios

**ViewSet:** UserViewSet  
**Basename:** user

| URL | Nombre de Ruta | Método | Acción | Descripción |
|-----|---------------|--------|--------|-------------|
| /api/v1/users/ | user-list | GET | list() | Listado de usuarios activos |
| /api/v1/users/{id}/ | user-detail | GET | retrieve() | Detalle de usuario |
| /api/v1/users/me/ | user-me | GET | me() | Usuario autenticado actual |
| /api/v1/users/stats/ | user-stats | GET | stats() | Estadísticas de usuarios |

**Parámetros de Consulta:**

- `role` - Filtrado por rol (admin, service, external)
- `email` - Búsqueda por correo (coincidencia parcial)
- `username` - Búsqueda por nombre de usuario (coincidencia parcial)

---

### Endpoints de Administración de Usuarios

**ViewSet:** UserManagementViewSet  
**Basename:** user-management

| URL | Nombre de Ruta | Método | Acción | Descripción |
|-----|---------------|--------|--------|-------------|
| /api/v1/user-management/ | user-management-list | GET | list() | Listado completo |
| /api/v1/user-management/ | user-management-list | POST | create() | Creación de usuario |
| /api/v1/user-management/{id}/ | user-management-detail | GET | retrieve() | Detalle |
| /api/v1/user-management/{id}/ | user-management-detail | PUT | update() | Actualización completa |
| /api/v1/user-management/{id}/ | user-management-detail | PATCH | partial_update() | Actualización parcial |
| /api/v1/user-management/{id}/ | user-management-detail | DELETE | destroy() | Desactivación de usuario |
| /api/v1/user-management/{id}/change-password/ | user-management-change-password | POST | change_password() | Cambio de contraseña |
| /api/v1/user-management/{id}/activate/ | user-management-activate | POST | activate() | Activación de usuario |

---

## Resumen Cuantitativo de Endpoints

| Categoría | Cantidad de Endpoints | ViewSets Asociados |
|-----------|----------------------|-------------------|
| Reuniones | 7 | 1 ViewSet + 2 acciones personalizadas |
| Participantes | 2 | 1 ViewSet (solo lectura) |
| Grabaciones | 2 | 1 ViewSet (solo lectura) |
| Usuarios | 4 | 1 ViewSet + 2 acciones personalizadas |
| Administración de Usuarios | 8 | 1 ViewSet CRUD completo + 2 acciones |
| Utilidades | 3 | Vistas funcionales |
| Documentación | 3 | drf-spectacular |
| Panel de Administración | 1 | Django Admin |
| **TOTAL** | **30** | **5 ViewSets** |

---

## Sistema de Nombres de Rutas

Django genera nombres automáticos para cada URL, útiles para uso programático con reverse():

### Reuniones

- meeting-list
- meeting-detail
- meeting-recording
- meeting-participants

### Participantes

- participant-list
- participant-detail

### Grabaciones

- recording-list
- recording-detail

### Usuarios

- user-list
- user-detail
- user-me
- user-stats

### Administración de Usuarios

- user-management-list
- user-management-detail
- user-management-change-password
- user-management-activate

**Uso Programático:**

```python
from django.urls import reverse

url = reverse('meeting-list')  # '/api/v1/meetings/'
url = reverse('meeting-detail', args=[12])  # '/api/v1/meetings/12/'
```

---

## Métodos de Testing de Endpoints

### Opción 1: Navegador Web (GET requests)

- http://localhost:8000/api/v1/docs/ (Swagger UI - Recomendado)
- http://localhost:8000/api/v1/meetings/
- http://localhost:8000/api/v1/health/

### Opción 2: cURL

```bash
# Verificación de estado
curl http://localhost:8000/api/v1/health/

# Listado de reuniones
curl http://localhost:8000/api/v1/meetings/

# Creación de reunión
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_email": "doctor@clinica.com",
    "invited_emails": ["paciente@correo.com"],
    "scheduled_start": "2025-11-25T15:00:00Z",
    "scheduled_end": "2025-11-25T15:30:00Z"
  }'
```

### Opción 3: Postman

Importar colección: Meet_Middleware_API.postman_collection.json

### Opción 4: Python requests

```python
import requests

# Verificación de estado
response = requests.get('http://localhost:8000/api/v1/health/')
print(response.json())

# Creación de reunión
data = {
    "organizer_email": "doctor@clinica.com",
    "invited_emails": ["paciente@correo.com"],
    "scheduled_start": "2025-11-25T15:00:00Z",
    "scheduled_end": "2025-11-25T15:30:00Z"
}
response = requests.post('http://localhost:8000/api/v1/meetings/', json=data)
print(response.json())
```

---

## Configuración de Autenticación

**Estado Actual:** Todos los endpoints configurados con AllowAny (desarrollo)

**Recomendación para Producción:**

- Migración a IsAuthenticated
- Implementación de JWT (djangorestframework-simplejwt)
- Endpoints de autenticación adicionales:
  - /api/v1/auth/login/
  - /api/v1/auth/logout/
  - /api/v1/auth/refresh/

---

## Notas de Implementación Técnica

### Configuración de Router

Django REST Framework DefaultRouter configurado con:

- 5 ViewSets registrados
- 30+ endpoints automáticos
- Formato JSON por defecto
- Trailing slashes configurables

### Sistema de Documentación

drf-spectacular genera documentación automática desde:

- Docstrings de ViewSets
- Definiciones de Serializers
- Schemas de request y response
- Parámetros de consulta

### Servicio de Archivos Estáticos

**Desarrollo:** Django sirve archivos estáticos automáticamente en modo DEBUG  
**Producción:** WhiteNoise configurado para servicio eficiente de archivos estáticos

---

## Enlaces de Acceso Rápido

- **Swagger UI:** http://localhost:8000/api/v1/docs/
- **Panel de Administración:** http://localhost:8000/admin/
- **Health Check:** http://localhost:8000/api/v1/health/
- **API Root:** http://localhost:8000/api/v1/

---

## Referencias Técnicas

- [Django REST Framework Routers](https://www.django-rest-framework.org/api-guide/routers/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
