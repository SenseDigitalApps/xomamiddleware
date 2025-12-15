#!/bin/bash
# Script de testing automatizado del stack Docker
# Verifica que todos los servicios funcionen correctamente

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🧪 TESTING DOCKER STACK - MEET MIDDLEWARE"
echo "=========================================="
echo ""

# Contadores
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Función para ejecutar test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "[$TESTS_TOTAL] Testing: $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# ===== PREREQUISITOS =====
echo "${BLUE}📋 Verificando prerequisitos...${NC}"
echo ""

run_test "Docker instalado" "command -v docker"
run_test "Docker Compose instalado" "command -v docker-compose"

echo ""

# ===== VERIFICAR SERVICIOS =====
echo "${BLUE}🐳 Verificando servicios Docker...${NC}"
echo ""

run_test "Servicio db corriendo" "docker-compose ps db | grep -q Up"
run_test "Servicio redis corriendo" "docker-compose ps redis | grep -q Up"
run_test "Servicio web corriendo" "docker-compose ps web | grep -q Up"
run_test "Servicio celery corriendo" "docker-compose ps celery | grep -q Up"
run_test "Servicio celery-beat corriendo" "docker-compose ps celery-beat | grep -q Up"

echo ""

# ===== VERIFICAR HEALTH CHECKS =====
echo "${BLUE}💊 Verificando health checks...${NC}"
echo ""

# Esperar un poco para que health checks se ejecuten
sleep 5

run_test "PostgreSQL healthy" "docker inspect meet-middleware-db | grep -q '\"Status\": \"healthy\"'"
run_test "Redis healthy" "docker inspect meet-middleware-redis | grep -q '\"Status\": \"healthy\"'"
run_test "Web healthy" "docker inspect meet-middleware-web | grep -q '\"Status\": \"healthy\"'"

echo ""

# ===== VERIFICAR ENDPOINTS =====
echo "${BLUE}🌐 Verificando endpoints...${NC}"
echo ""

run_test "Health check endpoint" "curl -f http://localhost:8000/api/v1/health/"
run_test "API Root endpoint" "curl -f http://localhost:8000/api/v1/"
run_test "Swagger UI" "curl -f http://localhost:8000/api/v1/docs/"
run_test "OpenAPI Schema" "curl -f http://localhost:8000/api/v1/schema/"
run_test "Django Admin" "curl -f http://localhost:8000/admin/"
run_test "Meetings endpoint" "curl -f http://localhost:8000/api/v1/meetings/"
run_test "Users endpoint" "curl -f http://localhost:8000/api/v1/users/"

echo ""

# ===== VERIFICAR CONECTIVIDAD =====
echo "${BLUE}🔗 Verificando conectividad entre servicios...${NC}"
echo ""

run_test "Web → PostgreSQL" "docker-compose exec -T db psql -U postgres -d meet_middleware_db -c 'SELECT 1;'"
run_test "Web → Redis" "docker-compose exec -T redis redis-cli ping"
run_test "Celery worker activo" "docker-compose exec -T celery celery -A app inspect ping"

echo ""

# ===== VERIFICAR VOLUMES =====
echo "${BLUE}💾 Verificando volumes...${NC}"
echo ""

run_test "Volume postgres_data existe" "docker volume ls | grep -q postgres_data"
run_test "Volume redis_data existe" "docker volume ls | grep -q redis_data"

echo ""

# ===== TEST DE INTEGRACIÓN =====
echo "${BLUE}🎬 Test de integración (crear reunión)...${NC}"
echo ""

# Crear reunión de prueba
MEETING_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_email": "test@example.com",
    "invited_emails": ["guest@example.com"],
    "scheduled_start": "2025-12-01T15:00:00Z",
    "scheduled_end": "2025-12-01T16:00:00Z"
  }')

if echo "$MEETING_RESPONSE" | grep -q '"id"'; then
    MEETING_ID=$(echo "$MEETING_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
    echo -e "[$((TESTS_TOTAL + 1))] Testing: Crear reunión... ${GREEN}✅ PASS${NC} (ID: $MEETING_ID)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Verificar que se guardó en BD
    run_test "Reunión guardada en BD" "docker-compose exec -T db psql -U postgres -d meet_middleware_db -c \"SELECT id FROM meetings_meeting WHERE id=$MEETING_ID;\" | grep -q $MEETING_ID"
    
    # Consultar reunión
    run_test "Consultar reunión creada" "curl -f http://localhost:8000/api/v1/meetings/$MEETING_ID/"
    
    # Listar reuniones
    run_test "Listar reuniones" "curl -f http://localhost:8000/api/v1/meetings/ | grep -q '\"id\":$MEETING_ID'"
else
    echo -e "[$((TESTS_TOTAL + 1))] Testing: Crear reunión... ${RED}❌ FAIL${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

echo ""

# ===== RESUMEN =====
echo "=========================================="
echo "📊 RESUMEN DE TESTS"
echo "=========================================="
echo ""
echo -e "Total:  $TESTS_TOTAL"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ¡TODOS LOS TESTS PASARON!${NC}"
    echo ""
    echo "🎉 El stack Docker está funcionando correctamente"
    echo ""
    echo "📝 Próximos pasos:"
    echo "   - Acceder a Swagger UI: http://localhost:8000/api/v1/docs/"
    echo "   - Acceder a Django Admin: http://localhost:8000/admin/"
    echo "   - Ver documentación: DOCKER_COMPOSE_DOCUMENTATION.md"
    echo ""
    exit 0
else
    echo -e "${RED}❌ ALGUNOS TESTS FALLARON${NC}"
    echo ""
    echo "🔧 Soluciones:"
    echo "   - Ver logs: docker-compose logs"
    echo "   - Reiniciar stack: docker-compose restart"
    echo "   - Ver troubleshooting en DOCKER_COMPOSE_DOCUMENTATION.md"
    echo ""
    exit 1
fi

