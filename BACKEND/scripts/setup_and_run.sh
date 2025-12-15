#!/bin/bash

# Script de setup y ejecución del middleware
# Ejecuta todos los comandos necesarios para iniciar el proyecto

set -e  # Salir si hay algún error

echo "=========================================="
echo "🚀 SETUP LOCAL - MEET MIDDLEWARE"
echo "=========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "${RED}❌ Error: manage.py no encontrado${NC}"
    echo "   Ejecuta este script desde la carpeta BACKEND/"
    exit 1
fi

# Paso 1: Verificar Python
echo "📦 Paso 1: Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "   ${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo "   ${RED}❌ Python 3 no encontrado${NC}"
    exit 1
fi

# Paso 2: Instalar dependencias
echo ""
echo "📦 Paso 2: Instalando dependencias..."
echo "   Esto puede tomar unos minutos..."
if pip3 install -r requirements.txt --quiet; then
    echo "   ${GREEN}✅ Dependencias instaladas${NC}"
else
    echo "   ${YELLOW}⚠️  Algunas dependencias pueden haber fallado${NC}"
    echo "   ${YELLOW}   Continuar de todas formas...${NC}"
fi

# Paso 3: Crear migraciones
echo ""
echo "🗄️  Paso 3: Creando migraciones..."
if python3 manage.py makemigrations; then
    echo "   ${GREEN}✅ Migraciones creadas${NC}"
else
    echo "   ${RED}❌ Error al crear migraciones${NC}"
    exit 1
fi

# Paso 4: Aplicar migraciones
echo ""
echo "🗄️  Paso 4: Aplicando migraciones..."
if python3 manage.py migrate; then
    echo "   ${GREEN}✅ Migraciones aplicadas${NC}"
else
    echo "   ${RED}❌ Error al aplicar migraciones${NC}"
    exit 1
fi

# Paso 5: Collectstatic (opcional, sin interacción)
echo ""
echo "📁 Paso 5: Recolectando archivos estáticos..."
if python3 manage.py collectstatic --noinput --clear > /dev/null 2>&1; then
    echo "   ${GREEN}✅ Archivos estáticos recolectados${NC}"
else
    echo "   ${YELLOW}⚠️  No se pudieron recolectar archivos estáticos (opcional)${NC}"
fi

# Paso 6: Verificar configuración
echo ""
echo "✅ Paso 6: Verificando configuración..."
if python3 manage.py check; then
    echo "   ${GREEN}✅ Configuración OK${NC}"
else
    echo "   ${RED}❌ Hay problemas en la configuración${NC}"
    exit 1
fi

# Instrucciones finales
echo ""
echo "=========================================="
echo "✅ SETUP COMPLETADO EXITOSAMENTE"
echo "=========================================="
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Crear superusuario (para acceder a /admin/):"
echo "   ${GREEN}python3 manage.py createsuperuser${NC}"
echo ""
echo "2. Iniciar el servidor:"
echo "   ${GREEN}python3 manage.py runserver${NC}"
echo ""
echo "3. Abrir en el navegador:"
echo "   - Django Admin:  ${GREEN}http://localhost:8000/admin/${NC}"
echo "   - Swagger UI:    ${GREEN}http://localhost:8000/api/v1/docs/${NC}"
echo "   - Health Check:  ${GREEN}http://localhost:8000/api/v1/health/${NC}"
echo ""
echo "📚 Documentación:"
echo "   - Ver SETUP_LOCAL.md para más detalles"
echo "   - Ver XOMA_INTEGRATION_GUIDE.md para integración con XOMA"
echo ""
echo "⚠️  Nota: Sin Google Service Account, se usarán links MOCK."
echo "   Ver ENV_SETUP.md para configurar Google."
echo ""

