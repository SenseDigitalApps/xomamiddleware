# Guía de Instalación en Entorno Local - Meet Middleware

## Resumen

Este documento proporciona instrucciones detalladas para la instalación y configuración del middleware en un entorno de desarrollo local.

---

## Requisitos del Sistema

### Requisitos Obligatorios

- Python 3.11 o superior
- pip (gestor de paquetes de Python)
- Git para control de versiones

### Requisitos Opcionales (Recomendados)

- PostgreSQL 15+ (alternativa: SQLite por defecto)
- Redis 7+ (requerido solo para funcionalidad de Celery)

---

## Procedimiento de Instalación

### PASO 1: Preparación del Entorno

```bash
# Navegación al directorio del proyecto
cd BACKEND/

# Creación de entorno virtual
python3 -m venv venv

# Activación del entorno virtual

# En macOS/Linux:
source venv/bin/activate

# En Windows:
venv\Scripts\activate

# Verificación de versión de Python
python --version  # Debe ser 3.11 o superior
```

---

### PASO 2: Configuración de Variables de Entorno

Crear archivo `.env` en el directorio BACKEND/:

```bash
# Creación del archivo
touch .env
```

**Contenido Mínimo Requerido:**

```bash
# Configuración de Django
SECRET_KEY=django-insecure-dev-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,*

# Configuración de Base de Datos
# Por defecto utiliza SQLite (db.sqlite3)
# Para PostgreSQL, descomentar y configurar:
# POSTGRES_DB=meet_middleware_db
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=postgres
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432

# Configuración CORS
CORS_ALLOW_ALL_ORIGINS=True

# Integración con Google Workspace
# Sistema utilizará enlaces mock sin estas configuraciones
# GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account-key.json
# GOOGLE_WORKSPACE_ADMIN_EMAIL=admin@yourdomain.com
# GOOGLE_CALENDAR_ID=primary

# Configuración de Celery y Redis (opcional)
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

**Nota:** Con esta configuración, el sistema utilizará SQLite y enlaces mock de Google Meet.

---

### PASO 3: Instalación de Dependencias

```bash
# Instalación de todos los paquetes requeridos
pip install -r requirements.txt
```

**Dependencias Principales Instaladas:**

- Django >= 4.2.0
- djangorestframework >= 3.14.0
- drf-spectacular >= 0.27.0
- google-api-python-client >= 2.120.0
- psycopg2-binary >= 2.9.0
- celery >= 5.3.0
- gunicorn >= 21.2.0
- whitenoise >= 6.6.0

**Resolución de Problemas Comunes:**

Si ocurren errores con psycopg2-binary:

```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install libpq-dev python3-dev

# Windows
# Descargar e instalar PostgreSQL desde postgresql.org
```

---

### PASO 4: Configuración de Base de Datos

#### Opción A: SQLite (Configuración por Defecto)

SQLite se configura automáticamente sin instalación adicional.

```bash
# Creación de migraciones
python manage.py makemigrations

# Aplicación de migraciones
python manage.py migrate
```

#### Opción B: PostgreSQL (Recomendado para Producción)

**1. Instalación de PostgreSQL:**

```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**2. Creación de Base de Datos:**

```bash
# Conexión a PostgreSQL
psql postgres

# Comandos en prompt de psql:
CREATE DATABASE meet_middleware_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE meet_middleware_db TO postgres;
\q
```

**3. Configuración en archivo .env:**

```bash
POSTGRES_DB=meet_middleware_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

**4. Aplicación de Migraciones:**

```bash
python manage.py makemigrations
python manage.py migrate
```

**Verificación:**

```bash
python manage.py showmigrations
# Debe mostrar [X] en todas las migraciones
```

---

### PASO 5: Creación de Superusuario

```bash
python manage.py createsuperuser
```

**Información Requerida:**

- Username: admin (o personalizado)
- Email: admin@example.com
- Password: (seleccionar contraseña segura)
- Password (confirmación)

**Nota:** Este usuario tendrá acceso completo al panel de administración en /admin/

---

### PASO 6: Inicialización del Servidor

```bash
# Inicio del servidor de desarrollo
python manage.py runserver

# Opción alternativa con puerto personalizado:
python manage.py runserver 8001
```

**Salida Esperada:**

```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
November 25, 2025 - 17:00:00
Django version 5.2.6, using settings 'app.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

---

### PASO 7: Verificación de Endpoints

#### 1. Health Check (Verificación Básica)

Acceder mediante navegador:

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

#### 2. Panel de Administración Django

```
http://localhost:8000/admin/
```

Debe presentar pantalla de login con acceso mediante credenciales de superusuario.

#### 3. API Root

```
http://localhost:8000/api/v1/
```

Debe retornar JSON con referencias a todos los endpoints disponibles.

#### 4. Swagger UI (Interfaz de Documentación)

```
http://localhost:8000/api/v1/docs/
```

