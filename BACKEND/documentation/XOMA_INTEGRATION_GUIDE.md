# Manual de Integración - XOMA y Meet Middleware

## Resumen

Este documento describe el procedimiento de integración entre la plataforma XOMA y el middleware de Google Meet, utilizando Django REST Framework para la creación, gestión y consulta de reuniones de videollamada.

---

## Flujo de Comunicación

```
XOMA (Frontend/Backend)
    ↓ HTTP Request (JSON)
Django REST Framework
    ↓ Validación de datos
MeetingCreateSerializer
    ↓ Datos validados
Servicio de Google Meet
    ↓ Creación de evento
Google Calendar API
    ↓ Respuesta con enlace
Meeting Model (PostgreSQL)
    ↓ Serialización de respuesta
MeetingSerializer
    ↓ HTTP Response (JSON)
XOMA (Frontend/Backend)
```

---

## Configuración de API

### URL Base del Servicio

```
http://localhost:8000/api/v1/
```

### Sistema de Autenticación

**Entorno Actual:** AllowAny (desarrollo)  
**Entorno de Producción:** Se recomienda implementar Token/JWT Authentication

---

## Caso de Uso 1: Creación de Reunión desde XOMA

### Descripción del Escenario

Un profesional médico en la plataforma XOMA programa una cita con un paciente y requiere la creación de una videollamada de Google Meet.

### Endpoint Requerido

```http
POST /api/v1/meetings/
```

### Serializer Utilizado

**MeetingCreateSerializer** - Validación y recepción de datos de entrada

### Implementación del Request desde XOMA

**JavaScript/TypeScript (Frontend):**

```javascript
const response = await fetch('http://localhost:8000/api/v1/meetings/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    organizer_email: "doctor@clinica.com",
    invited_emails: ["paciente@correo.com"],
    scheduled_start: "2025-11-25T15:00:00Z",
    scheduled_end: "2025-11-25T15:30:00Z",
    external_reference: "xoma_appointment_1234"
  })
});

const data = await response.json();
```

**Python (Backend):**

```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/meetings/',
    json={
        "organizer_email": "doctor@clinica.com",
        "invited_emails": ["paciente@correo.com"],
        "scheduled_start": "2025-11-25T15:00:00Z",
        "scheduled_end": "2025-11-25T15:30:00Z",
        "external_reference": "xoma_appointment_1234"
    }
)

data = response.json()
```

### Especificación de Campos del Request

| Campo | Tipo de Dato | Requerido | Descripción | Ejemplo |
|-------|--------------|-----------|-------------|---------|
| organizer_email | string (email) | Sí | Correo electrónico del organizador | "doctor@clinica.com" |
| invited_emails | array[string] | Sí | Lista de correos de invitados (mínimo 1) | ["paciente@correo.com"] |
| scheduled_start | string (ISO 8601) | No | Fecha y hora de inicio | "2025-11-25T15:00:00Z" |
| scheduled_end | string (ISO 8601) | No | Fecha y hora de fin | "2025-11-25T15:30:00Z" |
| external_reference | string | No | Identificador de cita en XOMA | "xoma_appointment_1234" |

### Validaciones Automáticas del Sistema

El MeetingCreateSerializer ejecuta las siguientes validaciones:

1. Validación de formato de correos electrónicos
2. Validación de lista no vacía para invited_emails
3. Validación de unicidad de correos electrónicos en la lista
4. Validación de coherencia temporal (scheduled_end > scheduled_start)

### Estructura de Response del Middleware

**HTTP Status: 201 Created**

