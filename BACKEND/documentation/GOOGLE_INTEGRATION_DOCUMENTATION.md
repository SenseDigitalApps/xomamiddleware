# Documentación de Integración con Google APIs

## 📋 Resumen

Este documento describe la integración del middleware con Google Workspace APIs, específicamente Google Calendar API para la creación de eventos con Google Meet.

---

## 🏗️ Arquitectura de Integración

```
MeetingService (meetings/services.py)
    ↓
GoogleMeetService (integrations/services.py)
    ↓
GoogleCalendarClient (integrations/google_client.py)
    ↓
Google Calendar API (REST)
    ↓
Google Meet (hangoutLink)
```

---

## 📦 Componentes Implementados

### 1. **core/exceptions.py**
Excepciones personalizadas para manejar errores de Google API:
- `GoogleAPIError` - Excepción base
- `GoogleAuthenticationError` - Errores de autenticación
- `GoogleCalendarError` - Errores de Calendar API
- `GoogleMeetCreationError` - Errores al crear Meet
- `GoogleAPIQuotaExceeded` - Cuota excedida

### 2. **integrations/config.py**
Configuración centralizada:
- `GoogleConfig` - Clase de configuración
- `validate_google_credentials()` - Validación de credenciales
- Definición de scopes necesarios

**Scopes utilizados:**
```python
GOOGLE_CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]
```

### 3. **integrations/google_client.py**
Cliente de bajo nivel para Google Calendar API:

**Clase: `GoogleCalendarClient`**

| Método | Descripción | Returns |
|--------|-------------|---------|
| `__init__()` | Inicializa credenciales y servicio | - |
| `create_event(event_data)` | Crea evento con Google Meet | dict (event_id, meet_link, html_link) |
| `get_event(event_id)` | Obtiene detalles de evento | dict |
| `update_event(event_id, updates)` | Actualiza evento | dict |
| `delete_event(event_id)` | Elimina evento | bool |
| `cancel_event(event_id)` | Cancela evento (status='cancelled') | dict |

**Función auxiliar:**
- `format_datetime_for_google(dt, timezone)` - Formatea datetime para Google API

### 4. **integrations/services.py**
Servicio de alto nivel para reuniones de Google Meet:

**Clase: `GoogleMeetService`**

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `create_meeting_event()` | Crea reunión con Meet | organizer_email, invited_emails, fechas, título |
| `update_meeting_event()` | Actualiza reunión | event_id, updates |
| `cancel_meeting_event()` | Cancela reunión | event_id |
| `delete_meeting_event()` | Elimina reunión | event_id |
| `get_meeting_event()` | Obtiene detalles | event_id |

### 5. **meetings/services.py** (Actualizado)
Integración con Google en `MeetingService`:

**Método actualizado:**
- `_create_google_meet_event()` - Ahora usa GoogleMeetService en lugar de mock

---

## 🔐 Autenticación

### Service Account

El middleware usa **Service Account** de Google Cloud para autenticación:

**Ventajas:**
- No requiere interacción del usuario
- Adecuado para aplicaciones servidor-a-servidor
- Puede actuar en nombre de usuarios (Domain-Wide Delegation)

