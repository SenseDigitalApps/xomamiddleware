# Documentación de Modelos de Base de Datos - Meet Middleware

## Resumen

Este documento describe la estructura de los modelos de datos implementados en el middleware de Google Meet, incluyendo especificaciones de campos, relaciones y restricciones de base de datos.

---

## Aplicación: accounts

### Modelo: User

**Descripción:** Modelo personalizado de usuario que extiende AbstractUser de Django, incorporando funcionalidad adicional para roles de usuario.

**Campos del Modelo:**

| Campo | Tipo de Dato | Descripción | Requerido |
|-------|--------------|-------------|-----------|
| username | CharField | Nombre de usuario único (heredado) | Sí |
| email | EmailField | Correo electrónico (heredado) | Sí |
| first_name | CharField | Nombre del usuario (heredado) | No |
| last_name | CharField | Apellido del usuario (heredado) | No |
| password | CharField | Contraseña hasheada (heredado) | Sí |
| role | CharField | Rol del usuario en el sistema | Sí |
| is_active | BooleanField | Indica si el usuario está activo (heredado) | Sí |
| is_staff | BooleanField | Indica acceso al panel de administración (heredado) | Sí |
| date_joined | DateTimeField | Fecha de registro del usuario (heredado) | Sí |

**Opciones para el Campo role:**

- `admin` - Administrador del sistema
- `service` - Usuario de servicio/API
- `external` - Usuario externo (valor por defecto)

**Relaciones:**

- `organized_meetings` - Relación inversa a reuniones organizadas por el usuario (ForeignKey reverso)

---

## Aplicación: meetings

### Modelo: Meeting

**Descripción:** Representa una reunión de Google Meet con todos sus metadatos asociados.

**Campos del Modelo:**

| Campo | Tipo de Dato | Descripción | Requerido |
|-------|--------------|-------------|-----------|
| id | AutoField | Identificador único de la reunión | Sí (auto) |
| google_event_id | CharField(255) | ID del evento en Google Calendar (único) | Sí |
| meet_link | URLField | URL de acceso a Google Meet | Sí |
| organizer | ForeignKey(User) | Usuario organizador de la reunión | Sí |
| invited_emails | JSONField | Lista de correos invitados | Sí (default=[]) |
| scheduled_start | DateTimeField | Fecha y hora de inicio programada | No |
| scheduled_end | DateTimeField | Fecha y hora de fin programada | No |
| status | CharField(20) | Estado actual de la reunión | Sí (default='CREATED') |
| created_at | DateTimeField | Timestamp de creación | Sí (auto) |
| updated_at | DateTimeField | Timestamp de última actualización | Sí (auto) |

**Opciones para el Campo status:**

- `CREATED` - Reunión creada
- `SCHEDULED` - Reunión programada
- `FINISHED` - Reunión finalizada
- `CANCELLED` - Reunión cancelada

**Relaciones del Modelo:**

- `organizer` - ForeignKey a User con política PROTECT
- `participants` - Relación inversa a participantes de la reunión
- `recording` - Relación inversa uno-a-uno con grabación

**Índices de Base de Datos:**

- Índice único en `google_event_id`
- Índice en `status`
- Índice descendente en `created_at`

---

### Modelo: MeetingRecording

**Descripción:** Representa los metadatos de una grabación de reunión almacenada en Google Drive.

**Campos del Modelo:**

| Campo | Tipo de Dato | Descripción | Requerido |
|-------|--------------|-------------|-----------|
| id | AutoField | Identificador único de la grabación | Sí (auto) |
| meeting | OneToOneField(Meeting) | Reunión asociada | Sí |
| drive_file_id | CharField(255) | ID del archivo en Google Drive | No |
| drive_file_url | URLField | URL de acceso al archivo en Drive | No |
| duration_seconds | PositiveIntegerField | Duración en segundos | No |
| available_at | DateTimeField | Fecha de disponibilidad | No |
| created_at | DateTimeField | Timestamp de registro | Sí (auto) |

**Relaciones del Modelo:**

- `meeting` - OneToOneField a Meeting con política CASCADE

**Métodos del Modelo:**

- `duration_formatted()` - Retorna duración en formato HH:MM:SS

---

### Modelo: Participant

**Descripción:** Representa un participante en una reunión específica.

**Campos del Modelo:**

| Campo | Tipo de Dato | Descripción | Requerido |
|-------|--------------|-------------|-----------|
| id | AutoField | Identificador único del participante | Sí (auto) |
| meeting | ForeignKey(Meeting) | Reunión asociada | Sí |
| email | EmailField | Correo electrónico del participante | Sí |
| role | CharField(20) | Rol del participante en la reunión | Sí (default='guest') |
| created_at | DateTimeField | Timestamp de registro | Sí (auto) |

**Opciones para el Campo role:**

- `organizer` - Organizador de la reunión
- `guest` - Invitado (valor por defecto)

**Relaciones del Modelo:**

- `meeting` - ForeignKey a Meeting con política CASCADE

**Restricciones de Integridad:**

- `unique_together`: (`meeting`, `email`) - Un correo electrónico no puede duplicarse en la misma reunión

**Índices de Base de Datos:**

- Índice en `email`
- Índice compuesto en (`meeting`, `email`)

---

## Diagrama de Relaciones

```
User (accounts)
  └── [1:N] Meeting (meetings)
                ├── [1:1] MeetingRecording (meetings)
                └── [1:N] Participant (meetings)
```

**Interpretación:**
- Un usuario puede organizar múltiples reuniones
- Cada reunión tiene un organizador
- Cada reunión puede tener una grabación (relación 1:1)
- Cada reunión puede tener múltiples participantes

---

## Estadísticas del Modelo de Datos

- **Total de modelos implementados:** 4
- **Total de campos personalizados:** 21
- **Total de relaciones:** 3
- **Líneas de código (modelos):** 259
- **Líneas de código (configuración admin):** 305
- **Total de código:** 564 líneas

---

## Procedimiento de Aplicación de Modelos

### Creación de Migraciones

```bash
python manage.py makemigrations
```

### Aplicación de Migraciones

```bash
python manage.py migrate
```

### Creación de Superusuario

```bash
python manage.py createsuperuser
```

### Acceso al Panel de Administración

```
http://localhost:8000/admin/
```

---

## Notas Técnicas

- Todos los modelos incluyen timestamps automáticos (created_at, updated_at donde aplica)
- Las relaciones ForeignKey utilizan nombres descriptivos en related_name
- Los índices están optimizados para consultas frecuentes
- Las restricciones de integridad aseguran consistencia de datos
- Los campos verbose_name están configurados para el panel de administración