```json
{
  "id": 12,
  "google_event_id": "abc123xyz456",
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

### Especificación de Campos de Response

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | integer | Identificador único de la reunión en el middleware |
| google_event_id | string | Identificador del evento en Google Calendar |
| meet_link | string | **CRÍTICO** - URL para acceder a la videollamada |
| organizer | integer | ID del usuario organizador |
| organizer_username | string | Nombre de usuario del organizador |
| organizer_email | string | Correo del organizador |
| invited_emails | array | Lista de correos invitados |
| scheduled_start | string | Fecha y hora de inicio programada |
| scheduled_end | string | Fecha y hora de fin programada |
| status | string | Estado (CREATED, SCHEDULED, FINISHED, CANCELLED) |
| status_display | string | Descripción legible del estado |
| participants_count | integer | Cantidad de participantes |
| has_recording | boolean | Indica disponibilidad de grabación |
| created_at | string | Timestamp de creación |
| updated_at | string | Timestamp de última actualización |

### Campo Crítico para XOMA

**meet_link** - Este campo contiene la URL que debe ser:

1. Almacenada en la base de datos de XOMA asociada a la cita
2. Presentada al doctor y paciente en la interfaz
3. Enviada a los participantes vía email o notificaciones

**Ejemplo de implementación:**

```javascript
const meetLink = data.meet_link;
// Valor: "https://meet.google.com/abc-defg-hij"

// Persistir en base de datos XOMA
await saveMeetingLink(appointmentId, meetLink);

// Distribuir a participantes
await sendEmailToParticipants(meetLink);
```

---

## Caso de Uso 2: Consulta de Reunión Existente

### Descripción del Escenario

XOMA requiere obtener información completa de una reunión previamente creada, incluyendo datos de participantes y disponibilidad de grabación.

### Endpoint Requerido

```http
GET /api/v1/meetings/{id}/
```

### Serializer Utilizado

**MeetingDetailSerializer** - Proporciona datos completos con información anidada

### Implementación del Request

```javascript
const meetingId = 12;
const response = await fetch(`http://localhost:8000/api/v1/meetings/${meetingId}/`);
const data = await response.json();
```

### Estructura de Response

**HTTP Status: 200 OK**

```json
{
  "id": 12,
  "google_event_id": "abc123xyz456",
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
  "recording": {
    "id": 1,
    "drive_file_url": "https://drive.google.com/file/d/1xyz789/view",
    "duration_formatted": "00:30:00"
  }
}
```

### Verificación de Disponibilidad de Grabación

```javascript
if (data.recording) {
  const recordingUrl = data.recording.drive_file_url;
  const duration = data.recording.duration_formatted;
  
  displayRecordingLink(recordingUrl, duration);
}
```

---

## Caso de Uso 3: Listado de Reuniones

### Descripción del Escenario

XOMA requiere presentar un listado de reuniones, por ejemplo, historial de citas de un profesional médico.

### Endpoint Requerido

```http
GET /api/v1/meetings/
```

### Parámetros de Consulta Disponibles

```javascript
// Filtrado por organizador
GET /api/v1/meetings/?organizer=1

// Filtrado por estado
GET /api/v1/meetings/?status=FINISHED

// Filtrado por rango de fechas
GET /api/v1/meetings/?scheduled_start__gte=2025-11-25
```

---

## Manejo de Errores

### Error de Validación (400 Bad Request)

**Escenario: Email inválido**

```json
{
  "invited_emails": [
    "Enter a valid email address."
  ]
}
```

**Escenario: Lista de invitados vacía**

```json
{
  "invited_emails": [
    "Debe proporcionar al menos un email invitado."
  ]
}
```

**Escenario: Fechas incoherentes**

```json
{
  "scheduled_end": [
    "La fecha de fin debe ser posterior a la fecha de inicio."
  ]
}
```

### Implementación de Manejo de Errores en XOMA

```javascript
try {
  const response = await fetch('http://localhost:8000/api/v1/meetings/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData)
  });

  if (!response.ok) {
    const errorData = await response.json();
    
    if (response.status === 400) {
      Object.keys(errorData).forEach(field => {
        displayFieldError(field, errorData[field][0]);
      });
      return;
    }
    
    throw new Error('Error en la creación de la reunión');
  }

  const data = await response.json();
  processMeetingData(data.meet_link);
  
} catch (error) {
  console.error('Error:', error);
  displayErrorMessage('No se pudo crear la reunión. Intente nuevamente.');
}
```

---

## Flujo Completo de Integración

### Escenario: Programación de Cita con Videollamada

#### Paso 1: Creación de Cita en XOMA

```javascript
const appointment = {
  doctor_id: 1,
  patient_id: 5,
  date: "2025-11-25",
  time: "15:00",
  duration: 30,
  reason: "Consulta general"
};

