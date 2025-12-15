"""
Excepciones personalizadas del proyecto.

Define excepciones específicas para diferentes componentes:
- Google APIs
- Validación de negocio
- Errores de integración
"""


class MeetMiddlewareException(Exception):
    """Excepción base para todas las excepciones del middleware."""
    pass


# ===== Excepciones de Google API =====

class GoogleAPIError(MeetMiddlewareException):
    """Error base para errores de Google API."""
    pass


class GoogleAuthenticationError(GoogleAPIError):
    """Error de autenticación con Google."""
    def __init__(self, message="Error de autenticación con Google Workspace"):
        self.message = message
        super().__init__(self.message)


class GoogleCalendarError(GoogleAPIError):
    """Error al interactuar con Google Calendar."""
    def __init__(self, message="Error al interactuar con Google Calendar"):
        self.message = message
        super().__init__(self.message)


class GoogleMeetCreationError(GoogleAPIError):
    """Error al crear Google Meet."""
    def __init__(self, message="Error al crear reunión de Google Meet"):
        self.message = message
        super().__init__(self.message)


class GoogleDriveError(GoogleAPIError):
    """Error al interactuar con Google Drive."""
    def __init__(self, message="Error al interactuar con Google Drive"):
        self.message = message
        super().__init__(self.message)


class GoogleAPIQuotaExceeded(GoogleAPIError):
    """Error cuando se excede la cuota de Google API."""
    def __init__(self, message="Cuota de Google API excedida"):
        self.message = message
        super().__init__(self.message)


# ===== Excepciones de Validación de Negocio =====

class BusinessValidationError(MeetMiddlewareException):
    """Error de validación de reglas de negocio."""
    pass


class InvalidMeetingDataError(BusinessValidationError):
    """Datos inválidos para crear una reunión."""
    def __init__(self, message="Datos de reunión inválidos"):
        self.message = message
        super().__init__(self.message)


class MeetingNotFoundError(BusinessValidationError):
    """Reunión no encontrada."""
    def __init__(self, meeting_id):
        self.message = f"Reunión con ID {meeting_id} no encontrada"
        super().__init__(self.message)


class ParticipantError(BusinessValidationError):
    """Error relacionado con participantes."""
    def __init__(self, message="Error con participantes de la reunión"):
        self.message = message
        super().__init__(self.message)


# ===== Excepciones de Configuración =====

class ConfigurationError(MeetMiddlewareException):
    """Error de configuración del sistema."""
    pass


class MissingCredentialsError(ConfigurationError):
    """Credenciales de Google no configuradas."""
    def __init__(self, message="Credenciales de Google no configuradas correctamente"):
        self.message = message
        super().__init__(self.message)


class InvalidConfigurationError(ConfigurationError):
    """Configuración inválida."""
    def __init__(self, message="Configuración del sistema inválida"):
        self.message = message
        super().__init__(self.message)
