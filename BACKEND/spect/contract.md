# OBJETIVO

Desarrollar un **middleware de integración entre el backend de XOMA (Oracle)** y Google Meet, que permita **crear reuniones de forma programática, invitar automáticamente a los participantes definidos en el body del endpoint, y activar la grabación automática sin excepción**. Esto garantiza trazabilidad, control de cumplimiento y almacenamiento de todas las sesiones de videollamada.

---

## Tecnologías Recomendadas

- **Backend del Middleware**: Node.js o Python (con SDK oficial de Google APIs)
- **API de Integración**: Google Calendar API + Google Meet API + Google Drive API (para almacenamiento de grabaciones)
- **Autenticación**: OAuth 2.0 con credenciales de servicio de Google Workspace
- **Infraestructura**: AWS (EC2 para el middleware, S3 opcional como backup de grabaciones exportadas desde Google Drive)
- **Base de datos**: PostgreSQL (para logs de sesiones y metadatos de llamadas)
- **Monitoreo**: CloudWatch para disponibilidad y consumo de recursos

---

## Flujo General del Sistema

1. **Creación de reunión**:
    
    El backend de XOMA (Oracle) envía al middleware un request con los usuarios que deben ser invitados.
    
2. **Generación del Meet**:
    
    El middleware crea la reunión en Google Calendar con link a Google Meet, añade a los usuarios como invitados y habilita automáticamente la grabación.
    
3. **Inicio de la grabación automática**:
    
    Con plan Google Workspace Enterprise Standard o superior, se fuerza la política de grabación automática mediante la API de configuración y políticas organizacionales.
    
4. **Notificación a participantes**:
    
    Los usuarios reciben invitación inmediata en sus calendarios y correo electrónico.
    
5. **Finalización y almacenamiento**:
    
    Al terminar la reunión, la grabación se guarda en Google Drive de forma automática. Opcionalmente, se puede configurar una exportación a S3 para almacenamiento redundante.
    
6. **Logs y estadísticas**:
    
    El middleware registra fecha, duración, usuarios invitados y link de grabación.
    

---

## Historias de Usuario

### Épica 1 – Integración y Gestión de Videollamadas

- **HU01**: Como backend de XOMA, quiero poder enviar la solicitud de videollamada entre usuarios para que el middleware cree automáticamente un Google Meet con grabación habilitada.
- **HU02**: Como usuario, quiero recibir en mi correo y calendario el enlace al Google Meet para unirme de forma inmediata.
- **HU03**: Como administrador, quiero que todas las reuniones se graben sin excepción, para asegurar trazabilidad y cumplimiento.
- **HU04**: Como administrador, quiero acceder a las grabaciones almacenadas en Google Drive (o S3 si se activa la exportación) para auditar las reuniones.

---

## Entregables

- Middleware en Node.js/Python con endpoints REST para creación de videollamadas.
- Integración con Google Meet + Calendar + Drive.
- Configuración de grabación automática (requiere Workspace Enterprise).
- Base de datos para logs de sesiones.
- Documentación técnica y funcional.
- Soporte para despliegue en AWS.

---

<aside>
⚠️

## Limitaciones Técnicas y Requisitos de Licenciamiento

- **Google Workspace Enterprise**: La grabación automática de reuniones de Google Meet solo está disponible en planes **Enterprise Standard, Enterprise Plus, Education Plus o Teaching and Learning Upgrade**.
- **Limitación API**: La API de Google no permite “forzar” la grabación en cuentas individuales de usuario. La grabación se gestiona a nivel de políticas de la organización (admin console). En caso de nos ser permitido este flujo por parte de meer, se deberá incluir un tercer componente que ingrese a la reunión, grabe la sesión y después exporte el video.
- **Espacio de Almacenamiento**: Las grabaciones se guardan en Google Drive. Se debe contar con capacidad suficiente en la organización o habilitar una política de exportación (ejemplo: a AWS S3).
- **Usuarios invitados externos**: Podrán unirse a la reunión, pero la grabación queda ligada a la organización que crea la reunión.
- **Costo adicional**: El licenciamiento de Google Workspace Enterprise es necesario y no está incluido en esta cotización.
</aside>

## Valor y tiempos

- **Valor de la inversión:** $43’200.000
(valor no incluye licenciamiento de Google Workspace Enterprise, ni costos de infraestructura AWS)
- **Tiempos de desarrollo:** 3 meses

![Colmedicos.jpg](attachment:a8eca4b2-59d8-4d74-8240-649561c9744f:Colmedicos.jpg)