const savedAppointment = await createAppointment(appointment);
```

#### Paso 2: Solicitud de Reunión al Middleware

```javascript
const meetingData = {
  organizer_email: savedAppointment.doctor.email,
  invited_emails: [savedAppointment.patient.email],
  scheduled_start: "2025-11-25T15:00:00Z",
  scheduled_end: "2025-11-25T15:30:00Z",
  external_reference: `appointment_${savedAppointment.id}`
};

const response = await fetch('http://localhost:8000/api/v1/meetings/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(meetingData)
});

const meeting = await response.json();
```

#### Paso 3: Almacenamiento del Enlace en XOMA

```javascript
await updateAppointment(savedAppointment.id, {
  meet_link: meeting.meet_link,
  middleware_meeting_id: meeting.id,
  google_event_id: meeting.google_event_id
});
```

#### Paso 4: Notificación a Participantes

```javascript
await sendEmail({
  to: savedAppointment.doctor.email,
  subject: "Videollamada programada",
  body: `Videollamada programada para ${date}. Enlace: ${meeting.meet_link}`
});

await sendEmail({
  to: savedAppointment.patient.email,
  subject: "Videollamada programada",
  body: `Videollamada programada para ${date}. Enlace: ${meeting.meet_link}`
});
```

#### Paso 5: Presentación en Interfaz de Usuario

```javascript
<div class="appointment-details">
  <h3>Cita Programada</h3>
  <p>Fecha: {formattedDate}</p>
  <p>Profesional: {doctorName}</p>
  <p>Paciente: {patientName}</p>
  
  <a href={meeting.meet_link} target="_blank" className="btn-video-call">
    Unirse a la Videollamada
  </a>
</div>
```

#### Paso 6: Verificación Post-Reunión de Grabación

```javascript
const response = await fetch(
  `http://localhost:8000/api/v1/meetings/${meeting.id}/`
);
const meetingDetails = await response.json();

if (meetingDetails.recording) {
  displayRecording({
    url: meetingDetails.recording.drive_file_url,
    duration: meetingDetails.recording.duration_formatted,
    available_at: meetingDetails.recording.available_at
  });
}
```

---

## Especificación de Endpoints para XOMA

| Operación en XOMA | Endpoint | Método HTTP | Serializer de Entrada | Serializer de Salida |
|-------------------|----------|-------------|----------------------|---------------------|
| Crear reunión | /api/v1/meetings/ | POST | MeetingCreateSerializer | MeetingSerializer |
| Consultar reunión | /api/v1/meetings/{id}/ | GET | - | MeetingDetailSerializer |
| Listar reuniones | /api/v1/meetings/ | GET | - | MeetingSerializer |
| Actualizar estado | /api/v1/meetings/{id}/ | PATCH | - | MeetingSerializer |

---

## Consideraciones Importantes para Desarrolladores

### 1. Campo Crítico: meet_link

El campo `meet_link` contiene la URL de acceso a la videollamada y debe ser:
- Almacenado en la base de datos de XOMA
- Distribuido a todos los participantes
- Presentado en la interfaz de usuario

### 2. Sistema de Validación

El middleware ejecuta validación automática de todos los datos recibidos. En caso de error, retorna mensajes específicos por campo.

### 3. Estados de Reunión

- `CREATED` - Reunión creada
- `SCHEDULED` - Reunión programada
- `FINISHED` - Reunión finalizada
- `CANCELLED` - Reunión cancelada

### 4. Grabaciones

Las grabaciones no están disponibles inmediatamente. Se deben consultar posteriormente mediante el endpoint de detalle de reunión.

### 5. External Reference

Utilice el campo `external_reference` para vincular la reunión del middleware con el identificador de cita en XOMA, facilitando el tracking y las búsquedas.

---

## Recursos de Documentación

- **Documentación de Serializers**: SERIALIZERS_DOCUMENTATION.md
- **Documentación de Modelos**: MODELS_DOCUMENTATION.md
- **Configuración de Variables**: ENV_SETUP.md
- **Colección de Postman**: Meet_Middleware_API.postman_collection.json

---

## Soporte Técnico

Para consultas o problemas de integración, contactar al equipo de desarrollo del middleware.
