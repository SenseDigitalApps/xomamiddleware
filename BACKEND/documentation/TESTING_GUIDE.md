# Guía de Procedimientos de Testing - Meet Middleware

## Resumen

Esta guía describe los procedimientos de testing implementados para verificar el correcto funcionamiento del middleware de Google Meet.

---

## Tipos de Testing Implementados

### 1. Testing Automatizado del Stack Docker

**Script:** scripts/test_docker_stack.sh

**Procedimiento de Ejecución:**

```bash
cd BACKEND/

# Verificar que el stack esté en ejecución
docker-compose up -d

# Ejecutar suite de tests
./scripts/test_docker_stack.sh
```

**Cobertura de Tests:**

- Verificación de instalación de Docker y Docker Compose
- Verificación de servicios en ejecución (db, redis, web, celery, celery-beat)
- Verificación de health checks
- Verificación de respuesta de endpoints
- Verificación de conectividad entre servicios
- Verificación de existencia de volumes
- Creación de reunión de prueba
- Verificación de persistencia en base de datos
- Consulta de reunión creada

**Resultado Esperado:**

```
==========================================
TESTING DOCKER STACK - MEET MIDDLEWARE
==========================================

Verificando prerequisitos...
[1] Testing: Docker instalado... PASS
[2] Testing: Docker Compose instalado... PASS

Verificando servicios Docker...
[3] Testing: Servicio db corriendo... PASS
[4] Testing: Servicio redis corriendo... PASS
[5] Testing: Servicio web corriendo... PASS

RESUMEN DE TESTS
Total:  25
Passed: 25
Failed: 0

TODOS LOS TESTS COMPLETADOS EXITOSAMENTE
```

---

### 2. Testing de Integración con Python

**Script:** scripts/test_integration.py

**Procedimiento de Ejecución:**

```bash
cd BACKEND/

# Verificar que el stack esté en ejecución
docker-compose up -d

# Ejecutar tests de integración
python3 scripts/test_integration.py
```

**Cobertura de Tests:**

- Verificación de endpoint health check
- Verificación de endpoint API Root
- Verificación de disponibilidad de Swagger UI
- Validación de schema OpenAPI
- Listado de reuniones
- Creación de reunión
- Obtención de detalle de reunión
- Actualización de reunión
- Cancelación de reunión
- Validación de manejo de errores
- Listado de usuarios
- Listado de participantes
- Listado de grabaciones

**Resultado Esperado:**

```
Esperando que el stack esté listo...
Servidor listo

Ejecutando tests de integración...
[1] Health check endpoint... PASS
[2] API Root endpoint... PASS
[15] Crear reunión... PASS (ID: 1)

RESUMEN FINAL
Total:  15
Passed: 15
Failed: 0
Success Rate: 100.0%

TODOS LOS TESTS COMPLETADOS EXITOSAMENTE
```

---

### 3. Testing Manual

Consulte DOCKER_VERIFICATION_GUIDE.md para procedimiento paso a paso detallado.

**Incluye:**

- Verificación visual de servicios
- Navegación en interfaz Swagger UI
- Creación de reuniones desde interfaz web
- Verificación en panel de administración Django
- Ejecución de consultas directas a PostgreSQL

---

## Escenarios de Testing

### Escenario 1: Instalación Inicial

**Objetivo:** Verificar funcionamiento del sistema desde configuración inicial

**Procedimiento:**

```bash
# 1. Limpieza completa del sistema
docker-compose down -v
docker system prune -a -f

# 2. Inicialización del stack
docker-compose up --build -d

# 3. Período de espera para estabilización
sleep 60

# 4. Ejecución de suite de tests
./scripts/test_docker_stack.sh

# 5. Creación de superusuario
docker-compose exec web python manage.py createsuperuser

# 6. Verificación en Swagger UI
# URL: http://localhost:8000/api/v1/docs/
```

---

### Escenario 2: Verificación Post-Actualización

**Objetivo:** Validar que modificaciones de código se aplican correctamente

**Procedimiento:**

```bash
# 1. Aplicar modificaciones al código

# 2. Reconstrucción y reinicio de servicios
docker-compose up --build -d

# 3. Verificación de ausencia de errores
docker-compose logs web | grep -i error

# 4. Testing de endpoints modificados
curl http://localhost:8000/api/v1/meetings/
```

---

### Escenario 3: Verificación de Persistencia

**Objetivo:** Confirmar que los datos persisten entre reinicios del sistema

**Procedimiento:**

```bash
# 1. Creación de datos de prueba
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{"organizer_email":"test@ex.com","invited_emails":["guest@ex.com"]}'

# 2. Detención del stack
docker-compose down

# 3. Reinicio del stack
docker-compose up -d

# 4. Período de espera
sleep 30

# 5. Verificación de datos
curl http://localhost:8000/api/v1/meetings/

# Resultado: La reunión creada debe estar presente
```

