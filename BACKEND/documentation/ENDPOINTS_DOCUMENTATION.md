# Documentación de Endpoints - Meet Middleware API

## 📋 Resumen

Este documento describe todos los endpoints REST disponibles en el middleware de Google Meet para la integración con XOMA.

**Base URL:** `http://localhost:8000/api/v1/`

---

## 📅 Endpoints de Reuniones (Meetings)

### 1. Crear Reunión

**Endpoint:** `POST /api/v1/meetings/`

**ViewSet:** `MeetingViewSet.create()`

**Descripción:** Crea una nueva reunión de Google Meet

**Request Body:**
```json
{
  "organizer_email": "doctor@clinica.com",
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-11-25T15:00:00Z",
  "scheduled_end": "2025-11-25T15:30:00Z",
  "external_reference": "xoma_appointment_1234"
}
```

**Response:** `201 Created`
```json
{
  "id": 12,
  "google_event_id": "mock_event_abc123",
  "meet_link": "https://meet.google.com/abc-defg-hij",
  "organizer": 1,
  "organizer_username": "doctor",
  "organizer_email": "doctor@clinica.com",
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-11-25T15:00:00Z",
  "scheduled_end": "2025-11-25T15:30:00Z",
  "status": "CREATED",
  "status_display": "Created",
  "participants_count": 2,
  "has_recording": false,
  "created_at": "2025-11-25T14:30:00Z",
  "updated_at": "2025-11-25T14:30:00Z"
}
```

---

### 2. Listar Reuniones

**Endpoint:** `GET /api/v1/meetings/`

**ViewSet:** `MeetingViewSet.list()`

**Descripción:** Lista todas las reuniones con filtros opcionales

**Query Parameters:**
- `organizer` (int): Filtrar por ID de organizador
- `status` (string): Filtrar por estado (CREATED, SCHEDULED, FINISHED, CANCELLED)
- `scheduled_start__gte` (datetime): Filtrar por fecha mínima
- `scheduled_start__lte` (datetime): Filtrar por fecha máxima

**Ejemplos:**
```bash
# Listar todas
GET /api/v1/meetings/

# Filtrar por organizador
GET /api/v1/meetings/?organizer=1

# Filtrar por estado
GET /api/v1/meetings/?status=FINISHED

# Filtrar por fecha
GET /api/v1/meetings/?scheduled_start__gte=2025-11-25
```

**Response:** `200 OK`
```json
[
  {
    "id": 12,
    "google_event_id": "mock_event_abc123",
    "meet_link": "https://meet.google.com/abc-defg-hij",
    "organizer_name": "Dr. Juan Pérez",
    "scheduled_start": "2025-11-25T15:00:00Z",
    "status": "FINISHED",
    "status_display": "Finished",
    "created_at": "2025-11-25T14:30:00Z"
  }
]
```

---

### 3. Detalle de Reunión

**Endpoint:** `GET /api/v1/meetings/{id}/`

**ViewSet:** `MeetingViewSet.retrieve()`

**Descripción:** Obtiene detalle completo de una reunión con información anidada

**Response:** `200 OK`
```json
{
  "id": 12,
  "google_event_id": "mock_event_abc123",
  "meet_link": "https://meet.google.com/abc-defg-hij",
  "organizer": {
    "id": 1,
    "username": "doctor",
    "email": "doctor@clinica.com",
    "first_name": "Juan",
    "last_name": "Pérez",
    "full_name": "Juan Pérez",
    "role": "external",
    "role_display": "External User"
  },
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-11-25T15:00:00Z",
  "scheduled_end": "2025-11-25T15:30:00Z",
  "status": "FINISHED",
  "status_display": "Finished",
  "participants": [
    {
      "id": 1,
      "email": "doctor@clinica.com",
      "role": "organizer",
      "role_display": "Organizer"
    },
    {
      "id": 2,
      "email": "paciente@correo.com",
      "role": "guest",
      "role_display": "Guest"
    }
  ],
  "participants_count": 2,
  "recording": {
    "id": 1,
    "drive_file_url": "https://drive.google.com/file/d/xyz/view",
    "duration_formatted": "00:30:00"
  },
  "created_at": "2025-11-25T14:30:00Z",
  "updated_at": "2025-11-25T16:00:00Z"
}
```

---

### 4. Actualizar Reunión

**Endpoint:** `PATCH /api/v1/meetings/{id}/`

**ViewSet:** `MeetingViewSet.partial_update()`

**Descripción:** Actualiza parcialmente una reunión (solo ciertos campos)

**Campos actualizables:**
- `status`
- `scheduled_start`
- `scheduled_end`

**Request Body:**
```json
{
  "status": "FINISHED"
}
```

**Response:** `200 OK`

---

### 5. Cancelar Reunión

**Endpoint:** `DELETE /api/v1/meetings/{id}/`

**ViewSet:** `MeetingViewSet.destroy()`

**Descripción:** Cancela una reunión (cambia estado a CANCELLED, no elimina)

