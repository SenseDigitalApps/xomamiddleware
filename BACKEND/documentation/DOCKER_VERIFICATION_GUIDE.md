# Guía de Verificación del Stack Docker

## Resumen

Este documento proporciona el procedimiento detallado para verificar el correcto funcionamiento del stack completo de Docker Compose, incluyendo todos los servicios y sus interconexiones.

---

## Método 1: Verificación Automatizada (Recomendado)

```bash
cd BACKEND/

# 1. Inicialización del stack
docker-compose up -d

# 2. Período de espera para estabilización (60 segundos)
sleep 60

# 3. Ejecución de suite de tests automatizados
./scripts/test_docker_stack.sh

# Alternativa con Python:
python3 scripts/test_integration.py
```

---

## Método 2: Verificación Manual Detallada

### PASO 1: Inicialización del Stack

```bash
cd /Users/camilo/Documents/Sense/XOMA\ MIDDLEWARE/BACKEND

# Iniciar todos los servicios con reconstrucción
docker-compose up --build
```

**Salida Esperada:**

```
Creating network "backend_meet-network" with driver "bridge"
Creating volume "backend_postgres_data" with default driver
Creating volume "backend_redis_data" with default driver
Creating meet-middleware-db ... done
Creating meet-middleware-redis ... done
Creating meet-middleware-web ... done
Creating meet-middleware-celery ... done
Creating meet-middleware-celery-beat ... done
```

**Mensaje de Confirmación:**

```
MEET MIDDLEWARE LISTO
Iniciando aplicación...
```

**Tiempo de Inicialización:** 2-3 minutos (primera ejecución)

---

### PASO 2: Verificación de Estado de Servicios

En terminal adicional:

```bash
cd /Users/camilo/Documents/Sense/XOMA\ MIDDLEWARE/BACKEND

# Verificar estado de todos los servicios
docker-compose ps
```

**Salida Esperada:**

```
NAME                          STATUS                 PORTS
meet-middleware-db            Up (healthy)           0.0.0.0:5432->5432/tcp
meet-middleware-redis         Up (healthy)           0.0.0.0:6379->6379/tcp
meet-middleware-web           Up (healthy)           0.0.0.0:8000->8000/tcp
meet-middleware-celery        Up
meet-middleware-celery-beat   Up
```

Todos los servicios deben mostrar estado "Up", con db, redis y web indicando "(healthy)".

---

### PASO 3: Verificación de Health Check

```bash
curl http://localhost:8000/api/v1/health/
```

**Respuesta Esperada:**

```json
{
  "status": "ok",
  "api": "running",
  "database": "connected"
}
```

Esta respuesta confirma operatividad correcta del middleware.

---

### PASO 4: Verificación de API Root

```bash
curl http://localhost:8000/api/v1/
```

**Respuesta Esperada:**

```json
{
  "message": "Meet Middleware API - XOMA Integration",
  "version": "1.0.0",
  "endpoints": {
    "health": "/api/v1/health/",
    "docs": "/api/v1/docs/",
    "meetings": "/api/v1/meetings/"
  }
}
```

---

### PASO 5: Verificación de Swagger UI

Acceder mediante navegador:

```
http://localhost:8000/api/v1/docs/
```

**Elementos a Verificar:**

- Interfaz de Swagger UI completamente renderizada
- Listado completo de endpoints disponibles
- Secciones organizadas: meetings, participants, recordings, users
- Funcionalidad "Try it out" operativa en cada endpoint

---

### PASO 6: Verificación de Panel de Administración

Acceder mediante navegador:

```
http://localhost:8000/admin/
```

**Elementos a Verificar:**

- Página de login de Django Admin visible
- Formulario de autenticación presente

---

### PASO 7: Creación de Superusuario

Si no se creó automáticamente:

```bash
docker-compose exec web python manage.py createsuperuser
```

**Credenciales Preconfiguradas:**

- Username: admin
- Email: admin@meetmiddleware.com
- Password: Admin123!

