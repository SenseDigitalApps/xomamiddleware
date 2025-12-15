# Documentación de Serializers - Meet Middleware

## Resumen

Este documento describe los serializers de Django REST Framework implementados en el middleware, incluyendo validaciones, campos y casos de uso.

---

## Aplicación: meetings

### 1. MeetingCreateSerializer

**Tipo:** serializers.Serializer (independiente de modelo)

**Propósito:** Recepción y validación de datos desde XOMA para creación de reuniones

**Uso:** POST /api/v1/meetings/

**Campos de Entrada:**

| Campo | Tipo de Dato | Requerido | Descripción |
|-------|--------------|-----------|-------------|
| organizer_email | EmailField | Sí | Correo electrónico del organizador |
| invited_emails | List[EmailField] | Sí | Lista de correos de invitados (mínimo: 1) |
| scheduled_start | DateTimeField | No | Fecha y hora de inicio |
| scheduled_end | DateTimeField | No | Fecha y hora de fin |
| external_reference | CharField | No | Referencia externa de XOMA |

**Validaciones Implementadas:**

- Validación de formato de correo electrónico
- Validación de lista no vacía para invited_emails
- Validación de unicidad de correos en la lista
- Validación de coherencia temporal (scheduled_end > scheduled_start)

**Ejemplo de Request:**

```json
{
  "organizer_email": "doctor@clinica.com",
  "invited_emails": ["paciente@correo.com"],
  "scheduled_start": "2025-11-25T15:00:00Z",
  "scheduled_end": "2025-11-25T15:30:00Z",
  "external_reference": "xoma_appointment_1234"
}
```

---

### 2. MeetingSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Serialización de reuniones para respuestas estándar

**Uso:** GET /api/v1/meetings/, respuestas de creación

**Campos de Salida:**

| Campo | Tipo de Dato | Descripción |
|-------|--------------|-------------|
| id | Integer | Identificador único |
| google_event_id | String | ID del evento en Google Calendar |
| meet_link | URL | Enlace de Google Meet |
| organizer | Integer | ID del organizador |
| organizer_username | String | Nombre de usuario del organizador (computado) |
| organizer_email | Email | Correo del organizador (computado) |
| invited_emails | List | Lista de correos invitados |
| scheduled_start | DateTime | Inicio programado |
| scheduled_end | DateTime | Fin programado |
| status | String | Estado de la reunión |
| status_display | String | Estado legible (computado) |
| participants_count | Integer | Cantidad de participantes (computado) |
| has_recording | Boolean | Indicador de grabación disponible (computado) |
| created_at | DateTime | Timestamp de creación |
| updated_at | DateTime | Timestamp de actualización |

---

### 3. MeetingDetailSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Serialización completa con datos anidados

**Uso:** GET /api/v1/meetings/{id}/

**Características:**

- Incluye objeto completo del organizador (UserSerializer)
- Incluye lista de participantes (ParticipantSerializer)
- Incluye datos de grabación si existe (MeetingRecordingSerializer)

---

### 4. MeetingListSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Serialización optimizada para listados

**Uso:** GET /api/v1/meetings/

**Campos de Salida:**

| Campo | Tipo de Dato | Descripción |
|-------|--------------|-------------|
| id | Integer | Identificador único |
| google_event_id | String | ID del evento |
| meet_link | URL | Enlace de Meet |
| organizer_name | String | Nombre del organizador (computado) |
| scheduled_start | DateTime | Inicio programado |
| status | String | Estado |
| status_display | String | Estado legible |
| created_at | DateTime | Timestamp de creación |

---

### 5. ParticipantSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Serialización de participantes de reuniones

**Uso:** Nested en MeetingDetailSerializer o GET /api/v1/participants/

**Campos:**

| Campo | Tipo de Dato | Descripción |
|-------|--------------|-------------|
| id | Integer | Identificador único |
| meeting | Integer | ID de la reunión |
| email | Email | Correo del participante |
| role | String | Rol (organizer, guest) |
| role_display | String | Descripción del rol |
| created_at | DateTime | Timestamp de registro |

---

### 6. MeetingRecordingSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Serialización de metadatos de grabaciones

**Uso:** Nested en MeetingDetailSerializer o GET /api/v1/recordings/

**Campos:**

| Campo | Tipo de Dato | Descripción |
|-------|--------------|-------------|
| id | Integer | Identificador único |
| meeting | Integer | ID de la reunión |
| meeting_id | Integer | ID de la reunión (solo lectura) |
| drive_file_id | String | ID del archivo en Google Drive |
| drive_file_url | URL | URL de acceso al archivo |
| duration_seconds | Integer | Duración en segundos |
| duration_formatted | String | Duración en formato HH:MM:SS (computado) |
| available_at | DateTime | Timestamp de disponibilidad |
| created_at | DateTime | Timestamp de registro |

