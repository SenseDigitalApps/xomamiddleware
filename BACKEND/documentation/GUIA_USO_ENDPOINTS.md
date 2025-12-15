# Guía de Uso de Endpoints - Meet Middleware API

## Resumen

Esta guía proporciona instrucciones paso a paso para utilizar los endpoints del middleware de Google Meet, incluyendo ejemplos prácticos para crear reuniones, gestionar usuarios y consultar información.

**URL Base del Sistema:** `http://localhost:8000/api/v1`

---

## Verificación Inicial del Sistema

### 1. Health Check

Verificar que el sistema esté funcionando:

```bash
curl http://localhost:8000/api/v1/health/
```

**Respuesta Esperada:**
```json
{
  "status": "ok",
  "api": "running",
  "database": "connected"
}
```

### 2. Acceso a Documentación Interactiva

Abrir en navegador:
```
http://localhost:8000/api/v1/docs/
```

Swagger UI permite probar todos los endpoints directamente desde el navegador.

---

## Endpoint Principal: Crear Reunión

### Descripción

Este es el endpoint más importante del sistema. Permite crear una reunión de Google Meet desde XOMA.

### Request

**Método:** `POST`  
**URL:** `http://localhost:8000/api/v1/meetings/`  
**Content-Type:** `application/json`

**Body:**
```json
{
  "organizer_email": "doctor@clinica.com",
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-12-01T15:00:00Z",
  "scheduled_end": "2025-12-01T16:00:00Z",
  "external_reference": "xoma_appointment_1234"
}
```

**Campos:**
- `organizer_email` (requerido): Email del organizador/doctor
- `invited_emails` (requerido): Array con al menos un email de invitado
- `scheduled_start` (opcional): Fecha/hora de inicio en formato ISO 8601
- `scheduled_end` (opcional): Fecha/hora de fin en formato ISO 8601
- `external_reference` (opcional): Referencia externa de XOMA (ID de cita)

### Ejemplo con cURL

```bash
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_email": "doctor@clinica.com",
    "invited_emails": ["paciente@correo.com"],
    "scheduled_start": "2025-12-01T15:00:00Z",
    "scheduled_end": "2025-12-01T16:00:00Z",
    "external_reference": "xoma_appointment_1234"
  }'
```

### Respuesta Exitosa (201 Created)

```json
{
  "id": 1,
  "google_event_id": "mock_event_abc123",
  "meet_link": "https://meet.google.com/abc-defg-hij",
  "organizer": 1,
  "organizer_username": "doctor",
  "organizer_email": "doctor@clinica.com",
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-12-01T15:00:00Z",
  "scheduled_end": "2025-12-01T16:00:00Z",
  "status": "CREATED",
  "status_display": "Created",
  "participants_count": 2,
  "has_recording": false,
  "created_at": "2025-11-26T18:30:00Z",
  "updated_at": "2025-11-26T18:30:00Z"
}
```

**Campo Crítico:** `meet_link` - URL para acceder a la videollamada

### Errores Comunes

**400 Bad Request - Lista de invitados vacía:**
```json
{
  "invited_emails": [
    "Debe proporcionar al menos un email invitado."
  ]
}
```

**400 Bad Request - Email inválido:**
```json
{
  "invited_emails": [
    "Enter a valid email address."
  ]
}
```

---

## Consultar Reuniones

### Listar Todas las Reuniones

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/meetings/`

```bash
curl http://localhost:8000/api/v1/meetings/
```

### Filtrar Reuniones por Estado

**URL:** `http://localhost:8000/api/v1/meetings/?status=CREATED`

Estados disponibles: `CREATED`, `SCHEDULED`, `FINISHED`, `CANCELLED`

```bash
curl "http://localhost:8000/api/v1/meetings/?status=FINISHED"
```

### Filtrar Reuniones por Organizador

**URL:** `http://localhost:8000/api/v1/meetings/?organizer=1`

```bash
curl "http://localhost:8000/api/v1/meetings/?organizer=1"
```