**Nota:** El sistema ya tiene estas credenciales configuradas para acceso inmediato.

---

### PASO 8: Acceso al Panel de Administración

1. Acceder a http://localhost:8000/admin/
2. Autenticar con credenciales: admin / Admin123!
3. Verificar secciones disponibles:
   - ACCOUNTS - Users
   - MEETINGS - Meetings, Participants, Meeting recordings

---

### PASO 9: Creación de Reunión desde Swagger UI

1. Acceder a http://localhost:8000/api/v1/docs/
2. Localizar POST /api/v1/meetings/
3. Activar "Try it out"
4. Ingresar datos:

```json
{
  "organizer_email": "doctor@test.com",
  "invited_emails": ["paciente@test.com"],
  "scheduled_start": "2025-12-01T15:00:00Z",
  "scheduled_end": "2025-12-01T16:00:00Z",
  "external_reference": "test_appointment_001"
}
```

5. Ejecutar request
6. Verificar respuesta:
   - Código HTTP: 201
   - Campos presentes: id, google_event_id, meet_link, status, participants_count

---

### PASO 10: Verificación en Panel de Administración

1. Acceder a http://localhost:8000/admin/
2. Navegar a "Meetings" en sección MEETINGS
3. Verificar presencia de reunión creada
4. Examinar detalles completos
5. Verificar sección inline de participantes (2 participantes)

---

### PASO 11: Verificación en Base de Datos

```bash
# Conexión a PostgreSQL
docker-compose exec db psql -U postgres -d meet_middleware_db
```

**Comandos SQL de Verificación:**

```sql
-- Consulta de reuniones
SELECT id, google_event_id, meet_link, status FROM meetings_meeting;

-- Consulta de participantes
SELECT id, email, role FROM meetings_participant;

-- Consulta de usuarios
SELECT id, username, email, role FROM accounts_user;

-- Salir del prompt
\q
```

**Datos Esperados:**

- Reunión creada con datos completos
- 2 participantes (organizador + invitado)
- Usuarios creados automáticamente

---

### PASO 12: Verificación de Endpoints Adicionales

```bash
# Listado de reuniones
curl http://localhost:8000/api/v1/meetings/

# Detalle de reunión específica
curl http://localhost:8000/api/v1/meetings/1/

# Listado de usuarios
curl http://localhost:8000/api/v1/users/

# Listado de participantes
curl http://localhost:8000/api/v1/participants/

# Estadísticas de usuarios
curl http://localhost:8000/api/v1/users/stats/

# Información del sistema
curl http://localhost:8000/api/v1/info/
```

---

### PASO 13: Verificación de Logs del Sistema

```bash
# Logs de todos los servicios
docker-compose logs

# Logs específicos de web
docker-compose logs web

# Filtrado de errores
docker-compose logs web | grep -i error

# Logs en tiempo real
docker-compose logs -f web
```

**Mensajes a Verificar:**

- "MEET MIDDLEWARE LISTO" - Inicialización exitosa
- "PostgreSQL está listo" - Conexión a base de datos
- "Migraciones aplicadas exitosamente"
- Ausencia de errores críticos

---

### PASO 14: Verificación de Celery

```bash
# Verificación de workers activos
docker-compose exec celery celery -A app inspect active

# Listado de tareas registradas
docker-compose exec celery celery -A app inspect registered

# Estadísticas de celery
docker-compose exec celery celery -A app inspect stats

# Logs de celery
docker-compose logs celery
```

---

### PASO 15: Testing de Persistencia

```bash
# 1. Crear reunión de prueba

# 2. Detener stack
docker-compose down

# 3. Reiniciar stack
docker-compose up -d

# 4. Esperar estabilización
sleep 30

# 5. Verificar persistencia
curl http://localhost:8000/api/v1/meetings/

# La reunión debe permanecer en el sistema
```

---

### PASO 16: Monitoreo de Recursos