---

## Aplicación: accounts

### 1. UserSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Serialización de información básica de usuarios (sin datos sensibles)

**Uso:** Lectura de información de usuarios, nested en otros serializers

**Campos:**

| Campo | Tipo de Dato | Descripción |
|-------|--------------|-------------|
| id | Integer | Identificador único |
| username | String | Nombre de usuario |
| email | Email | Correo electrónico |
| first_name | String | Nombre |
| last_name | String | Apellido |
| full_name | String | Nombre completo (computado) |
| role | String | Rol del usuario |
| role_display | String | Descripción del rol |
| is_active | Boolean | Estado de activación |
| date_joined | DateTime | Fecha de registro |

---

### 2. UserCreateSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Creación de usuarios con manejo seguro de contraseñas

**Uso:** POST /api/v1/users/

**Campos de Entrada:**

| Campo | Tipo de Dato | Requerido | Descripción |
|-------|--------------|-----------|-------------|
| username | String | Sí | Nombre de usuario (único) |
| email | Email | Sí | Correo electrónico (único) |
| password | String | Sí | Contraseña (write-only, mínimo 8 caracteres) |
| password_confirm | String | Sí | Confirmación de contraseña (write-only) |
| first_name | String | No | Nombre del usuario |
| last_name | String | No | Apellido del usuario |
| role | String | Sí | Rol del usuario (default: external) |

**Validaciones Implementadas:**

- Validación de contraseña mediante validadores de Django
- Verificación de coincidencia entre password y password_confirm
- Hashing automático de contraseña mediante set_password()

---

### 3. UserUpdateSerializer

**Tipo:** serializers.ModelSerializer

**Propósito:** Actualización de información de usuarios (sin contraseña)

**Uso:** PATCH /api/v1/users/{id}/

**Campos Actualizables:**

- email
- first_name
- last_name
- role
- is_active

---

### 4. ChangePasswordSerializer

**Tipo:** serializers.Serializer

**Propósito:** Cambio de contraseña para usuario autenticado

**Uso:** POST /api/v1/users/{id}/change-password/

**Campos de Entrada:**

| Campo | Tipo de Dato | Requerido | Descripción |
|-------|--------------|-----------|-------------|
| old_password | String | Sí | Contraseña actual (write-only) |
| new_password | String | Sí | Nueva contraseña (write-only) |
| new_password_confirm | String | Sí | Confirmación de nueva contraseña (write-only) |

**Validaciones Implementadas:**

- Validación de nueva contraseña mediante validadores de Django
- Verificación de coincidencia entre new_password y new_password_confirm

---

## Estadísticas de Serializers

### Distribución por Aplicación

| Aplicación | Cantidad de Serializers | Líneas de Código |
|------------|-------------------------|------------------|
| meetings | 6 | 280 líneas |
| accounts | 4 | 160 líneas |
| **TOTAL** | **10** | **440 líneas** |

### Clasificación por Tipo

| Tipo de Serializer | Cantidad | Uso Principal |
|-------------------|----------|---------------|
| ModelSerializer | 8 | Basados en modelos de BD |
| Serializer | 2 | Validación personalizada |

---

## Flujo de Procesamiento (Crear Reunión)

```
1. XOMA envía datos → MeetingCreateSerializer (validación)
2. Servicio crea reunión en Google Meet
3. Registro de Meeting en base de datos
4. Serialización de respuesta → MeetingSerializer
```

**Secuencia de Procesamiento:**

```
POST /api/v1/meetings/
├── MeetingCreateSerializer.validate()
├── meeting_service.create_meeting()
├── Integración con Google Calendar API
├── Meeting.objects.create()
└── MeetingSerializer(meeting).data
```

---

## Notas de Implementación

### Buenas Prácticas Aplicadas

- Todos los serializers incluyen validaciones apropiadas según contexto
- Campos sensibles utilizan atributo write_only=True
- Campos computados utilizan SerializerMethodField o ReadOnlyField
- Implementación de nested serializers para respuestas completas
- Separación clara entre serializers de entrada y salida
- Validación exhaustiva de datos de entrada
- Mensajes de error descriptivos y específicos

### Seguridad

- Contraseñas siempre en modo write_only
- Hash automático de contraseñas mediante set_password()
- Validadores de Django para políticas de contraseñas
- Campos de solo lectura para datos automáticos
- Sin exposición de datos sensibles en responses
