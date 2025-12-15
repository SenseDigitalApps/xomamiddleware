#!/bin/bash
# Docker entrypoint script para Meet Middleware
# Este script se ejecuta cuando el container inicia

set -e

echo "🐳 =========================================="
echo "🐳 MEET MIDDLEWARE - Docker Entrypoint"
echo "🐳 =========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== Función para esperar PostgreSQL =====
wait_for_postgres() {
    if [ -n "$POSTGRES_HOST" ]; then
        echo "${BLUE}⏳ Esperando a que PostgreSQL esté listo...${NC}"
        echo "   Host: $POSTGRES_HOST"
        echo "   Port: ${POSTGRES_PORT:-5432}"
        
        max_attempts=30
        attempt=1
        
        while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
            if [ $attempt -eq $max_attempts ]; then
                echo "${RED}❌ Error: PostgreSQL no está disponible después de $max_attempts intentos${NC}"
                exit 1
            fi
            
            echo "   Intento $attempt/$max_attempts..."
            sleep 1
            attempt=$((attempt + 1))
        done
        
        echo "${GREEN}✅ PostgreSQL está listo${NC}"
        echo ""
    else
        echo "${YELLOW}⚠️  POSTGRES_HOST no configurado. Usando SQLite${NC}"
        echo ""
    fi
}

# ===== Función para esperar Redis =====
wait_for_redis() {
    if [ -n "$CELERY_BROKER_URL" ] && [[ "$CELERY_BROKER_URL" == redis://* ]]; then
        # Extraer host y puerto de CELERY_BROKER_URL
        REDIS_HOST=$(echo $CELERY_BROKER_URL | sed -n 's/redis:\/\/\([^:]*\).*/\1/p')
        REDIS_PORT=$(echo $CELERY_BROKER_URL | sed -n 's/redis:\/\/[^:]*:\([0-9]*\).*/\1/p')
        REDIS_PORT=${REDIS_PORT:-6379}
        
        echo "${BLUE}⏳ Esperando a que Redis esté listo...${NC}"
        echo "   Host: $REDIS_HOST"
        echo "   Port: $REDIS_PORT"
        
        max_attempts=15
        attempt=1
        
        while ! nc -z "$REDIS_HOST" "$REDIS_PORT"; do
            if [ $attempt -eq $max_attempts ]; then
                echo "${YELLOW}⚠️  Redis no está disponible (Celery no funcionará)${NC}"
                break
            fi
            
            echo "   Intento $attempt/$max_attempts..."
            sleep 1
            attempt=$((attempt + 1))
        done
        
        if nc -z "$REDIS_HOST" "$REDIS_PORT"; then
            echo "${GREEN}✅ Redis está listo${NC}"
        fi
        echo ""
    fi
}

# ===== Ejecutar funciones de espera =====
wait_for_postgres
wait_for_redis

# ===== Ejecutar migraciones =====
echo "${BLUE}🗄️  Ejecutando migraciones de base de datos...${NC}"
if python manage.py migrate --noinput; then
    echo "${GREEN}✅ Migraciones aplicadas exitosamente${NC}"
    echo ""
else
    echo "${RED}❌ Error al aplicar migraciones${NC}"
    exit 1
fi

# ===== Recolectar archivos estáticos =====
echo "${BLUE}📁 Recolectando archivos estáticos...${NC}"
if python manage.py collectstatic --noinput --clear > /dev/null 2>&1; then
    echo "${GREEN}✅ Archivos estáticos recolectados${NC}"
    echo ""
else
    echo "${YELLOW}⚠️  No se pudieron recolectar archivos estáticos${NC}"
    echo ""
fi

# ===== Crear superusuario si no existe (opcional) =====
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "${BLUE}👤 Verificando superusuario...${NC}"
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('✅ Superusuario creado')
else:
    print('ℹ️  Superusuario ya existe')
END
    echo ""
fi

# ===== Verificar configuración =====
echo "${BLUE}✅ Verificando configuración del proyecto...${NC}"
if python manage.py check --deploy > /dev/null 2>&1; then
    echo "${GREEN}✅ Configuración OK${NC}"
else
    echo "${YELLOW}⚠️  Hay advertencias de configuración (ver con: python manage.py check --deploy)${NC}"
fi
echo ""

# ===== Información del sistema =====
echo "${GREEN}=========================================="
echo "✅ MEET MIDDLEWARE LISTO"
echo "==========================================${NC}"
echo ""
echo "📊 Información:"
echo "   - Python: $(python --version)"
echo "   - Django: $(python -c 'import django; print(django.get_version())')"
echo "   - Base de datos: ${POSTGRES_DB:-SQLite}"
echo ""
echo "🚀 Iniciando aplicación..."
echo ""

# ===== Ejecutar comando pasado como argumentos =====
exec "$@"

