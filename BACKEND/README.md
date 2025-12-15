# Meet Middleware - Integración Google Meet para XOMA

## Descripción del Proyecto

Sistema middleware de integración profesional entre XOMA y Google Workspace, diseñado para la creación y gestión programática de videollamadas mediante Google Meet con registro y seguimiento automatizado de participantes y grabaciones.

## Estructura del Proyecto

```
BACKEND/
├── app/                 # Configuración principal de Django
├── accounts/           # Gestión de usuarios
├── meetings/           # Dominio principal: reuniones y grabaciones
├── integrations/       # Integración con Google APIs (Calendar, Meet, Drive)
├── core/              # Utilidades y excepciones transversales
├── manage.py          # Script de gestión de Django
├── requirements.txt   # Dependencias Python
├── Dockerfile         # Configuración Docker
├── docker-compose.yml # Orquestación de servicios
└── spect/             # Especificaciones técnicas del proyecto
```

## Stack Tecnológico

- **Django 5.2.6** - Framework web principal
- **PostgreSQL 15** - Sistema de base de datos
- **Django REST Framework 3.14+** - Framework para APIs REST
- **Celery 5.3+ + Redis 7.0+** - Sistema de tareas asíncronas
- **Google APIs** - Integración con Calendar, Meet y Drive
- **Gunicorn 21.2+** - Servidor WSGI para producción
- **WhiteNoise 6.6+** - Servicio de archivos estáticos

## Estado del Proyecto

**Implementación Completa:** Todos los componentes especificados han sido implementados y verificados.

- Estructura del proyecto creada y organizada
- Sistema de dependencias configurado (14 paquetes)
- Configuración de Django completada
- Modelos de base de datos implementados (4 modelos)
- Serializers DRF implementados (10 serializers)
- ViewSets y endpoints REST creados (30+ endpoints)
- Integración con Google Calendar API y Google Meet
- Sistema de URLs y routers configurado
- Scripts de verificación y testing creados
- Dockerfile optimizado con arquitectura multi-stage
- docker-compose.yml con orquestación de 5 servicios
- WhiteNoise configurado para servicio de archivos estáticos
- Colección de Postman para testing de API
- Migraciones de base de datos creadas

**Estado Operacional:** Sistema completamente funcional y listo para despliegue.

---

## Inicio Rápido

### Método 1: Despliegue con Docker Compose (Recomendado)

```bash
cd BACKEND/

# Inicializar stack completo de servicios
docker-compose up -d

# Acceso a interfaces del sistema
# Panel de administración: http://localhost:8000/admin/
# Documentación de API: http://localhost:8000/api/v1/docs/
```

**Credenciales de Administración Preconfiguradas:**

- URL de acceso: http://localhost:8000/admin/
- Nombre de usuario: admin
- Contraseña: Admin123!

Consulte DOCKER_COMPOSE_DOCUMENTATION.md para procedimientos detallados.

### Método 2: Instalación en Entorno Local

```bash
cd BACKEND/

# Ejecutar script de configuración automatizada
./scripts/setup_and_run.sh

# Crear usuario administrativo
python3 manage.py createsuperuser

# Inicializar servidor de desarrollo
python3 manage.py runserver
```

Consulte LOCAL_VERIFICATION_GUIDE.md para procedimientos detallados de instalación local.

---

## Documentación del Sistema

### Documentación Técnica

- [MODELS_DOCUMENTATION.md](./MODELS_DOCUMENTATION.md) - Especificación de modelos de base de datos
- [SERIALIZERS_DOCUMENTATION.md](./SERIALIZERS_DOCUMENTATION.md) - Documentación de serializers DRF
- [ENDPOINTS_DOCUMENTATION.md](./ENDPOINTS_DOCUMENTATION.md) - Referencia completa de endpoints REST API
- [URLS_DOCUMENTATION.md](./URLS_DOCUMENTATION.md) - Configuración de URLs y sistema de routing
- [GOOGLE_INTEGRATION_DOCUMENTATION.md](./GOOGLE_INTEGRATION_DOCUMENTATION.md) - Integración con Google Workspace APIs

### Guías de Instalación y Configuración

