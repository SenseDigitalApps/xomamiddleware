# Dockerfile para Meet Middleware
# Middleware de integración Google Meet para XOMA

# ===== Stage 1: Base Image =====
FROM python:3.11-slim as base

# Metadatos
LABEL maintainer="Meet Middleware Team"
LABEL description="Middleware de integración Google Meet para XOMA"
LABEL version="1.0.0"

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=app.settings

# ===== Stage 2: Dependencies =====
FROM base as dependencies

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client y librerías de desarrollo
    libpq-dev \
    postgresql-client \
    # Herramientas de compilación (necesarias para algunas librerías Python)
    gcc \
    g++ \
    # Utilidades
    curl \
    netcat-traditional \
    # Limpieza
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ===== Stage 3: Application =====
FROM dependencies as application

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements.txt primero (mejor cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p staticfiles media logs && \
    chmod -R 755 staticfiles media logs

# Recolectar archivos estáticos
RUN python manage.py collectstatic --noinput || true

# ===== Stage 4: Production =====
FROM application as production

# Crear usuario no-root para seguridad
RUN groupadd -r django && \
    useradd -r -g django -u 1000 django && \
    chown -R django:django /app

# Cambiar a usuario no-root
USER django

# Exponer puerto 8000
EXPOSE 8000

# Copiar y configurar entrypoint script
USER root
COPY scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    chown django:django /usr/local/bin/docker-entrypoint.sh
USER django

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/api/v1/health/ || exit 1

# Entrypoint y comando por defecto
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "app.wsgi:application"]
