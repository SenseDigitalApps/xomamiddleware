"""
Cliente para integración con Google APIs.

Maneja:
- Autenticación con Service Account
- Creación de eventos en Google Calendar
- Configuración de Google Meet
- Gestión de eventos (actualizar, eliminar, consultar)
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import uuid
from datetime import datetime

from core.exceptions import (
    GoogleAuthenticationError,
    GoogleCalendarError,
    GoogleMeetCreationError,
    GoogleAPIQuotaExceeded
)
from .config import GoogleConfig

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """
    Cliente para interactuar con Google Calendar API.
    
    Proporciona métodos para:
    - Crear eventos con Google Meet
    - Actualizar eventos existentes
    - Eliminar eventos
    - Consultar eventos
    """
    
    def __init__(self):
        """
        Inicializa el cliente de Google Calendar.
        
        Carga credenciales y construye el servicio de Calendar API.
        
        Raises:
            GoogleAuthenticationError: Si falla la autenticación
        """
        try:
            self.config = GoogleConfig()
            self.credentials = self._load_credentials()
            self.service = self._build_service()
            logger.info("Google Calendar Client inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Google Calendar Client: {e}")
            raise GoogleAuthenticationError(
                f"No se pudo autenticar con Google: {str(e)}"
            )
    
    def _load_credentials(self):
        """
        Carga credenciales del Service Account desde archivo JSON.
        
        Returns:
            service_account.Credentials: Credenciales cargadas
        
        Raises:
            GoogleAuthenticationError: Si no se pueden cargar las credenciales
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.config.service_account_file,
                scopes=self.config.calendar_scopes
            )
            
            # Delegar dominio si está configurado
            # Esto permite que el Service Account actúe en nombre de un usuario
            if self.config.admin_email:
                credentials = credentials.with_subject(self.config.admin_email)
                logger.info(f"Credentials delegadas a: {self.config.admin_email}")
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error al cargar credenciales: {e}")
            raise GoogleAuthenticationError(
                f"No se pudieron cargar las credenciales: {str(e)}"
            )
    
    def _build_service(self):
        """
        Construye el servicio de Google Calendar API.
        
        Returns:
            Resource: Servicio de Calendar API v3
        """
        return build('calendar', 'v3', credentials=self.credentials)
    
    def create_event(self, event_data):
        """
        Crea un evento en Google Calendar con Google Meet.
        
        Args:
            event_data (dict): Datos del evento
                - summary (str): Título del evento
                - description (str, optional): Descripción
                - start (dict): {'dateTime': '2025-11-25T15:00:00Z', 'timeZone': 'America/Bogota'}
                - end (dict): {'dateTime': '2025-11-25T16:00:00Z', 'timeZone': 'America/Bogota'}
                - attendees (list, optional): [{'email': 'user@example.com'}, ...]
        
        Returns:
            dict: Datos del evento creado
                - event_id: ID del evento en Google Calendar
                - meet_link: URL de Google Meet (hangoutLink)
                - html_link: Link al evento en Calendar
                - status: Estado del evento
        
        Raises:
            GoogleMeetCreationError: Si no se puede crear el evento
            GoogleAPIQuotaExceeded: Si se excede la cuota de la API
        """
        try:
            # Agregar configuración de Google Meet (conferenceData)
            event_data['conferenceData'] = {
                'createRequest': {
                    'requestId': f"meet-{uuid.uuid4()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
            
            # Agregar reminders por defecto si no están configurados
            if 'reminders' not in event_data:
                event_data['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
                        {'method': 'popup', 'minutes': 30},  # 30 minutos antes
                    ],
                }
            
            logger.info(f"Creando evento en Google Calendar: {event_data.get('summary')}")
            
            # Crear evento
            event = self.service.events().insert(
                calendarId=self.config.calendar_id,
                body=event_data,
                conferenceDataVersion=1,  # Necesario para Google Meet
                sendUpdates='all'  # Enviar invitaciones por email
            ).execute()
            
            # Extraer datos relevantes
            result = {
                'event_id': event['id'],
                'meet_link': event.get('hangoutLink', ''),
                'html_link': event.get('htmlLink', ''),
                'status': event.get('status', 'confirmed'),
                'created': event.get('created', ''),
                'updated': event.get('updated', '')
            }
            
            logger.info(f"Evento creado exitosamente: {result['event_id']}")
            logger.info(f"Google Meet link: {result['meet_link']}")
            
            return result
            
        except HttpError as error:
            # Manejar diferentes tipos de errores HTTP
            if error.resp.status == 403:
                logger.error("Cuota de API excedida o permisos insuficientes")
                raise GoogleAPIQuotaExceeded(
                    "Cuota de Google Calendar API excedida. Intente más tarde."
                )
            elif error.resp.status == 401:
                logger.error("Error de autenticación")
                raise GoogleAuthenticationError(
                    "Credenciales de Google inválidas o expiradas"
                )
            else:
                logger.error(f"Error HTTP al crear evento: {error}")
                raise GoogleMeetCreationError(
                    f"Error al crear evento en Google Calendar: {error}"
                )
        
        except Exception as e:
            logger.error(f"Error inesperado al crear evento: {e}")
            raise GoogleMeetCreationError(
                f"Error inesperado al crear reunión: {str(e)}"
            )
    
    def get_event(self, event_id):
        """
        Obtiene los detalles de un evento existente.
        
        Args:
            event_id (str): ID del evento en Google Calendar
        
        Returns:
            dict: Datos del evento
        
        Raises:
            GoogleCalendarError: Si no se puede obtener el evento
        """
        try:
            event = self.service.events().get(
                calendarId=self.config.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Evento obtenido: {event_id}")
            return event
            
        except HttpError as error:
            if error.resp.status == 404:
                logger.error(f"Evento no encontrado: {event_id}")
                raise GoogleCalendarError(f"Evento no encontrado: {event_id}")
            else:
                logger.error(f"Error al obtener evento: {error}")
                raise GoogleCalendarError(f"Error al obtener evento: {error}")
    
    def update_event(self, event_id, updates):
        """
        Actualiza un evento existente.
        
        Args:
            event_id (str): ID del evento a actualizar
            updates (dict): Campos a actualizar
        
        Returns:
            dict: Evento actualizado
        
        Raises:
            GoogleCalendarError: Si no se puede actualizar el evento
        """
        try:
            # Primero obtener el evento actual
            event = self.get_event(event_id)
            
            # Aplicar actualizaciones
            event.update(updates)
            
            # Actualizar en Google Calendar
            updated_event = self.service.events().update(
                calendarId=self.config.calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Evento actualizado: {event_id}")
            return updated_event
            
        except HttpError as error:
            logger.error(f"Error al actualizar evento: {error}")
            raise GoogleCalendarError(f"Error al actualizar evento: {error}")
    
    def delete_event(self, event_id):
        """
        Elimina un evento de Google Calendar.
        
        Args:
            event_id (str): ID del evento a eliminar
        
        Returns:
            bool: True si se eliminó correctamente
        
        Raises:
            GoogleCalendarError: Si no se puede eliminar el evento
        """
        try:
            self.service.events().delete(
                calendarId=self.config.calendar_id,
                eventId=event_id,
                sendUpdates='all'  # Notificar a participantes
            ).execute()
            
            logger.info(f"Evento eliminado: {event_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Error al eliminar evento: {error}")
            raise GoogleCalendarError(f"Error al eliminar evento: {error}")
    
    def cancel_event(self, event_id):
        """
        Cancela un evento (cambia status a 'cancelled').
        
        Args:
            event_id (str): ID del evento a cancelar
        
        Returns:
            dict: Evento cancelado
        
        Raises:
            GoogleCalendarError: Si no se puede cancelar el evento
        """
        try:
            return self.update_event(event_id, {'status': 'cancelled'})
        except Exception as e:
            logger.error(f"Error al cancelar evento: {e}")
            raise GoogleCalendarError(f"Error al cancelar evento: {e}")


def format_datetime_for_google(dt, timezone='America/Bogota'):
    """
    Formatea un datetime para Google Calendar API.
    
    Args:
        dt (datetime): Datetime a formatear
        timezone (str): Zona horaria
    
    Returns:
        dict: {'dateTime': '...', 'timeZone': '...'}
    """
    if dt is None:
        return None
    
    # Asegurar que sea string en formato ISO 8601
    if isinstance(dt, datetime):
        dt_str = dt.isoformat()
    else:
        dt_str = str(dt)
    
    return {
        'dateTime': dt_str,
        'timeZone': timezone
    }