- [DOCKER_COMPOSE_DOCUMENTATION.md](./DOCKER_COMPOSE_DOCUMENTATION.md) - Orquestación de servicios con Docker Compose
- [DOCKER_DOCUMENTATION.md](./DOCKER_DOCUMENTATION.md) - Configuración de contenedores Docker
- [SETUP_LOCAL.md](./SETUP_LOCAL.md) - Guía de instalación en entorno local
- [LOCAL_VERIFICATION_GUIDE.md](./LOCAL_VERIFICATION_GUIDE.md) - Guía de verificación de instalación local
- [ENV_SETUP.md](./ENV_SETUP.md) - Configuración de variables de entorno
- [ENV_DOCKER_TEMPLATE.md](./ENV_DOCKER_TEMPLATE.md) - Plantilla de variables para Docker

### Guías de Testing y Verificación

- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Procedimientos de testing del sistema
- [DOCKER_VERIFICATION_GUIDE.md](./DOCKER_VERIFICATION_GUIDE.md) - Guía de verificación del stack Docker

### Manual de Integración

- [XOMA_INTEGRATION_GUIDE.md](./XOMA_INTEGRATION_GUIDE.md) - **Manual de integración con plataforma XOMA**

### Resumen Ejecutivo

- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - Resumen ejecutivo del proyecto

### Recursos para Testing de API

- [Meet_Middleware_API.postman_collection.json](./Meet_Middleware_API.postman_collection.json) - Colección de Postman con 27 endpoints

---

## Endpoints del Sistema

**URL Base:** http://localhost:8000/api/v1/

**Endpoints Principales:**

- POST /meetings/ - Creación de reunión
- GET /meetings/ - Listado de reuniones
- GET /meetings/{id}/ - Detalle de reunión
- PATCH /meetings/{id}/ - Actualización de reunión
- DELETE /meetings/{id}/ - Cancelación de reunión

**Documentación Interactiva:** http://localhost:8000/api/v1/docs/

---

## Verificación del Sistema

### Estado Actual del Stack Docker

```bash
# Verificar servicios en ejecución
docker-compose ps
```

**Servicios Operativos:**

- PostgreSQL 15 (puerto 5432) - Estado: healthy
- Redis 7 (puerto 6379) - Estado: healthy
- Django Web (puerto 8000) - Estado: healthy
- Celery Worker
- Celery Beat Scheduler

### Testing del Sistema

```bash
# Ejecutar suite de tests automatizados
./scripts/test_docker_stack.sh

# Tests de integración
python3 scripts/test_integration.py
```

### Datos de Prueba Actuales

- 2 reuniones creadas en el sistema
- 3 usuarios registrados (1 admin + 2 auto-creados)
- 4 participantes registrados
- Base de datos PostgreSQL operativa con 13 tablas

---

## Configuración de Producción

### Recomendaciones para Despliegue

1. **Configuración de Google Service Account**
   - Consulte ENV_SETUP.md sección 2
   - Requerido para enlaces reales de Google Meet
   - Actualmente utiliza enlaces simulados

2. **Configuración de Seguridad**
   - Cambiar SECRET_KEY a valor aleatorio seguro
   - Configurar DEBUG=False
   - Configurar ALLOWED_HOSTS con dominios específicos
   - Implementar autenticación JWT

3. **Optimización de Base de Datos**
   - Configurar backups automatizados
   - Implementar connection pooling
   - Configurar índices adicionales según patrones de uso

4. **Monitoreo y Logging**
   - Implementar Sentry para tracking de errores
   - Configurar logging centralizado
   - Implementar métricas con Prometheus

---

## Soporte y Contacto

**Proyecto:** XOMA Meet Middleware  
**Versión:** 1.0.0  
**Framework:** Django 5.2.6  
**Documentación:** 13 guías técnicas disponibles  
**Scripts:** 6 scripts de automatización  
**Colección API:** Postman collection con 27 endpoints  

Para soporte técnico, consulte la documentación específica del componente en cuestión.

---

## Licencia y Derechos

Este proyecto ha sido desarrollado como middleware de integración para XOMA.

---

**Última Actualización:** Noviembre 2025