**Archivo de credenciales:**
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "service-account@project.iam.gserviceaccount.com",
  "client_id": "123456789",
  ...
}
```

### Flujo de Autenticación

1. Cargar credenciales desde archivo JSON
2. Crear objeto `Credentials` con scopes
3. Aplicar Domain-Wide Delegation (si está configurado)
4. Construir servicio de Calendar API
5. Realizar requests autenticados

**Código:**
```python
credentials = service_account.Credentials.from_service_account_file(
    settings.GOOGLE_SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

if settings.GOOGLE_WORKSPACE_ADMIN_EMAIL:
    credentials = credentials.with_subject(admin_email)

service = build('calendar', 'v3', credentials=credentials)
```

---

## 🎯 Crear Reunión con Google Meet

### Flujo Completo

```
1. XOMA envía POST /api/v1/meetings/
   ↓
2. MeetingViewSet.create()
   ↓
3. MeetingCreateSerializer valida datos
   ↓
4. MeetingService.create_meeting()
   ↓
5. _create_google_meet_event()
   ↓
6. GoogleMeetService.create_meeting_event()
   ↓
7. GoogleCalendarClient.create_event()
   ├─ Autenticación con Service Account
   ├─ Construir evento con conferenceData
   ├─ Calendar API: events().insert()
   │  - calendarId='primary'
   │  - conferenceDataVersion=1
   │  - sendUpdates='all'
   └─ Obtener hangoutLink ← meet_link REAL
   ↓
8. Guardar Meeting en PostgreSQL
   ↓
9. Crear Participants
   ↓
10. Response 201 con meet_link REAL
```

### Estructura del Evento para Google

```python
event_data = {
    'summary': 'Reunión - 25/11/2025 15:00',
    'description': 'Reunión organizada por doctor@clinica.com\n\nParticipantes:\n- paciente@correo.com',
    'start': {
        'dateTime': '2025-11-25T15:00:00',
        'timeZone': 'America/Bogota'
    },
    'end': {
        'dateTime': '2025-11-25T16:00:00',
        'timeZone': 'America/Bogota'
    },
    'attendees': [
        {'email': 'paciente@correo.com'}
    ],
    'conferenceData': {
        'createRequest': {
            'requestId': 'meet-uuid',
            'conferenceSolutionKey': {'type': 'hangoutsMeet'}
        }
    },
    'reminders': {
        'useDefault': False,
        'overrides': [
            {'method': 'email', 'minutes': 1440},  # 1 día antes
            {'method': 'popup', 'minutes': 30}     # 30 min antes
        ]
    },
    'guestsCanModify': False,
    'guestsCanInviteOthers': False,
    'guestsCanSeeOtherGuests': True
}
```

### Response de Google Calendar API

```json
{
  "id": "abc123xyz456",
  "htmlLink": "https://www.google.com/calendar/event?eid=...",
  "hangoutLink": "https://meet.google.com/abc-defg-hij",
  "status": "confirmed",
  "created": "2025-11-25T14:30:00.000Z",
  "updated": "2025-11-25T14:30:00.000Z",
  "summary": "Reunión - 25/11/2025 15:00",
  "description": "...",
  "start": {...},
  "end": {...},
  "attendees": [...]
}
```

**Campo clave:** `hangoutLink` - Esta es la URL de Google Meet

---

## ⚠️ Manejo de Errores

### Tipos de Errores

| Error HTTP | Excepción | Causa | Solución |
|------------|-----------|-------|----------|
| 401 | GoogleAuthenticationError | Credenciales inválidas | Verificar Service Account |
| 403 | GoogleAPIQuotaExceeded | Cuota excedida o permisos | Verificar cuotas y scopes |
| 404 | GoogleCalendarError | Evento no encontrado | Verificar event_id |
| 500 | GoogleCalendarError | Error del servidor | Reintentar más tarde |

### Ejemplo de Manejo

```python
try:
    result = google_service.create_meeting_event(...)
except GoogleAuthenticationError as e:
    logger.error(f"Error de autenticación: {e}")
    return Response({'error': 'Credenciales de Google inválidas'}, status=500)
except GoogleAPIQuotaExceeded as e:
    logger.error(f"Cuota excedida: {e}")
    return Response({'error': 'Servicio temporalmente no disponible'}, status=503)
except GoogleMeetCreationError as e:
    logger.error(f"Error al crear reunión: {e}")
    return Response({'error': str(e)}, status=500)
```

---

## 📊 Cuotas y Límites de Google Calendar API

### Cuotas Por Defecto

| Recurso | Límite | Por |
|---------|--------|-----|
| Queries | 1,000,000 | Por día |
| Queries por usuario | 10 | Por segundo |
| Inserts | 10,000 | Por día |

**Para XOMA:** Estas cuotas son más que suficientes para uso normal.

### Monitoreo de Cuotas

Ver uso en [Google Cloud Console](https://console.cloud.google.com/):
1. APIs & Services → Dashboard
2. Ver métricas de Calendar API

---

## 🧪 Testing de Integración

### Prueba Manual (Django Shell)

```python
# python manage.py shell

from integrations.services import GoogleMeetService
from datetime import datetime, timedelta

service = GoogleMeetService()

# Crear reunión de prueba
result = service.create_meeting_event(
    organizer_email='test@example.com',
    invited_emails=['invitado@example.com'],
    scheduled_start=datetime.now() + timedelta(hours=1),
    scheduled_end=datetime.now() + timedelta(hours=2),
    title='Reunión de Prueba'
)

print(f"Event ID: {result['event_id']}")
print(f"Meet Link: {result['meet_link']}")
```

### Verificar en Google Calendar

1. Ve a [Google Calendar](https://calendar.google.com/)
2. Busca el evento creado
3. Verifica que tenga el botón "Join with Google Meet"
4. Click en el botón para probar el link

---

## 🔒 Consideraciones de Seguridad

### Protección de Credenciales

✅ **Hacer:**
- Guardar Service Account JSON fuera del repositorio
- Usar variables de entorno
- Establecer permisos restrictivos (chmod 600)
- Rotar credenciales periódicamente
- Usar diferentes Service Accounts para dev/prod

❌ **NO Hacer:**
- Subir credenciales a GitHub
- Compartir credenciales por email/chat
- Hardcodear rutas absolutas en código
- Usar mismas credenciales en múltiples proyectos

### Permisos Mínimos

El Service Account solo debe tener:
- Scopes de Calendar (no más)
- Role de Editor del proyecto (o permisos específicos de Calendar)

---

## 📈 Logging y Debugging

### Logs Implementados

```python
logger.info("Google Calendar Client inicializado correctamente")
logger.info(f"Creando evento en Google Calendar: {summary}")
logger.info(f"Evento creado exitosamente: {event_id}")
logger.info(f"Google Meet link: {meet_link}")
logger.error(f"Error al crear evento: {error}")
```

### Ver Logs

```bash
# En producción
tail -f /var/log/meet-middleware.log

# En desarrollo (Django runserver)
# Los logs aparecen en consola
```

---

## 🔄 Próximas Mejoras

### Funcionalidades Futuras

1. **Sincronización de Grabaciones**
   - Detectar grabaciones automáticamente en Drive
   - Vincular con MeetingRecording model
   - Webhook de Drive API

2. **Gestión Avanzada de Eventos**
   - Actualizar horarios desde XOMA
   - Reprogramar reuniones
   - Agregar/remover participantes

3. **Notificaciones Personalizadas**
   - Templates de email customizados
   - Recordatorios personalizados
   - SMS/WhatsApp notifications

4. **Métricas y Analytics**
   - Tiempo de duración real
   - Asistencia efectiva
   - Reportes de uso

---

## 🔗 Referencias

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/v3/reference)
- [Google Meet API](https://developers.google.com/meet)
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)

---

## 📝 Notas de Implementación

### PASO 7 Completado

✅ Cliente de Google Calendar API funcional  
✅ Creación de eventos con Google Meet  
✅ Autenticación con Service Account  
✅ Manejo robusto de errores  
✅ Logging para debugging  
✅ Documentación completa  

### Pendiente (futuros pasos)

⏳ Configurar URLs y routers (PASO 8)  
⏳ Testing end-to-end  
⏳ Dockerización  