### Obtener Detalle de una Reunión

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/meetings/{id}/`

**Ejemplo:**
```bash
curl http://localhost:8000/api/v1/meetings/1/
```

**Respuesta:** Incluye información completa con participantes y grabación anidados.

---

## Actualizar Reunión

### Actualizar Estado de Reunión

**Método:** `PATCH`  
**URL:** `http://localhost:8000/api/v1/meetings/{id}/`

**Body:**
```json
{
  "status": "FINISHED"
}
```

**Ejemplo:**
```bash
curl -X PATCH http://localhost:8000/api/v1/meetings/1/ \
  -H "Content-Type: application/json" \
  -d '{"status": "FINISHED"}'
```

**Campos Actualizables:**
- `status`: CREATED, SCHEDULED, FINISHED, CANCELLED
- `scheduled_start`: Nueva fecha/hora de inicio
- `scheduled_end`: Nueva fecha/hora de fin

---

## Cancelar Reunión

**Método:** `DELETE`  
**URL:** `http://localhost:8000/api/v1/meetings/{id}/`

```bash
curl -X DELETE http://localhost:8000/api/v1/meetings/1/
```

**Efecto:** Cambia el estado de la reunión a `CANCELLED` y cancela el evento en Google Calendar (si está configurado).

---

## Consultar Participantes

### Listar Todos los Participantes

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/participants/`

```bash
curl http://localhost:8000/api/v1/participants/
```

### Filtrar Participantes por Reunión

**URL:** `http://localhost:8000/api/v1/participants/?meeting=1`

```bash
curl "http://localhost:8000/api/v1/participants/?meeting=1"
```

### Obtener Participantes de una Reunión Específica

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/meetings/{id}/participants/`

```bash
curl http://localhost:8000/api/v1/meetings/1/participants/
```

---

## Consultar Grabaciones

### Listar Todas las Grabaciones

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/recordings/`

```bash
curl http://localhost:8000/api/v1/recordings/
```

### Obtener Grabación de una Reunión

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/meetings/{id}/recording/`

```bash
curl http://localhost:8000/api/v1/meetings/1/recording/
```

**Respuesta si existe grabación:**
```json
{
  "id": 1,
  "meeting": 1,
  "drive_file_id": "1xyz789abc456",
  "drive_file_url": "https://drive.google.com/file/d/1xyz789abc456/view",
  "duration_seconds": 1800,
  "duration_formatted": "00:30:00",
  "available_at": "2025-12-01T16:30:00Z",
  "created_at": "2025-12-01T16:30:00Z"
}
```

**Respuesta si no existe grabación:**
```json
{
  "detail": "Esta reunión no tiene grabación disponible."
}
```

---

## Gestión de Usuarios

### Listar Usuarios

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/users/`

```bash
curl http://localhost:8000/api/v1/meetings/users/
```

### Filtrar Usuarios por Rol

**URL:** `http://localhost:8000/api/v1/users/?role=external`

Roles disponibles: `admin`, `service`, `external`

```bash
curl "http://localhost:8000/api/v1/users/?role=admin"
```

### Obtener Detalle de Usuario

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/users/{id}/`

```bash
curl http://localhost:8000/api/v1/users/1/
```

### Estadísticas de Usuarios

**Método:** `GET`  
**URL:** `http://localhost:8000/api/v1/users/stats/`

```bash
curl http://localhost:8000/api/v1/users/stats/
```

**Respuesta:**
```json
{
  "total_users": 10,
  "active_users": 8,
  "by_role": {
    "admin": 2,
    "service": 1,
    "external": 7
  }
}
```

---

## Crear y Gestionar Usuarios (User Management)

### Crear Usuario

**Método:** `POST`  
**URL:** `http://localhost:8000/api/v1/user-management/`

**Body:**
```json
{
  "username": "doctor_juan",
  "email": "juan@clinica.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "Juan",
  "last_name": "Pérez",
  "role": "external"
}
```

**Ejemplo:**
```bash
curl -X POST http://localhost:8000/api/v1/user-management/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "doctor_juan",
    "email": "juan@clinica.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "Juan",
    "last_name": "Pérez",
    "role": "external"
  }'
```