Presenta interfaz interactiva para testing de todos los endpoints.

#### 5. Listado de Reuniones

```
http://localhost:8000/api/v1/meetings/
```

Debe retornar array vacío [] en instalación inicial.

---

### PASO 8: Testing de Funcionalidad

#### Método A: Desde Swagger UI (Recomendado)

1. Acceder a http://localhost:8000/api/v1/docs/
2. Localizar endpoint POST /api/v1/meetings/
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

5. Ejecutar request
6. Verificar respuesta 201 Created

#### Método B: Mediante cURL

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

**Nota Importante:** Sin configuración de Google Service Account, el campo meet_link contendrá un enlace simulado para propósitos de desarrollo.

---

## Verificación de Instalación

### Checklist de Componentes

**Instalación:**

- [ ] Python 3.11+ instalado y verificado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas sin errores
- [ ] Archivo .env creado y configurado

**Base de Datos:**

- [ ] Migraciones creadas
- [ ] Migraciones aplicadas a base de datos
- [ ] Sin errores de base de datos

**Usuario Administrativo:**

- [ ] Superusuario creado
- [ ] Acceso al panel /admin/ verificado

**Servidor:**

- [ ] Servidor inicia sin errores
- [ ] Accesible en http://localhost:8000

**Endpoints:**

- [ ] /admin/ - Panel de administración accesible
- [ ] /api/v1/ - API Root responde
- [ ] /api/v1/health/ - Health check OK
- [ ] /api/v1/docs/ - Swagger UI carga

**Funcionalidad:**

- [ ] Login en panel de administración funcional
- [ ] Modelos visibles en admin
- [ ] Swagger UI permite testing de endpoints
- [ ] Reunión se crea y persiste en base de datos

---

## Resolución de Problemas

### Error: Puerto 8000 en Uso

**Solución:**

```bash
# Opción 1: Utilizar puerto alternativo
python manage.py runserver 8001

# Opción 2: Liberar puerto
# macOS/Linux:
lsof -ti:8000 | xargs kill -9

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Error: Módulo no Encontrado

**Solución:**

```bash
# Verificar activación de entorno virtual
which python  # Debe apuntar al venv

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: Instalación de psycopg2 Falla

**Solución:**

```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install libpq-dev

# Reinstalar paquete
pip install psycopg2-binary
```

### Error: Tabla no Existe

**Solución:**

```bash
# Ejecutar migraciones
python manage.py migrate

# Si persiste, reinicializar base de datos (perderá datos):
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## Comandos Útiles del Sistema

```bash
# Ver estado de migraciones
python manage.py showmigrations

# Acceder a shell de Django
python manage.py shell

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Ver configuración actual
python manage.py diffsettings

# Verificar integridad del proyecto
python manage.py check
```

---

## Endpoints Disponibles

### Documentación

- http://localhost:8000/api/v1/docs/ - Swagger UI
- http://localhost:8000/api/v1/redoc/ - ReDoc
- http://localhost:8000/api/v1/schema/ - Especificación OpenAPI

### Administración

- http://localhost:8000/admin/ - Panel de administración Django

### API Versión 1

- http://localhost:8000/api/v1/ - API Root
- http://localhost:8000/api/v1/health/ - Health Check
- http://localhost:8000/api/v1/meetings/ - Gestión de reuniones
- http://localhost:8000/api/v1/users/ - Gestión de usuarios
- http://localhost:8000/api/v1/participants/ - Participantes
- http://localhost:8000/api/v1/recordings/ - Grabaciones

Consulte URLS_DOCUMENTATION.md para listado completo.

---

## Próximos Pasos

Una vez completada la instalación local:

### 1. Configuración de Google Service Account (Opcional)

Consulte ENV_SETUP.md sección 2 para procedimiento de configuración de credenciales de Google y obtención de enlaces funcionales de Google Meet.

### 2. Migración a PostgreSQL

Para entornos de producción o datos persistentes, se recomienda migrar de SQLite a PostgreSQL.

### 3. Containerización con Docker

Consulte DOCKER_DOCUMENTATION.md para procedimientos de dockerización del proyecto.

### 4. Implementación de Testing

Desarrolle suite de tests unitarios y de integración para asegurar calidad del código.

---

## Referencias Técnicas

- [Documentación de Django](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)

---

## Notas Finales

- Utilice Swagger UI como herramienta principal de testing de API
- El panel de administración Django permite gestión manual de datos
- Monitoree logs en la terminal donde ejecuta runserver
- Utilice python manage.py shell para pruebas rápidas de código

---

**Estado al Completar Esta Guía:** Sistema funcional en entorno local y preparado para desarrollo.

Para soporte adicional, consulte:
- ENV_SETUP.md - Configuración detallada de variables
- URLS_DOCUMENTATION.md - Referencia completa de endpoints
- XOMA_INTEGRATION_GUIDE.md - Manual de integración
