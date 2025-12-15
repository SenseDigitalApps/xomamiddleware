# Documentación de Docker Compose - Meet Middleware

## 📋 Resumen

Este documento describe la configuración de Docker Compose para orquestar todos los servicios del middleware de Google Meet.

---

## 🏗️ Arquitectura de Servicios

```
┌─────────────────────────────────────────────┐
│              meet-network                    │
│                                              │
│  ┌──────────┐    ┌──────────┐              │
│  │    db    │    │  redis   │              │
│  │ Postgres │    │  Redis   │              │
│  │   :5432  │    │  :6379   │              │
│  └────┬─────┘    └────┬─────┘              │
│       │               │                      │
│       └───────┬───────┘                      │
│               │                              │
│         ┌─────▼─────┐                       │
│         │    web    │                       │
│         │  Django   │                       │
│         │   :8000   │◄──────────┐          │
│         └─────┬─────┘           │          │
│               │                 │          │
│         ┌─────▼─────┐    ┌─────┴──────┐   │
│         │  celery   │    │ celery-beat│   │
│         │  Worker   │    │  Scheduler │   │
│         └───────────┘    └────────────┘   │
│               ▲                            │
│         ┌─────┴─────┐                      │
│         │   nginx   │ (opcional)          │
│         │   :80     │                      │
│         └───────────┘                      │
└─────────────────────────────────────────────┘
```

---

## 📦 Servicios Configurados

### 1. **db** - PostgreSQL 15

**Imagen:** `postgres:15-alpine`

**Configuración:**
- **Puerto:** 5432 (expuesto)
- **Base de datos:** `meet_middleware_db`
- **Usuario:** `postgres`
- **Password:** `postgres`
- **Volume:** `postgres_data` para persistencia
- **Health check:** `pg_isready` cada 10 segundos

**Variables de entorno:**
```yaml
POSTGRES_DB: meet_middleware_db
POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
```

**Acceso externo:**
```bash
# Conectar desde host
psql -h localhost -U postgres -d meet_middleware_db

# Desde otro container
psql -h db -U postgres -d meet_middleware_db
```

---

### 2. **redis** - Redis 7

**Imagen:** `redis:7-alpine`

**Configuración:**
- **Puerto:** 6379 (expuesto)
- **Persistencia:** AOF (Append Only File)
- **Volume:** `redis_data`
- **Health check:** `redis-cli ping` cada 10 segundos

**Comando:**
```bash
redis-server --appendonly yes
```

**Uso:**
- Broker de Celery
- Backend de resultados de Celery
- Caché de Django (futuro)

**Acceso externo:**
```bash
# Desde host
redis-cli -h localhost

# Desde otro container
redis-cli -h redis
```

---

### 3. **web** - Django Application

**Imagen:** Construida desde `Dockerfile`

**Configuración:**
- **Puerto:** 8000 (expuesto)
- **Comando:** Gunicorn con 4 workers
- **Depende de:** db (healthy), redis (healthy)
- **Volumes:**
  - `./media` - Archivos de usuario
  - `./staticfiles` - Archivos estáticos
  - `./logs` - Logs de la aplicación
  - Service account JSON (si está configurado)

**Variables de entorno:**
- Django: SECRET_KEY, DEBUG, ALLOWED_HOSTS
- Database: POSTGRES_*
- Celery: CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- Google: GOOGLE_SERVICE_ACCOUNT_FILE, etc.

**Health check:**
```bash
curl --fail http://localhost:8000/api/v1/health/
```

**Restart policy:** `unless-stopped`

---

### 4. **celery** - Celery Worker

**Imagen:** Construida desde `Dockerfile` (misma que web)

**Configuración:**
- **Comando:** `celery -A app worker -l info --concurrency=4`
- **Depende de:** db, redis, web
- **Volume:** `./logs` - Logs de Celery

**Variables de entorno:**
- Database: POSTGRES_*
- Celery: CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- Google: GOOGLE_SERVICE_ACCOUNT_FILE, etc.

**Workers:** 4 procesos concurrentes

---

### 5. **celery-beat** - Celery Scheduler

**Imagen:** Construida desde `Dockerfile` (misma que web)

**Configuración:**
- **Comando:** `celery -A app beat -l info`
- **Depende de:** db, redis, web
- **Volume:** `./logs` - Logs de Beat

**Scheduler:** DatabaseScheduler (tareas en BD)

**Uso futuro:**
- Sincronizar grabaciones de Drive
- Verificar estados de reuniones
- Limpiar reuniones antiguas
- Notificaciones programadas

---

### 6. **nginx** - Reverse Proxy (Producción)

**Imagen:** `nginx:alpine`

