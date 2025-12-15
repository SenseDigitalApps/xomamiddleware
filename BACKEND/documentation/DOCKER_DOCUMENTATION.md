# Documentación de Docker - Meet Middleware

## 📋 Resumen

Este documento describe la configuración de Docker para el middleware, incluyendo el Dockerfile, entrypoint script y mejores prácticas.

---

## 🐳 Arquitectura Docker

```
Dockerfile (Multi-stage build)
├── Stage 1: base          → Python 3.11-slim base
├── Stage 2: dependencies  → Dependencias del sistema
├── Stage 3: application   → Dependencias Python + código
└── Stage 4: production    → Usuario no-root + configuración final
```

---

## 📦 Componentes del Dockerfile

### 1. Imagen Base
```dockerfile
FROM python:3.11-slim
```

**Características:**
- Python 3.11 (versión estable)
- Debian Bookworm (slim)
- Tamaño: ~150 MB (vs ~900 MB full)

### 2. Variables de Entorno
```dockerfile
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
```

**Beneficios:**
- `PYTHONUNBUFFERED=1` - Logs inmediatos (no buffered)
- `PYTHONDONTWRITEBYTECODE=1` - No crear .pyc (reduce tamaño)
- `PIP_NO_CACHE_DIR=1` - No cachear paquetes pip

### 3. Dependencias del Sistema
```dockerfile
RUN apt-get update && apt-get install -y \
    libpq-dev \          # Para psycopg2
    postgresql-client \  # Cliente de PostgreSQL
    gcc \                # Compilador
    curl \               # Para health checks
    netcat-traditional   # Para wait scripts
```

### 4. Dependencias Python
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
```

**Optimización:** Cache de Docker
- Si `requirements.txt` no cambia, Docker reutiliza esta capa
- Instalación más rápida en rebuilds

### 5. Usuario No-Root
```dockerfile
RUN useradd -r -u 1000 django
USER django
```

**Seguridad:**
- No ejecutar como root
- UID 1000 (compatible con la mayoría de hosts)

### 6. Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/api/v1/health/ || exit 1
```

**Configuración:**
- Intervalo: 30 segundos
- Timeout: 10 segundos
- Start period: 40 segundos (tiempo para que Django inicie)
- Retries: 3 intentos

---

## 🚀 Script docker-entrypoint.sh

### Funciones

El entrypoint ejecuta automáticamente:

1. **Esperar a PostgreSQL**
   - Verifica que PostgreSQL esté disponible
   - Usa `netcat` para verificar puerto
   - Máximo 30 intentos (30 segundos)

2. **Esperar a Redis** (opcional)
   - Solo si `CELERY_BROKER_URL` está configurado
   - Máximo 15 intentos

3. **Ejecutar Migraciones**
   ```bash
   python manage.py migrate --noinput
   ```

4. **Recolectar Archivos Estáticos**
   ```bash
   python manage.py collectstatic --noinput --clear
   ```

5. **Crear Superusuario** (opcional)
   - Solo si están configuradas las variables:
     - `DJANGO_SUPERUSER_USERNAME`
     - `DJANGO_SUPERUSER_PASSWORD`
     - `DJANGO_SUPERUSER_EMAIL`

6. **Verificar Configuración**
   ```bash
   python manage.py check --deploy
   ```

7. **Ejecutar Comando**
   - Por defecto: Gunicorn en puerto 8000
   - Puede sobreescribirse con otro comando

---

## 📝 Archivo .dockerignore

Excluye de la imagen Docker:

- ✅ Python cache (`__pycache__/`, `*.pyc`)
- ✅ Virtual environments (`venv/`, `env/`)
- ✅ Base de datos local (`db.sqlite3`)
- ✅ Variables de entorno (`.env`)
- ✅ IDE files (`.vscode/`, `.idea/`)
- ✅ Git (`.git/`)
- ✅ Logs (`*.log`)
- ✅ Tests (`htmlcov/`, `.pytest_cache/`)
- ✅ Credenciales de Google (`*.json`)
- ✅ Documentación (excepto `README.md`)

**Beneficio:** Imagen más pequeña y segura

---

## 🏗️ Construir Imagen

### Construcción Básica

```bash
cd BACKEND/

# Construir imagen
docker build -t meet-middleware:latest .

# Ver tamaño de imagen
docker images meet-middleware
```

**Tiempo estimado:** 3-5 minutos (primera vez)  
**Tamaño esperado:** ~350-400 MB

### Construcción con Tag

```bash
# Con versión
docker build -t meet-middleware:1.0.0 .

# Con múltiples tags
docker build -t meet-middleware:1.0.0 -t meet-middleware:latest .
```

### Construcción sin Cache

```bash
# Forzar rebuild completo
docker build --no-cache -t meet-middleware:latest .
```

---

## 🚀 Ejecutar Container

### Ejecución Básica (SQLite)

```bash
docker run -p 8000:8000 \
  -e DEBUG=True \
  meet-middleware:latest
```

**Acceder a:** `http://localhost:8000/api/v1/health/`

### Ejecución con PostgreSQL Externo

```bash
docker run -p 8000:8000 \
  -e DEBUG=True \
  -e POSTGRES_DB=meet_middleware_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PORT=5432 \
  meet-middleware:latest
```

### Ejecución con Variables de Entorno desde Archivo

```bash
# Crear archivo .env.docker
docker run -p 8000:8000 \
  --env-file .env.docker \
  meet-middleware:latest
```

### Ejecución con Volúmenes