```bash
# Uso de CPU y memoria
docker stats --no-stream

# Uso de almacenamiento
docker system df

# Estadísticas de containers específicos
docker stats $(docker-compose ps -q)
```

**Valores Esperados:**

- Web: Menos de 200 MB RAM, menos de 5% CPU
- PostgreSQL: Menos de 100 MB RAM, menos de 3% CPU
- Redis: Menos de 50 MB RAM, menos de 1% CPU
- Celery: Menos de 150 MB RAM, menos de 5% CPU

---

## Checklist de Verificación Completa

### Prerequisitos

- [ ] Docker instalado (verificar con docker --version)
- [ ] Docker Compose instalado (verificar con docker-compose --version)
- [ ] Puertos 8000, 5432, 6379 disponibles

### Servicios

- [ ] PostgreSQL corriendo y healthy
- [ ] Redis corriendo y healthy
- [ ] Django Web corriendo y healthy
- [ ] Celery Worker corriendo
- [ ] Celery Beat corriendo

### Conectividad

- [ ] Conexión exitosa web → db
- [ ] Conexión exitosa web → redis
- [ ] Conexión exitosa celery → db
- [ ] Conexión exitosa celery → redis

### Base de Datos

- [ ] Migraciones aplicadas automáticamente
- [ ] Tablas creadas en PostgreSQL
- [ ] Superusuario creado

### Endpoints

- [ ] /api/v1/health/ retorna JSON correcto
- [ ] /api/v1/ retorna API Root
- [ ] /api/v1/docs/ carga Swagger UI
- [ ] /admin/ accesible

### Funcionalidad

- [ ] Login en administración funcional
- [ ] Modelos visibles en admin
- [ ] Creación de reunión desde Swagger (201)
- [ ] Reunión en listado
- [ ] Reunión en admin
- [ ] Reunión en PostgreSQL
- [ ] meet_link generado

### Persistencia

- [ ] Datos persisten en reinicios
- [ ] Volumes existen

### Performance

- [ ] Servicios consumen menos de 500 MB RAM total
- [ ] Respuesta de API menor a 1 segundo
- [ ] Health check pasa consistentemente

---

## Pruebas Adicionales

### Prueba 1: CRUD Completo

```bash
# Crear
MEETING_ID=$(curl -s -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{"organizer_email":"test@ex.com","invited_emails":["guest@ex.com"]}' \
  | grep -o '"id":[0-9]*' | grep -o '[0-9]*')

# Leer
curl http://localhost:8000/api/v1/meetings/$MEETING_ID/

# Actualizar
curl -X PATCH http://localhost:8000/api/v1/meetings/$MEETING_ID/ \
  -H "Content-Type: application/json" \
  -d '{"status":"FINISHED"}'

# Cancelar
curl -X DELETE http://localhost:8000/api/v1/meetings/$MEETING_ID/
```

### Prueba 2: Validaciones

```bash
# Intentar creación con datos inválidos (debe retornar 400)
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -d '{"organizer_email":"test@ex.com","invited_emails":[]}'
```

### Prueba 3: Sistema de Filtros

```bash
# Filtrado por estado
curl "http://localhost:8000/api/v1/meetings/?status=CREATED"

# Filtrado por organizador
curl "http://localhost:8000/api/v1/meetings/?organizer=1"

# Filtrado por fecha
curl "http://localhost:8000/api/v1/meetings/?scheduled_start__gte=2025-12-01"
```

---

## Resolución de Problemas

### Problema 1: Servicios no Inician

**Síntoma:** Container unhealthy

**Solución:**

```bash
docker-compose logs db
lsof -i:5432
docker-compose restart db
```

### Problema 2: Web no Conecta a Base de Datos

**Síntoma:** OperationalError: could not connect to server

**Solución:**

```bash
docker-compose ps db
sleep 30
docker-compose exec web nc -zv db 5432
```

### Problema 3: Migraciones no Aplicadas

**Síntoma:** no such table