**Response:** `200 OK`
```json
{
  "message": "Reunión cancelada exitosamente",
  "meeting_id": 12,
  "status": "CANCELLED"
}
```

---

### 6. Obtener Grabación de Reunión

**Endpoint:** `GET /api/v1/meetings/{id}/recording/`

**ViewSet:** `MeetingViewSet.recording()` (custom action)

**Descripción:** Obtiene la grabación de una reunión si existe

**Response:** `200 OK`
```json
{
  "id": 1,
  "meeting": 12,
  "meeting_id": 12,
  "drive_file_id": "1xyz789abc456",
  "drive_file_url": "https://drive.google.com/file/d/1xyz789abc456/view",
  "duration_seconds": 1800,
  "duration_formatted": "00:30:00",
  "available_at": "2025-11-25T16:00:00Z",
  "created_at": "2025-11-25T16:00:00Z"
}
```

**Response:** `404 Not Found` (si no hay grabación)
```json
{
  "message": "Esta reunión no tiene grabación disponible",
  "meeting_id": 12
}
```

---

### 7. Obtener Participantes de Reunión

**Endpoint:** `GET /api/v1/meetings/{id}/participants/`

**ViewSet:** `MeetingViewSet.participants()` (custom action)

**Descripción:** Obtiene la lista de participantes de una reunión

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "meeting": 12,
    "email": "doctor@clinica.com",
    "role": "organizer",
    "role_display": "Organizer",
    "created_at": "2025-11-25T14:30:00Z"
  },
  {
    "id": 2,
    "meeting": 12,
    "email": "paciente@correo.com",
    "role": "guest",
    "role_display": "Guest",
    "created_at": "2025-11-25T14:30:00Z"
  }
]
```

---

## 👤 Endpoints de Usuarios (Users)

### 8. Listar Usuarios

**Endpoint:** `GET /api/v1/users/`

**ViewSet:** `UserViewSet.list()`

**Descripción:** Lista todos los usuarios activos

**Query Parameters:**
- `role` (string): Filtrar por rol (admin, service, external)
- `email` (string): Buscar por email (parcial)
- `username` (string): Buscar por username (parcial)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "username": "doctor",
    "email": "doctor@clinica.com",
    "first_name": "Juan",
    "last_name": "Pérez",
    "full_name": "Juan Pérez",
    "role": "external",
    "role_display": "External User",
    "is_active": true,
    "date_joined": "2025-11-20T10:00:00Z"
  }
]
```

---

### 9. Detalle de Usuario

**Endpoint:** `GET /api/v1/users/{id}/`

**ViewSet:** `UserViewSet.retrieve()`

**Descripción:** Obtiene detalle de un usuario específico

**Response:** `200 OK`

---

### 10. Usuario Actual

**Endpoint:** `GET /api/v1/users/me/`

**ViewSet:** `UserViewSet.me()` (custom action)

**Descripción:** Obtiene información del usuario autenticado actual

**Response:** `200 OK`

---

### 11. Estadísticas de Usuarios

**Endpoint:** `GET /api/v1/users/stats/`

**ViewSet:** `UserViewSet.stats()` (custom action)

**Descripción:** Obtiene estadísticas de usuarios del sistema

**Response:** `200 OK`
```json
{
  "total_users": 150,
  "active_users": 145,
  "inactive_users": 5,
  "by_role": {
    "admin": 5,
    "service": 10,
    "external": 135
  }
}
```

---

## 🎥 Endpoints de Grabaciones (Recordings)

### 12. Listar Grabaciones

**Endpoint:** `GET /api/v1/recordings/`

**ViewSet:** `MeetingRecordingViewSet.list()`

**Descripción:** Lista todas las grabaciones disponibles

**Query Parameters:**
- `meeting` (int): Filtrar por ID de reunión

**Response:** `200 OK`

---

### 13. Detalle de Grabación

**Endpoint:** `GET /api/v1/recordings/{id}/`

**ViewSet:** `MeetingRecordingViewSet.retrieve()`

**Descripción:** Obtiene detalle de una grabación específica

**Response:** `200 OK`

---

## 👥 Endpoints de Participantes (Participants)

### 14. Listar Participantes

**Endpoint:** `GET /api/v1/participants/`

**ViewSet:** `ParticipantViewSet.list()`

**Descripción:** Lista todos los participantes

**Query Parameters:**
- `meeting` (int): Filtrar por ID de reunión

**Response:** `200 OK`

---

### 15. Detalle de Participante

**Endpoint:** `GET /api/v1/participants/{id}/`

**ViewSet:** `ParticipantViewSet.retrieve()`

**Descripción:** Obtiene detalle de un participante específico

**Response:** `200 OK`

---

## 🔧 Endpoints Utilitarios

### 16. Health Check

**Endpoint:** `GET /api/v1/health/`

**Vista:** `health_check()`

**Descripción:** Verifica que el sistema está funcionando

**Response:** `200 OK`
```json
{
  "status": "ok",
  "api": "running",
  "database": "connected"
}
```