**Configuración:**
- **Puertos:** 80 (HTTP), 443 (HTTPS)
- **Depende de:** web
- **Volumes:**
  - `nginx.conf` - Configuración
  - `staticfiles` - Archivos estáticos (read-only)
  - `media` - Archivos de media (read-only)
  - `logs/nginx` - Logs de nginx

**Funciones:**
- Proxy reverso a Django
- Servir archivos estáticos eficientemente
- SSL/TLS termination
- Load balancing (futuro)

---

## 🔧 Volumes

### Volumes Named (Persistencia)

```yaml
volumes:
  postgres_data:  # Datos de PostgreSQL
  redis_data:     # Datos de Redis
```

**Características:**
- Persisten entre reinicios de containers
- Gestionados por Docker
- Ubicación: `/var/lib/docker/volumes/`

**Comandos útiles:**
```bash
# Listar volumes
docker volume ls

# Inspeccionar volume
docker volume inspect backend_postgres_data

# Backup de volume
docker run --rm -v backend_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data

# Restaurar volume
docker run --rm -v backend_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

### Bind Mounts (Acceso desde host)

```yaml
volumes:
  - ./media:/app/media           # Archivos de usuario
  - ./staticfiles:/app/staticfiles  # Archivos estáticos
  - ./logs:/app/logs             # Logs
```

**Características:**
- Directamente accesibles desde host
- Útil para desarrollo
- Útil para revisar logs

---

## 🌐 Networks

```yaml
networks:
  meet-network:
    driver: bridge
```

**Características:**
- Todos los servicios en la misma red
- Comunicación por nombre de servicio (DNS interno)
- Aislado de otras redes Docker

**Ejemplos:**
```python
# Desde web container, conectar a:
- PostgreSQL: host="db", port=5432
- Redis: host="redis", port=6379
```

---

## 🚀 Uso de Docker Compose

### Comandos Básicos

```bash
# Iniciar todos los servicios
docker-compose up

# Iniciar en background (detached)
docker-compose up -d

# Reconstruir imágenes y iniciar
docker-compose up --build

# Iniciar servicios específicos
docker-compose up db redis

# Detener servicios
docker-compose down

# Detener y eliminar volumes (⚠️ se pierden datos)
docker-compose down -v

# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f web

# Ver estado de servicios
docker-compose ps

# Reiniciar un servicio
docker-compose restart web

# Escalar un servicio (múltiples instancias)
docker-compose up --scale celery=3
```

---

## 🔄 Modos de Ejecución

### Modo Desarrollo

```bash
# Usar override de desarrollo
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# O crear alias
alias dc-dev='docker-compose -f docker-compose.yml -f docker-compose.dev.yml'
dc-dev up
```

**Características del modo dev:**
- ✅ DEBUG=True
- ✅ Hot reload (código montado como volume)
- ✅ Runserver en lugar de Gunicorn
- ✅ Logs en nivel debug
- ✅ Puertos expuestos para acceso directo

### Modo Producción

```bash
# Usar override de producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# O crear alias
alias dc-prod='docker-compose -f docker-compose.yml -f docker-compose.prod.yml'
dc-prod up -d
```

**Características del modo prod:**
- ✅ DEBUG=False
- ✅ Gunicorn con 4 workers
- ✅ Nginx como proxy reverso
- ✅ Puertos internos no expuestos
- ✅ Logs en archivos
- ✅ Max tasks per child configurado

---

## 🧪 Comandos de Gestión

### Ejecutar Comandos Django

```bash
# Shell de Django
docker-compose exec web python manage.py shell

# Crear migraciones
docker-compose exec web python manage.py makemigrations

# Aplicar migraciones
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Collectstatic
docker-compose exec web python manage.py collectstatic --noinput

# Verificar configuración
docker-compose exec web python manage.py check --deploy
```

### Acceder a Base de Datos

```bash
# Shell de PostgreSQL
docker-compose exec db psql -U postgres -d meet_middleware_db

# Dump de base de datos
docker-compose exec db pg_dump -U postgres meet_middleware_db > backup.sql

# Restaurar base de datos
cat backup.sql | docker-compose exec -T db psql -U postgres -d meet_middleware_db
```

### Gestión de Celery

```bash
# Ver estado de workers
docker-compose exec celery celery -A app inspect active

# Ver tareas registradas
docker-compose exec celery celery -A app inspect registered

# Purgar cola de tareas
docker-compose exec celery celery -A app purge

# Ver logs de celery
docker-compose logs -f celery
```

---

## 📁 Estructura de Archivos

```
BACKEND/
├── docker-compose.yml           # Configuración base
├── docker-compose.dev.yml       # Override para desarrollo
├── docker-compose.prod.yml      # Override para producción
├── Dockerfile                   # Imagen de la aplicación
├── nginx.conf                   # Configuración de Nginx
├── .env.docker.example          # Template de variables
└── scripts/
    └── docker-entrypoint.sh     # Script de inicialización