**Solución:**

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py showmigrations
```

### Problema 4: Health Check Falla

**Síntoma:** Container unhealthy

**Solución:**

```bash
docker inspect meet-middleware-web | grep -A 10 Health
curl http://localhost:8000/api/v1/health/
docker-compose restart web
```

### Problema 5: Puerto Ocupado

**Síntoma:** address already in use

**Solución:**

```bash
lsof -ti:8000 | xargs kill -9
```

---

## Comandos de Gestión del Stack

### Gestión General

```bash
# Iniciar en background
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Verificar estado
docker-compose ps

# Reiniciar servicio específico
docker-compose restart web

# Detener stack (preservar datos)
docker-compose down

# Detener y eliminar volumes
docker-compose down -v
```

### Debugging

```bash
# Acceso a shell en container
docker-compose exec web bash

# Django shell interactivo
docker-compose exec web python manage.py shell

# Ver procesos en ejecución
docker-compose top

# Logs con límite de líneas
docker-compose logs --tail=50 web

# Ver configuración final efectiva
docker-compose config
```

### Operaciones de Base de Datos

```bash
# Conexión a PostgreSQL
docker-compose exec db psql -U postgres -d meet_middleware_db

# Backup de base de datos
docker-compose exec db pg_dump -U postgres meet_middleware_db > backup.sql

# Restauración de base de datos
cat backup.sql | docker-compose exec -T db psql -U postgres -d meet_middleware_db
```

---

## Resultados Esperados

Al completar el procedimiento de verificación:

- Stack completo operativo con 5 servicios
- PostgreSQL con datos persistentes
- Redis funcionando como cache y broker
- Django API respondiendo en puerto 8000
- Celery Worker procesando tareas
- Celery Beat scheduler activo
- Swagger UI accesible y funcional
- Panel de administración Django accesible
- Funcionalidad de creación de reuniones operativa
- Persistencia de datos entre reinicios verificada

---

## Configuración Opcional Post-Verificación

### 1. Configuración de Google Service Account

Para obtener enlaces reales de Google Meet:

- Consulte ENV_SETUP.md sección 2
- Descargue credenciales JSON de Google Cloud
- Configure ruta en docker-compose.yml

### 2. Configuración de Tareas Periódicas de Celery

- Sincronización de grabaciones desde Google Drive
- Verificación periódica de estados de reuniones
- Limpieza automatizada de datos antiguos

### 3. Testing Completo

- Implementación de tests unitarios
- Tests de integración
- Tests end-to-end con plataforma XOMA

---

## Comandos de Limpieza

### Finalización de Sesión de Testing

```bash
# Detener stack (preservar datos)
docker-compose down

# Detener y eliminar todos los recursos
docker-compose down -v

# Limpieza de imágenes no utilizadas
docker image prune -a

# Limpieza completa del sistema Docker
docker system prune -a --volumes
```

---

## Confirmación de Verificación Exitosa

Si todos los ítems del checklist están completados, el middleware de Google Meet está completamente funcional en Docker y preparado para:

- Recepción de peticiones desde XOMA
- Creación de reuniones de Google Meet
- Gestión de participantes y metadatos de grabaciones
- Escalamiento según demanda operativa

---

## Próximos Pasos

### 1. Integración con XOMA

Consulte XOMA_INTEGRATION_GUIDE.md para procedimientos de integración, configuración de endpoints y testing end-to-end.

### 2. Configuración de Google Workspace

Implemente autenticación real de Service Account para obtener enlaces funcionales de Google Meet en lugar de enlaces simulados.

### 3. Configuración de Monitoreo

Implemente sistemas de:

- Logging centralizado
- Métricas de uso y performance
- Sistema de alertas

### 4. Despliegue en Producción

Configure:

- SSL/HTTPS mediante certificados
- Dominio personalizado
- Utilice docker-compose.prod.yml
- Implemente backups automatizados

---

**Estado al Completar:** Sistema completamente verificado y preparado para operación.
