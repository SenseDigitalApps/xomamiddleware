# Configuración de Variables de Entorno

Para ejecutar el proyecto localmente, necesitas crear un archivo `.env` en la raíz del proyecto BACKEND con las siguientes variables:

## Variables Requeridas

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
POSTGRES_DB=meet_middleware_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Google Workspace Integration
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account-key.json
GOOGLE_WORKSPACE_ADMIN_EMAIL=admin@yourdomain.com
GOOGLE_CALENDAR_ID=primary

# Celery & Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## Instrucciones de Configuración

### 1. Crear archivo .env
```bash
cd BACKEND
cp ENV_SETUP.md .env  # O crea el archivo manualmente
```

### 2. Configurar Google Service Account

#### 2.1 Crear Proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto nuevo:
   - Click en "Select a project" → "New Project"
   - Nombre: "Meet Middleware" (o el que prefieras)
   - Click "Create"

#### 2.2 Habilitar APIs Necesarias

1. En el proyecto, ve a "APIs & Services" → "Library"
2. Busca y habilita:
   - **Google Calendar API** ✅ (Requerida)
   - **Google Drive API** (Opcional, para grabaciones futuras)

#### 2.3 Crear Service Account

1. Ve a "IAM & Admin" → "Service Accounts"
2. Click "Create Service Account"
3. Configuración:
   - **Service account name**: `meet-middleware-sa`
   - **Service account ID**: Se genera automáticamente
   - **Description**: "Service Account para Meet Middleware"
   - Click "Create and Continue"

4. **Otorgar permisos** (Paso 2):
   - Role: "Project → Editor" (o permisos específicos de Calendar)
   - Click "Continue"

5. **Grant users access** (Paso 3):
   - Dejar en blanco por ahora
   - Click "Done"

#### 2.4 Generar Clave JSON

1. En la lista de Service Accounts, encuentra la que creaste
2. Click en los 3 puntos → "Manage keys"
3. Click "Add Key" → "Create new key"
4. Selecciona **JSON**
5. Click "Create"
6. Se descargará un archivo JSON automáticamente
   - **Nombre ejemplo**: `meet-middleware-sa-abc123.json`
   - **⚠️ IMPORTANTE**: Guarda este archivo en lugar seguro
   - **⚠️ NUNCA** lo subas a GitHub o repositorios públicos

#### 2.5 Configurar Domain-Wide Delegation (Opcional pero recomendado)

Si tu organización usa Google Workspace:

1. En la Service Account, click "Show Domain-Wide Delegation"
2. Click "Enable Domain-Wide Delegation"
3. Product name: "Meet Middleware"
4. Click "Save"
5. Copia el **Client ID** (lo necesitarás)

6. Ve a [Google Workspace Admin Console](https://admin.google.com/)
7. Ve a Security → API Controls → Domain-wide Delegation
8. Click "Add new"
9. Pega el Client ID
10. Agregar scopes:
   ```
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/calendar.events
   ```
11. Click "Authorize"

#### 2.6 Configurar en el Proyecto

1. Mueve el archivo JSON descargado a un lugar seguro:
   ```bash
   # Ejemplo en macOS/Linux
   mkdir -p ~/.config/meet-middleware/
   mv ~/Downloads/meet-middleware-sa-*.json ~/.config/meet-middleware/service-account-key.json
   chmod 600 ~/.config/meet-middleware/service-account-key.json
   ```

2. Actualiza tu archivo `.env`:
   ```bash
   GOOGLE_SERVICE_ACCOUNT_FILE=/Users/tuusuario/.config/meet-middleware/service-account-key.json
   GOOGLE_WORKSPACE_ADMIN_EMAIL=admin@tudominio.com
   GOOGLE_CALENDAR_ID=primary
   ```

#### 2.7 Verificar Configuración

Para verificar que todo está configurado correctamente:

```python
# En Django shell (python manage.py shell)
from integrations.config import validate_google_credentials
validate_google_credentials()  # Debe retornar True sin errores
```

### 3. Configurar PostgreSQL

**Opción A: Docker (recomendado)**
```bash
docker run --name postgres-meet \
  -e POSTGRES_DB=meet_middleware_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:15
```

**Opción B: Instalación local**
- Instala PostgreSQL 15
- Crea la base de datos: `createdb meet_middleware_db`
- Actualiza las credenciales en `.env`

### 4. Configurar Redis

**Opción A: Docker (recomendado)**
```bash
docker run --name redis-meet \
  -p 6379:6379 \
  -d redis:7
```

**Opción B: Instalación local**
- macOS: `brew install redis && brew services start redis`
- Linux: `sudo apt install redis-server && sudo systemctl start redis`

## Notas de Seguridad

⚠️ **IMPORTANTE:**
- Nunca subas el archivo `.env` al repositorio
- El archivo `.env` está incluido en `.gitignore`
- Genera un SECRET_KEY único para producción
- Cambia `DEBUG=False` en producción
- Restringe ALLOWED_HOSTS en producción