**Validaciones:**
- Password mínimo 8 caracteres
- Password y password_confirm deben coincidir
- Username y email deben ser únicos

### Actualizar Usuario

**Método:** `PATCH`  
**URL:** `http://localhost:8000/api/v1/user-management/{id}/`

**Body:**
```json
{
  "first_name": "Juan Carlos",
  "role": "admin"
}
```

```bash
curl -X PATCH http://localhost:8000/api/v1/user-management/2/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan Carlos",
    "role": "admin"
  }'
```

### Cambiar Contraseña de Usuario

**Método:** `POST`  
**URL:** `http://localhost:8000/api/v1/user-management/{id}/change-password/`

**Body:**
```json
{
  "old_password": "OldPass123",
  "new_password": "NewPass456!",
  "new_password_confirm": "NewPass456!"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/user-management/2/change-password/ \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "OldPass123",
    "new_password": "NewPass456!",
    "new_password_confirm": "NewPass456!"
  }'
```

### Desactivar Usuario

**Método:** `DELETE`  
**URL:** `http://localhost:8000/api/v1/user-management/{id}/`

```bash
curl -X DELETE http://localhost:8000/api/v1/user-management/2/
```

**Efecto:** Marca el usuario como inactivo (soft delete).

### Activar Usuario

**Método:** `POST`  
**URL:** `http://localhost:8000/api/v1/user-management/{id}/activate/`

```bash
curl -X POST http://localhost:8000/api/v1/user-management/2/activate/
```

---

## Flujo Completo de Ejemplo: Crear Reunión desde XOMA

### Paso 1: Verificar Sistema

```bash
curl http://localhost:8000/api/v1/health/
```

### Paso 2: Crear Reunión

```bash
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_email": "doctor@clinica.com",
    "invited_emails": ["paciente@correo.com"],
    "scheduled_start": "2025-12-05T10:00:00Z",
    "scheduled_end": "2025-12-05T11:00:00Z",
    "external_reference": "xoma_appointment_5678"
  }'
```

**Guardar el ID de la reunión de la respuesta** (ejemplo: `"id": 1`)

### Paso 3: Consultar Detalle de Reunión

```bash
curl http://localhost:8000/api/v1/meetings/1/
```

### Paso 4: Verificar Participantes

```bash
curl http://localhost:8000/api/v1/meetings/1/participants/
```

### Paso 5: Marcar Reunión como Finalizada (después de la videollamada)

```bash
curl -X PATCH http://localhost:8000/api/v1/meetings/1/ \
  -H "Content-Type: application/json" \
  -d '{"status": "FINISHED"}'
```

### Paso 6: Consultar Grabación (si está disponible)

```bash
curl http://localhost:8000/api/v1/meetings/1/recording/
```

---

## Uso con Postman

### Importar Colección

1. Abrir Postman
2. Click en "Import"
3. Seleccionar archivo: `Meet_Middleware_API.postman_collection.json`
4. La colección se importará con todas las carpetas y endpoints

### Configurar Variables

La colección incluye variables preconfiguradas:

- `base_url`: `http://localhost:8000/api/v1`
- `meeting_id`: `1` (se actualiza automáticamente al crear reunión)

### Probar Endpoints

1. **Utilidades → Health Check**: Verificar que el sistema funcione
2. **Meetings → Crear Reunión**: Crear una nueva reunión
3. **Meetings → Listar Reuniones**: Ver todas las reuniones
4. **Meetings → Obtener Detalle**: Ver detalles completos
5. **Ejemplos de Uso XOMA**: Flujos completos de integración

### Tests Automáticos

Algunos endpoints incluyen tests automáticos que:
- Verifican códigos de estado HTTP
- Validan estructura de respuesta
- Guardan IDs en variables para uso posterior

---

## Ejemplos de Uso con Python

### Crear Reunión