```

---

## 🔐 Variables de Entorno

### Archivo .env.docker

Crear archivo `.env.docker` basado en `.env.docker.example`:

```bash
cp .env.docker.example .env.docker
```

**Variables requeridas:**
```bash
SECRET_KEY=...
DEBUG=False
POSTGRES_PASSWORD=...
```

**Variables opcionales:**
```bash
GOOGLE_SERVICE_ACCOUNT_FILE=...
DJANGO_SUPERUSER_USERNAME=...
```

### Cargar Variables

Docker Compose carga automáticamente `.env` del directorio actual.

Si quieres usar otro archivo:
```bash
docker-compose --env-file .env.docker up
```

---

## 🧪 Testing del Stack Completo

### Test 1: Verificar que todos los servicios inician

```bash
# Iniciar stack
docker-compose up -d

# Ver estado
docker-compose ps

# Esperado: todos los servicios "Up" y "healthy"
```

### Test 2: Verificar health checks

```bash
# Verificar web
curl http://localhost:8000/api/v1/health/

# Verificar PostgreSQL
docker-compose exec db pg_isready -U postgres

# Verificar Redis
docker-compose exec redis redis-cli ping
```

### Test 3: Verificar conectividad entre servicios

```bash
# Desde web, conectar a db
docker-compose exec web python manage.py dbshell

# Desde web, verificar Redis
docker-compose exec web python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

### Test 4: Crear reunión end-to-end

```bash
# 1. Crear superusuario
docker-compose exec web python manage.py createsuperuser

# 2. Acceder a Swagger UI
# http://localhost:8000/api/v1/docs/

# 3. Crear reunión desde Swagger
# POST /api/v1/meetings/

# 4. Verificar en base de datos
docker-compose exec db psql -U postgres -d meet_middleware_db -c "SELECT * FROM meetings_meeting;"
```

---

## 📊 Monitoreo y Logs

### Ver Logs

```bash
# Todos los servicios
docker-compose logs -f

# Solo web
docker-compose logs -f web

# Solo celery
docker-compose logs -f celery

# Últimas 100 líneas
docker-compose logs --tail=100 web

# Logs desde timestamp
docker-compose logs --since="2025-11-25T10:00:00" web
```

### Monitorear Recursos

```bash
# Ver uso de recursos
docker stats

# Ver solo containers de docker-compose
docker stats $(docker-compose ps -q)
```

---

## 🔄 Workflows Comunes

### Workflow 1: Primera Ejecución

```bash
# 1. Clonar repositorio
cd BACKEND/

# 2. Configurar variables de entorno
cp .env.docker.example .env.docker
# Editar .env.docker

# 3. Iniciar stack
docker-compose up -d

# 4. Esperar a que servicios estén healthy
docker-compose ps

# 5. Crear superusuario
docker-compose exec web python manage.py createsuperuser

# 6. Acceder a aplicación
# http://localhost:8000/api/v1/docs/
```

### Workflow 2: Desarrollo con Hot Reload

```bash
# 1. Usar modo desarrollo
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 2. Código se actualiza automáticamente
# Editar archivos .py en tu IDE

# 3. Django recarga automáticamente
```

### Workflow 3: Aplicar Nueva Migración

```bash
# 1. Crear migración
docker-compose exec web python manage.py makemigrations

# 2. Aplicar migración
docker-compose exec web python manage.py migrate

# 3. Reiniciar servicios (opcional)
docker-compose restart web celery
```

### Workflow 4: Actualizar Código (Deploy)

```bash
# 1. Pull cambios de Git
git pull

# 2. Reconstruir y reiniciar
docker-compose up -d --build

# 3. Aplicar migraciones
docker-compose exec web python manage.py migrate

# 4. Collectstatic
docker-compose exec web python manage.py collectstatic --noinput
```

### Workflow 5: Backup de Base de Datos

```bash
# 1. Crear backup
docker-compose exec db pg_dump -U postgres meet_middleware_db > backup_$(date +%Y%m%d).sql

# 2. Comprimir
gzip backup_$(date +%Y%m%d).sql

# 3. Para restaurar
gunzip backup_20251125.sql.gz
cat backup_20251125.sql | docker-compose exec -T db psql -U postgres -d meet_middleware_db
```

---

## 🔒 Seguridad

### Mejores Prácticas Implementadas

1. ✅ **Secrets desde variables de entorno**
   - No hardcodear passwords
   - Usar `.env.docker` (no versionado)

2. ✅ **Puertos limitados en producción**
   - Solo nginx expuesto (80, 443)
   - DB y Redis internos

