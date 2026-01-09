"""
Configuración centralizada para integración con Google Workspace.

Define scopes, configuración de APIs y validaciones de credenciales.
"""

from django.conf import settings
from core.exceptions import MissingCredentialsError, InvalidConfigurationError
import os


# Scopes de Google API necesarios
GOOGLE_CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]

GOOGLE_DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
]

GOOGLE_MEET_SCOPES = [
    'https://www.googleapis.com/auth/meetings.space.created',
    'https://www.googleapis.com/auth/meetings.space.readonly',
    'https://www.googleapis.com/auth/meetings.space.settings',  
]

# Todos los scopes combinados
ALL_SCOPES = GOOGLE_CALENDAR_SCOPES + GOOGLE_DRIVE_SCOPES + GOOGLE_MEET_SCOPES


def validate_google_credentials(raise_exception=True):
    """
    Valida que las credenciales de Google estén configuradas correctamente.
    
    Verifica:
    - Que exista el archivo de credenciales
    - Que las variables de entorno estén configuradas
    
    Args:
        raise_exception (bool): Si True, lanza excepción en caso de error.
                               Si False, retorna False en caso de error.
    
    Raises:
        MissingCredentialsError: Si faltan credenciales y raise_exception=True
        InvalidConfigurationError: Si la configuración es inválida y raise_exception=True
    
    Returns:
        bool: True si las credenciales son válidas, False si no (cuando raise_exception=False)
    """
    # Verificar que exista la ruta al archivo de credenciales
    service_account_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE
    
    if not service_account_file:
        if raise_exception:
            raise MissingCredentialsError(
                "Variable GOOGLE_SERVICE_ACCOUNT_FILE no está configurada. "
                "Ver ENV_SETUP.md para instrucciones."
            )
        return False
    
    # Verificar que el archivo exista
    if not os.path.exists(service_account_file):
        if raise_exception:
            raise InvalidConfigurationError(
                f"Archivo de credenciales no encontrado: {service_account_file}. "
                "Asegúrese de haber descargado la clave JSON del Service Account."
            )
        return False
    
    # Verificar que el archivo sea legible
    if not os.access(service_account_file, os.R_OK):
        if raise_exception:
            raise InvalidConfigurationError(
                f"No se puede leer el archivo de credenciales: {service_account_file}. "
                "Verifique los permisos del archivo."
            )
        return False
    
    return True


def get_google_config():
    """
    Retorna la configuración de Google desde settings.
    
    Returns:
        dict: Configuración de Google
    """
    return {
        'service_account_file': settings.GOOGLE_SERVICE_ACCOUNT_FILE,
        'admin_email': settings.GOOGLE_WORKSPACE_ADMIN_EMAIL,
        'calendar_id': settings.GOOGLE_CALENDAR_ID or 'primary',
        'scopes': ALL_SCOPES,
    }


class GoogleConfig:
    """
    Clase de configuración para Google APIs.
    
    Proporciona acceso centralizado a configuración y validación.
    """
    
    def __init__(self):
        """Inicializa y valida la configuración."""
        self._validate()
    
    def _validate(self):
        """Valida la configuración al inicializar."""
        validate_google_credentials()
    
    @property
    def service_account_file(self):
        """Ruta al archivo de credenciales del Service Account."""
        return settings.GOOGLE_SERVICE_ACCOUNT_FILE
    
    @property
    def admin_email(self):
        """Email del administrador de Workspace (para delegation)."""
        return settings.GOOGLE_WORKSPACE_ADMIN_EMAIL
    
    @property
    def calendar_id(self):
        """ID del calendario a usar (por defecto 'primary')."""
        return settings.GOOGLE_CALENDAR_ID or 'primary'
    
    @property
    def calendar_scopes(self):
        """Scopes necesarios para Google Calendar."""
        return GOOGLE_CALENDAR_SCOPES
    
    @property
    def drive_scopes(self):
        """Scopes necesarios para Google Drive."""
        return GOOGLE_DRIVE_SCOPES
    
    @property
    def meet_scopes(self):
        """Scopes necesarios para Google Meet."""
        return GOOGLE_MEET_SCOPES
    
    @property
    def all_scopes(self):
        """Todos los scopes necesarios."""
        return ALL_SCOPES