```python
import requests

url = "http://localhost:8000/api/v1/meetings/"
data = {
    "organizer_email": "doctor@clinica.com",
    "invited_emails": ["paciente@correo.com"],
    "scheduled_start": "2025-12-01T15:00:00Z",
    "scheduled_end": "2025-12-01T16:00:00Z",
    "external_reference": "xoma_appointment_1234"
}

response = requests.post(url, json=data)
meeting = response.json()

print(f"Reunión creada: ID {meeting['id']}")
print(f"Meet Link: {meeting['meet_link']}")
```

### Consultar Reunión

```python
import requests

meeting_id = 1
url = f"http://localhost:8000/api/v1/meetings/{meeting_id}/"

response = requests.get(url)
meeting = response.json()

print(f"Estado: {meeting['status']}")
print(f"Participantes: {meeting['participants_count']}")
if meeting.get('recording'):
    print(f"Grabación: {meeting['recording']['drive_file_url']}")
```

### Listar Reuniones con Filtros

```python
import requests

url = "http://localhost:8000/api/v1/meetings/"
params = {"status": "FINISHED", "organizer": 1}

response = requests.get(url, params=params)
meetings = response.json()

print(f"Reuniones finalizadas: {len(meetings)}")
```

---

## Ejemplos de Uso con JavaScript/Node.js

### Crear Reunión

```javascript
const fetch = require('node-fetch');

const url = 'http://localhost:8000/api/v1/meetings/';
const data = {
  organizer_email: 'doctor@clinica.com',
  invited_emails: ['paciente@correo.com'],
  scheduled_start: '2025-12-01T15:00:00Z',
  scheduled_end: '2025-12-01T16:00:00Z',
  external_reference: 'xoma_appointment_1234'
};

fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
})
  .then(res => res.json())
  .then(meeting => {
    console.log(`Reunión creada: ID ${meeting.id}`);
    console.log(`Meet Link: ${meeting.meet_link}`);
  });
```

---

## Códigos de Estado HTTP

| Código | Significado | Cuándo Ocurre |
|--------|-------------|---------------|
| 200 | OK | Operación exitosa (GET, PATCH) |
| 201 | Created | Recurso creado exitosamente (POST) |
| 204 | No Content | Recurso eliminado exitosamente (DELETE) |
| 400 | Bad Request | Datos inválidos o validación fallida |
| 404 | Not Found | Recurso no encontrado |
| 500 | Internal Server Error | Error del servidor |

---

## Notas Importantes

### Enlaces de Google Meet

**Estado Actual:** El sistema genera enlaces **mock** (simulados) cuando no están configuradas las credenciales de Google Workspace.

**Para obtener enlaces reales:**
1. Configurar Google Service Account (ver ENV_SETUP.md)
2. Proporcionar credenciales JSON
3. Reiniciar servicios

### Creación Automática de Usuarios

Cuando se crea una reunión, el sistema:
- Crea automáticamente el usuario organizador si no existe
- Crea automáticamente usuarios para participantes si no existen
- Asigna rol `external` por defecto

### Fechas y Horas

- Formato requerido: ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)
- Zona horaria: UTC (recomendado) o con offset
- Ejemplo: `2025-12-01T15:00:00Z`

### Validaciones

- Emails deben tener formato válido
- `invited_emails` debe tener al menos un elemento
- `scheduled_end` debe ser posterior a `scheduled_start` (si ambos existen)
- Passwords mínimo 8 caracteres

---

## Troubleshooting

### Error: Connection Refused

**Causa:** Servicios Docker no están corriendo

**Solución:**
```bash
cd BACKEND/
docker-compose up -d
```

### Error: 500 Internal Server Error

**Causa:** Error en el servidor

**Solución:**
```bash
# Ver logs
docker-compose logs web

# Reiniciar servicio
docker-compose restart web
```

### Error: 400 Bad Request

**Causa:** Datos inválidos en el request

**Solución:** Verificar formato JSON y campos requeridos

---

## Recursos Adicionales

- **Swagger UI:** http://localhost:8000/api/v1/docs/
- **ReDoc:** http://localhost:8000/api/v1/redoc/
- **Django Admin:** http://localhost:8000/admin/
- **Colección Postman:** `Meet_Middleware_API.postman_collection.json`

---

**Última Actualización:** Noviembre 2025