---

### Escenario 4: Testing de Escalabilidad

**Objetivo:** Verificar capacidad de escalamiento horizontal

**Procedimiento:**

```bash
# 1. Escalamiento de workers de Celery
docker-compose up -d --scale celery=3

# 2. Verificación de 3 instancias activas
docker-compose ps celery

# 3. Verificación de actividad de workers
docker-compose exec celery celery -A app inspect ping
```

---

### Escenario 5: Testing de Recuperación ante Fallos

**Objetivo:** Validar mecanismos de recuperación automática

**Procedimiento:**

```bash
# 1. Terminación forzada de container web
docker kill meet-middleware-web

# 2. Espera para restart automático
sleep 10

# 3. Verificación de estado
docker-compose ps web

# 4. Verificación de funcionalidad
curl http://localhost:8000/api/v1/health/
```

---

## Workflow de Testing para Desarrollo

```bash
# 1. Iniciar en modo desarrollo
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 2. Realizar modificaciones de código
# (Hot reload automático activado)

# 3. Testing en Swagger UI
# URL: http://localhost:8000/api/v1/docs/

# 4. Monitoreo de logs en tiempo real
docker-compose logs -f web
```

---

## Workflow de Testing para CI/CD

```bash
# 1. Inicialización de stack
docker-compose up -d

# 2. Espera para estabilización
sleep 60

# 3. Ejecución de tests automatizados
./scripts/test_docker_stack.sh
EXIT_CODE=$?

# 4. Limpieza de recursos
docker-compose down -v

# 5. Retorno de código de salida
exit $EXIT_CODE
```

---

## Métricas de Performance

### Tiempos de Ejecución Esperados

| Operación | Tiempo Estimado |
|-----------|----------------|
| docker-compose up --build (inicial) | 3-5 minutos |
| docker-compose up --build (con cache) | 30-60 segundos |
| docker-compose up -d (sin rebuild) | 10-20 segundos |
| Estabilización de health checks | 30-40 segundos |
| test_docker_stack.sh | 30-40 segundos |
| test_integration.py | 20-30 segundos |

### Uso de Recursos Esperado

| Servicio | RAM | CPU | Almacenamiento |
|----------|-----|-----|----------------|
| PostgreSQL | 50-100 MB | 1-3% | 100 MB |
| Redis | 20-50 MB | <1% | 50 MB |
| Web (Django) | 100-200 MB | 2-5% | - |
| Celery Worker | 100-150 MB | 1-3% | - |
| Celery Beat | 50-100 MB | <1% | - |
| **TOTAL** | **~500 MB** | **~10%** | **~150 MB** |

---

## Tests Críticos para Integración con XOMA

Antes de proceder con la integración, verificar que estos tests se completen exitosamente:

### Test 1: Creación de Reunión

```bash
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_email": "doctor@clinica.com",
    "invited_emails": ["paciente@correo.com"],
    "scheduled_start": "2025-12-01T15:00:00Z",
    "scheduled_end": "2025-12-01T16:00:00Z",
    "external_reference": "xoma_appointment_1234"
  }'
```

**Resultado Esperado:** HTTP Status 201 con campo meet_link en response

### Test 2: Consulta de Reunión

```bash
curl http://localhost:8000/api/v1/meetings/1/
```

**Resultado Esperado:** HTTP Status 200 con datos completos

### Test 3: Listado de Reuniones

```bash
curl http://localhost:8000/api/v1/meetings/
```

**Resultado Esperado:** HTTP Status 200 con array de reuniones

---

## Generación de Reportes

### Procedimiento de Generación

```bash
# Ejecución de tests con captura de output
./scripts/test_docker_stack.sh > test_report_$(date +%Y%m%d_%H%M%S).txt 2>&1

# Visualización de reporte
cat test_report_*.txt
```

### Estructura del Reporte

```
==========================================
TESTING DOCKER STACK - MEET MIDDLEWARE
==========================================

Verificando prerequisitos...
[1] Testing: Docker instalado... PASS
[2] Testing: Docker Compose instalado... PASS

Verificando servicios Docker...
[3] Testing: Servicio db corriendo... PASS

RESUMEN DE TESTS
Total:  25
Passed: 25
Failed: 0

Fecha: 2025-11-25 17:30:00
Duración: 35 segundos
```

---

## Referencias

- DOCKER_VERIFICATION_GUIDE.md - Verificación detallada paso a paso
- DOCKER_COMPOSE_DOCUMENTATION.md - Documentación de Docker Compose
- XOMA_INTEGRATION_GUIDE.md - Manual de integración con XOMA