3. ✅ **Health checks**
   - Verificar disponibilidad de servicios
   - Restart automático si fallan

4. ✅ **Usuario no-root**
   - Django corre como usuario django
   - PostgreSQL corre como postgres

5. ✅ **Networks aislados**
   - Servicios en red privada
   - Solo puertos necesarios expuestos

6. ✅ **Volumes read-only**
   - nginx lee staticfiles como read-only
   - Configuraciones como read-only

---

## 📈 Escalabilidad

### Escalar Servicios

```bash
# Escalar workers de Celery
docker-compose up -d --scale celery=5

# Escalar web (requiere load balancer)
docker-compose up -d --scale web=3
```

### Límites de Recursos

Agregar a docker-compose.yml:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## 🐛 Troubleshooting

### Problema: Servicios no inician

**Solución:**
```bash
# Ver logs de todos los servicios
docker-compose logs

# Ver estado detallado
docker-compose ps -a

# Verificar health checks
docker inspect meet-middleware-db | grep Health

# Reiniciar servicios
docker-compose restart
```

### Problema: PostgreSQL no está listo

**Solución:**
```bash
# Verificar logs de db
docker-compose logs db

# Verificar que el health check pase
docker-compose exec db pg_isready -U postgres

# Esperar más tiempo (aumentar start_period en healthcheck)
```

### Problema: Error de permisos en volumes

**Solución:**
```bash
# Crear directorios con permisos correctos
mkdir -p media staticfiles logs
chmod 777 media staticfiles logs

# O cambiar owner
sudo chown -R 1000:1000 media staticfiles logs
```

### Problema: Puerto 8000 ya en uso

**Solución:**
```bash
# Cambiar puerto en .env.docker
WEB_PORT=8001

# O en docker-compose.yml
ports:
  - "8001:8000"
```

### Problema: Celery no procesa tareas

**Solución:**
```bash
# Ver logs de celery
docker-compose logs celery

# Verificar conexión a Redis
docker-compose exec celery python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Reiniciar celery
docker-compose restart celery
```

---

## 🎯 Comandos Útiles

### Gestión de Stack

```bash
# Iniciar
docker-compose up -d

# Detener (preservar volúmenes)
docker-compose stop

# Reiniciar
docker-compose restart

# Pausar
docker-compose pause

# Reanudar
docker-compose unpause

# Detener y eliminar (preservar volúmenes)
docker-compose down

# Detener y eliminar todo (incluyendo volúmenes)
docker-compose down -v
```

### Inspección

```bash
# Ver configuración final
docker-compose config

# Ver servicios
docker-compose ps

# Ver imágenes
docker-compose images

# Ver top de procesos
docker-compose top
```

### Limpieza

```bash
# Eliminar containers detenidos
docker-compose rm

# Eliminar imágenes
docker-compose down --rmi all

# Eliminar todo (containers, volumes, networks, images)
docker-compose down -v --rmi all
```

---

## 📚 Archivos de Configuración

### docker-compose.yml (Base)
- Configuración compartida
- Servicios: db, redis, web, celery, celery-beat
- Para desarrollo y producción

### docker-compose.dev.yml (Desarrollo)
- DEBUG=True
- Hot reload de código
- Runserver en lugar de Gunicorn
- Puertos expuestos para debugging

### docker-compose.prod.yml (Producción)
- DEBUG=False
- Nginx como proxy
- Gunicorn optimizado
- Puertos internos no expuestos
- Logs en archivos

---

## 🔗 Endpoints Disponibles

Con docker-compose corriendo:

### Desarrollo:
- **Django:** http://localhost:8000
- **Admin:** http://localhost:8000/admin/
- **Swagger:** http://localhost:8000/api/v1/docs/
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

### Producción (con nginx):
- **Nginx:** http://localhost (puerto 80)
- **HTTPS:** https://localhost (puerto 443)
- **Django:** Interno (no expuesto)
- **PostgreSQL:** Interno (no expuesto)
- **Redis:** Interno (no expuesto)

---

## 📝 Próximos Pasos

Después de configurar docker-compose:

1. **Verificar funcionamiento** (PASO 12)
   - Iniciar stack con `docker-compose up`
   - Probar todos los endpoints
   - Verificar salud de servicios

2. **Configurar Celery Tasks** (PASO 13)
   - Crear tareas periódicas
   - Sincronizar grabaciones
   - Notificaciones

3. **Testing completo**
   - Tests unitarios
   - Tests de integración
   - Tests end-to-end

---

## 📚 Referencias

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Compose File Reference](https://docs.docker.com/compose/compose-file/)
- [Deploying Django with Docker](https://docs.docker.com/samples/django/)