```bash
docker run -p 8000:8000 \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/staticfiles:/app/staticfiles \
  -v $(pwd)/logs:/app/logs \
  meet-middleware:latest
```

### Ejecución en Background

```bash
docker run -d \
  --name meet-middleware \
  -p 8000:8000 \
  -e DEBUG=True \
  meet-middleware:latest

# Ver logs
docker logs -f meet-middleware

# Detener
docker stop meet-middleware

# Eliminar
docker rm meet-middleware
```

---

## 🔧 Comandos Útiles

### Verificar Logs del Container

```bash
# Ver logs en tiempo real
docker logs -f meet-middleware

# Ver últimas 100 líneas
docker logs --tail 100 meet-middleware
```

### Ejecutar Comandos dentro del Container

```bash
# Shell interactivo
docker exec -it meet-middleware bash

# Django shell
docker exec -it meet-middleware python manage.py shell

# Crear migraciones
docker exec -it meet-middleware python manage.py makemigrations

# Crear superusuario
docker exec -it meet-middleware python manage.py createsuperuser
```

### Inspeccionar Container

```bash
# Ver detalles del container
docker inspect meet-middleware

# Ver procesos corriendo
docker top meet-middleware

# Ver uso de recursos
docker stats meet-middleware
```

### Limpiar Recursos

```bash
# Detener todos los containers
docker stop $(docker ps -aq)

# Eliminar containers detenidos
docker container prune

# Eliminar imágenes sin usar
docker image prune

# Eliminar todo (⚠️ cuidado)
docker system prune -a
```

---

## 🧪 Testing del Dockerfile

### Test 1: Verificar que la imagen se construye

```bash
docker build -t meet-middleware:test .
```

**Esperado:** "Successfully built" y "Successfully tagged"

### Test 2: Verificar que el container inicia

```bash
docker run --rm -p 8000:8000 meet-middleware:test
```

**Esperado:** Mensaje "✅ MEET MIDDLEWARE LISTO"

### Test 3: Verificar health check

```bash
# Iniciar container
docker run -d --name test-middleware -p 8000:8000 meet-middleware:test

# Esperar unos segundos
sleep 45

# Verificar health status
docker inspect --format='{{.State.Health.Status}}' test-middleware

# Limpiar
docker stop test-middleware
docker rm test-middleware
```

**Esperado:** Status "healthy"

### Test 4: Verificar endpoints

```bash
# Con container corriendo
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/api/v1/
curl http://localhost:8000/api/v1/meetings/
```

---

## 📊 Optimizaciones del Dockerfile

### Multi-stage Build

El Dockerfile usa multi-stage build para:
- ✅ Separar construcción de runtime
- ✅ Reducir tamaño final de imagen
- ✅ Mejor organización

### Layer Caching

Orden optimizado de COPY:
1. `requirements.txt` primero (cambia poco)
2. Código de la aplicación después (cambia frecuentemente)

**Beneficio:** Builds más rápidos

### Cleanup en Misma Capa

```dockerfile
RUN apt-get update && apt-get install -y ... \
    && rm -rf /var/lib/apt/lists/*
```

**Beneficio:** Imagen más pequeña (no guarda cache de apt)

---

## 🔒 Seguridad

### Prácticas Implementadas

1. ✅ **Usuario no-root**
   - Container corre como usuario `django` (UID 1000)
   - No tiene permisos de root

2. ✅ **No incluir secretos**
   - `.dockerignore` excluye `.env` y `*.json`
   - Secretos se pasan por variables de entorno

3. ✅ **Imagen base oficial**
   - `python:3.11-slim` es imagen oficial de Docker Hub
   - Actualizada regularmente

4. ✅ **Dependencias mínimas**
   - Solo paquetes necesarios
   - Limpieza de cache

5. ✅ **Health checks**
   - Docker puede detectar containers unhealthy
   - Restart automático si falla

---

## 📈 Tamaño de Imagen

### Estimación de Capas

| Capa | Tamaño Aprox. |
|------|---------------|
| Python 3.11-slim | ~150 MB |
| Dependencias sistema | ~50 MB |
| Dependencias Python | ~200 MB |
| Código aplicación | ~10 MB |
| **TOTAL** | **~410 MB** |

### Comparación

| Enfoque | Tamaño |
|---------|--------|
| `python:3.11` (full) | ~900 MB |
| `python:3.11-slim` (usado) | ~400 MB |
| `python:3.11-alpine` | ~100 MB* |

*Alpine es más pequeño pero puede tener problemas de compatibilidad

---

## 🔄 Próximo Paso

Una vez que el Dockerfile esté creado:

**PASO 11:** Crear `docker-compose.yml`
- Servicio `db` (PostgreSQL)
- Servicio `redis` (Redis)
- Servicio `web` (Django - usa este Dockerfile)
- Servicio `celery` (worker)
- Networking entre servicios
- Volumes para persistencia

---

## 📝 Notas

### Comando por Defecto

El Dockerfile usa **Gunicorn** (servidor WSGI para producción):
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app.wsgi:application"]
```

Para desarrollo, puedes sobrescribir:
```bash
docker run -p 8000:8000 meet-middleware \
  python manage.py runserver 0.0.0.0:8000
```

### Variables de Entorno Requeridas

**Mínimas:**
- `SECRET_KEY` - Clave secreta de Django
- `DEBUG` - Modo debug (True/False)

**Recomendadas:**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`
- `ALLOWED_HOSTS`

**Opcionales:**
- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `CELERY_BROKER_URL`

---

## 🔗 Referencias

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Python Docker Images](https://hub.docker.com/_/python)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)