**Response:** `503 Service Unavailable` (si hay problemas)
```json
{
  "status": "degraded",
  "api": "running",
  "database": "disconnected",
  "database_error": "Connection refused"
}
```

---

### 17. Información del Sistema

**Endpoint:** `GET /api/v1/info/`

**Vista:** `system_info()`

**Descripción:** Obtiene información del sistema

**Response:** `200 OK`
```json
{
  "project": "Meet Middleware",
  "description": "API para integración de Google Meet con XOMA",
  "version": "1.0.0",
  "python_version": "3.11.0",
  "debug_mode": true,
  "environment": "development",
  "api_base_url": "/api/v1/",
  "docs_url": "/api/v1/docs/"
}
```

---

### 18. API Root

**Endpoint:** `GET /api/v1/`

**Vista:** `api_root()`

**Descripción:** Punto de entrada de la API con enlaces a recursos

**Response:** `200 OK`
```json
{
  "message": "Meet Middleware API - XOMA Integration",
  "version": "1.0.0",
  "endpoints": {
    "health": "/api/v1/health/",
    "info": "/api/v1/info/",
    "docs": "/api/v1/docs/",
    "meetings": "/api/v1/meetings/",
    "users": "/api/v1/users/",
    "recordings": "/api/v1/recordings/",
    "participants": "/api/v1/participants/"
  },
  "documentation": {
    "integration_guide": "Ver XOMA_INTEGRATION_GUIDE.md",
    "models": "Ver MODELS_DOCUMENTATION.md",
    "serializers": "Ver SERIALIZERS_DOCUMENTATION.md"
  }
}
```

---

## 📊 Resumen de Endpoints

| # | Endpoint | Método | ViewSet/Vista | Propósito |
|---|----------|--------|---------------|-----------|
| 1 | `/meetings/` | POST | MeetingViewSet | Crear reunión |
| 2 | `/meetings/` | GET | MeetingViewSet | Listar reuniones |
| 3 | `/meetings/{id}/` | GET | MeetingViewSet | Detalle de reunión |
| 4 | `/meetings/{id}/` | PATCH | MeetingViewSet | Actualizar reunión |
| 5 | `/meetings/{id}/` | DELETE | MeetingViewSet | Cancelar reunión |
| 6 | `/meetings/{id}/recording/` | GET | MeetingViewSet | Obtener grabación |
| 7 | `/meetings/{id}/participants/` | GET | MeetingViewSet | Obtener participantes |
| 8 | `/users/` | GET | UserViewSet | Listar usuarios |
| 9 | `/users/{id}/` | GET | UserViewSet | Detalle de usuario |
| 10 | `/users/me/` | GET | UserViewSet | Usuario actual |
| 11 | `/users/stats/` | GET | UserViewSet | Estadísticas |
| 12 | `/recordings/` | GET | MeetingRecordingViewSet | Listar grabaciones |
| 13 | `/recordings/{id}/` | GET | MeetingRecordingViewSet | Detalle grabación |
| 14 | `/participants/` | GET | ParticipantViewSet | Listar participantes |
| 15 | `/participants/{id}/` | GET | ParticipantViewSet | Detalle participante |
| 16 | `/health/` | GET | health_check | Health check |
| 17 | `/info/` | GET | system_info | Info del sistema |
| 18 | `/` | GET | api_root | Raíz de la API |

**Total: 18 endpoints funcionales**

---

## 🔐 Códigos de Estado HTTP

| Código | Significado | Cuándo se usa |
|--------|-------------|---------------|
| 200 | OK | Operación exitosa |
| 201 | Created | Recurso creado exitosamente |
| 400 | Bad Request | Validación fallida |
| 401 | Unauthorized | No autenticado |
| 404 | Not Found | Recurso no encontrado |
| 500 | Internal Server Error | Error del servidor |
| 503 | Service Unavailable | Servicio no disponible |

---

## 📝 Notas Importantes

### Estado Actual (PASO 6)

- ✅ Todos los ViewSets están implementados
- ✅ Los endpoints son funcionales
- ⚠️ La integración con Google Calendar usa datos MOCK
- ⚠️ El `meet_link` generado es simulado

### PASO 7 (Próximo)

En el PASO 7 se implementará la integración real con Google Calendar API:
- `meeting_service.create_meeting()` llamará a Google Calendar
- Se obtendrá un `meet_link` real de Google Meet
- Se sincronizarán eventos con Google Calendar

### Pruebas

Los endpoints pueden ser probados con:
- Postman
- Insomnia
- cURL
- Frontend de XOMA

**Ejemplo con cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_email": "doctor@clinica.com",
    "invited_emails": ["paciente@correo.com"],
    "scheduled_start": "2025-11-25T15:00:00Z",
    "scheduled_end": "2025-11-25T15:30:00Z"
  }'
```

---

## 🔗 Referencias

- **Guía de Integración XOMA**: `XOMA_INTEGRATION_GUIDE.md`
- **Documentación de Serializers**: `SERIALIZERS_DOCUMENTATION.md`
- **Documentación de Modelos**: `MODELS_DOCUMENTATION.md`

