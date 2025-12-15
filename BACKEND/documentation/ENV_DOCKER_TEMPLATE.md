# Template de Variables de Entorno para Docker

## 📋 Instrucciones

Crea un archivo `.env.docker` en la raíz del proyecto BACKEND con el siguiente contenido:

```bash
# Copiar el contenido de abajo a .env.docker
```

---

## 📝 Contenido del Archivo .env.docker

```bash
# ===== Django Settings =====
SECRET_KEY=change-this-to-a-random-secret-key-in-production
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# ===== PostgreSQL Configuration =====
POSTGRES_DB=meet_middleware_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432

# ===== Redis Configuration =====
REDIS_PORT=6379
REDIS_PASSWORD=

# ===== Web Server =====
WEB_PORT=8000

# ===== Django Superuser (Creación automática - opcional) =====
# Si se configuran estas 3 variables, el superusuario se creará automáticamente
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin123

# ===== Google Workspace Integration (Opcional) =====
# Para usar Google Calendar API real, configurar estas variables
# GOOGLE_SERVICE_ACCOUNT_FILE=/app/credentials/service-account.json
# GOOGLE_WORKSPACE_ADMIN_EMAIL=admin@yourdomain.com
# GOOGLE_CALENDAR_ID=primary

# ===== CORS Configuration =====
CORS_ALLOW_ALL_ORIGINS=True
# CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## 🔐 Generar SECRET_KEY

Para producción, genera una clave secreta aleatoria:

### Opción 1: Python

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Opción 2: OpenSSL

```bash
openssl rand -base64 50
```

### Opción 3: Django Shell

```bash
docker-compose exec web python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 📝 Configuraciones por Ambiente

### Desarrollo

```bash
SECRET_KEY=dev-secret-key-not-for-production
DEBUG=True
ALLOWED_HOSTS=*
POSTGRES_PASSWORD=postgres
```

### Producción

```bash
SECRET_KEY=your-super-long-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
POSTGRES_PASSWORD=super-secure-password-here
DJANGO_SUPERUSER_PASSWORD=admin-secure-password
```

---

## ⚠️ Seguridad

### ❌ NO HACER:

- Subir `.env.docker` al repositorio
- Usar passwords débiles en producción
- Dejar DEBUG=True en producción
- Usar SECRET_KEY del ejemplo

### ✅ HACER:

- Mantener `.env.docker` en `.gitignore`
- Usar passwords fuertes y únicos
- Rotar SECRET_KEY periódicamente
- Usar variables de entorno en CI/CD

---

## 🔗 Uso con Docker Compose

Docker Compose carga automáticamente el archivo `.env` del directorio actual.

Para usar un archivo diferente:

```bash
# Opción 1: Renombrar a .env
mv .env.docker .env
docker-compose up

# Opción 2: Especificar con --env-file
docker-compose --env-file .env.docker up

# Opción 3: Exportar variables
export $(cat .env.docker | xargs)
docker-compose up
```

---

## 📚 Más Información

Ver documentación relacionada:
- [ENV_SETUP.md](./ENV_SETUP.md) - Configuración detallada de variables
- [DOCKER_COMPOSE_DOCUMENTATION.md](./DOCKER_COMPOSE_DOCUMENTATION.md) - Documentación de Docker Compose

