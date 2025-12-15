# Guía de Verificación de Instalación Local

## Resumen

Este documento describe el procedimiento de verificación para instalación local del middleware, incluyendo comandos necesarios y resultados esperados.

---

## Opción 1: Procedimiento Automatizado

```bash
cd BACKEND/

# Ejecución de script de configuración
./scripts/setup_and_run.sh

# Creación de superusuario
python3 manage.py createsuperuser

# Inicialización del servidor
python3 manage.py runserver
```

---

## Opción 2: Procedimiento Manual Detallado

### 1. Navegación al Directorio del Proyecto

```bash
cd /Users/camilo/Documents/Sense/XOMA\ MIDDLEWARE/BACKEND
```

### 2. Configuración de Variables de Entorno (Opcional)

Crear archivo `.env` con contenido mínimo:

```bash
SECRET_KEY=django-insecure-dev-key-for-testing-only
DEBUG=True
ALLOWED_HOSTS=*
```

**Nota:** Si no se crea el archivo, Django utilizará valores por defecto definidos en settings.py

### 3. Instalación de Dependencias

```bash
pip3 install -r requirements.txt
```

**Tiempo Estimado:** 2-3 minutos

**Resolución de Problemas:**

```bash
# macOS - Si hay errores con psycopg2
brew install postgresql

# Ubuntu/Debian - Si hay errores con psycopg2
sudo apt-get install libpq-dev
```

### 4. Creación de Migraciones

```bash
python3 manage.py makemigrations
```

**Salida Esperada:**

```
Migrations for 'accounts':
  accounts/migrations/0001_initial.py
    - Create model User
Migrations for 'meetings':
  meetings/migrations/0001_initial.py
    - Create model Meeting
    - Create model MeetingRecording
    - Create model Participant
```

### 5. Aplicación de Migraciones

```bash
python3 manage.py migrate
```

**Salida Esperada:**

```
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying accounts.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying meetings.0001_initial... OK
```

### 6. Creación de Superusuario

```bash
python3 manage.py createsuperuser
```

**Información Requerida:**

- Username: admin (o preferencia del usuario)
- Email: admin@example.com
- Password: (seleccionar contraseña segura)
- Password (confirmación)

### 7. Inicialización del Servidor

```bash
python3 manage.py runserver
```

**Salida Esperada:**

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

---

## Verificación de Endpoints

### 1. Health Check

```
http://localhost:8000/api/v1/health/
```

**Respuesta Esperada:**

```json
{
  "status": "ok",
  "api": "running",
  "database": "connected"
}
```

### 2. Interfaz Swagger UI

```
http://localhost:8000/api/v1/docs/
```

Debe presentar interfaz completa de documentación con listado de endpoints.

### 3. Panel de Administración Django

```
http://localhost:8000/admin/
```

Debe presentar formulario de login para acceso con credenciales de superusuario.

### 4. API Root

```
http://localhost:8000/api/v1/
```

Debe retornar JSON con referencias a recursos disponibles.

### 5. Listado de Reuniones

```
http://localhost:8000/api/v1/meetings/
```

Debe retornar array vacío [] en instalación inicial.

---

## Testing de Funcionalidad

### Método 1: Desde Swagger UI

1. Acceder a http://localhost:8000/api/v1/docs/
2. Localizar POST /api/v1/meetings/
3. Activar "Try it out"
4. Ingresar datos de prueba:

```json
{
  "organizer_email": "doctor@test.com",
  "invited_emails": ["paciente@test.com"],
  "scheduled_start": "2025-12-01T15:00:00Z",
  "scheduled_end": "2025-12-01T16:00:00Z"
}
```

5. Ejecutar
6. Verificar respuesta 201 Created

### Método 2: Mediante cURL

```bash
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_email": "doctor@test.com",
    "invited_emails": ["paciente@test.com"],
    "scheduled_start": "2025-12-01T15:00:00Z",
    "scheduled_end": "2025-12-01T16:00:00Z"
  }'
```

**Respuesta Esperada:**

```json
{
  "id": 1,
  "google_event_id": "mock_event_abc123",
  "meet_link": "https://meet.google.com/abc-def-ghi",
  "status": "CREATED",
  "participants_count": 2
}
```

**Nota:** El meet_link será un enlace simulado sin configuración de Google Service Account.

---

## Checklist de Verificación

**Instalación:**

- [ ] Dependencias instaladas correctamente
- [ ] Migraciones creadas
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] Servidor en ejecución

**Endpoints:**

- [ ] /api/v1/health/ responde correctamente
- [ ] /api/v1/docs/ carga Swagger UI
- [ ] /admin/ permite acceso
- [ ] POST a /api/v1/meetings/ crea reunión
- [ ] Reunión visible en panel de administración

---

## Estado del Sistema

### Funcionalidad sin Google Service Account

- Todos los endpoints operativos
- Validación de datos funcional
- Persistencia en base de datos
- Panel de administración Django
- Interfaz Swagger UI
- meet_link: Enlaces simulados (no funcionales)

### Funcionalidad con Google Service Account

Todo lo anterior más:

- meet_link: Enlaces reales y funcionales
- Invitaciones automáticas por email
- Sincronización con Google Calendar
- Integración completa con Google Meet

Para configuración: Consulte ENV_SETUP.md sección 2

---

## Resolución de Problemas Adicionales

### Puerto Ocupado

```bash
python3 manage.py runserver 8001
```

### Módulo no Encontrado

```bash
pip3 install -r requirements.txt
```

### Error de Base de Datos

```bash
# Reinicialización (perderá datos)
rm db.sqlite3
python3 manage.py migrate
```

### Imposibilidad de Crear Superusuario

```bash
# Verificar migraciones
python3 manage.py showmigrations

# Aplicar si necesario
python3 manage.py migrate
```

---

## Resultado Final

Al completar exitosamente esta guía:

- Sistema accesible en http://localhost:8000/api/v1/docs/
- Capacidad de creación de reuniones mediante API
- Visualización de reuniones en panel de administración
- Capacidad de listado mediante GET /api/v1/meetings/
- Capacidad de consulta de detalles de reunión

---

## Próximo Paso

**Paso 10:** Containerización del proyecto mediante Docker

Consulte spect/01_setup.md para especificaciones del Paso 10.
