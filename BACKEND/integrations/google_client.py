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
        
        Usa from_service_account_info en lugar de from_service_account_file
        para evitar problemas de deadlock en macOS con Docker.
        
        Returns:
            service_account.Credentials: Credenciales cargadas
        
        Raises:
            GoogleAuthenticationError: Si no se pueden cargar las credenciales
        """
        try:
            # Leer el archivo en memoria primero para evitar deadlock en macOS/Docker
            # Estrategia: Leer todo el contenido de una vez en binario, luego parsear
            import json
            import time
            
            # Intentar leer con retry para manejar problemas temporales de macOS/Docker
            max_retries = 5
            retry_delay = 0.3
            
            creds_info = None
            for attempt in range(max_retries):
                try:
                    # Leer el archivo completo en binario de una vez (evita múltiples reads)
                    # Esto reduce la posibilidad de deadlock en macOS con Docker
                    with open(self.config.service_account_file, 'rb') as f:
                        # Leer todo el contenido de una vez
                        content = f.read()
                    
                    # Parsear JSON desde el contenido en memoria (no desde el file handle)
                    creds_info = json.loads(content.decode('utf-8'))
                    break
                    
                except (OSError, IOError) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Intento {attempt + 1}/{max_retries} falló al leer credenciales: {e}, esperando {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # Exponential backoff
                    else:
                        logger.error(f"Todos los intentos fallaron al leer credenciales")
                        raise
                except json.JSONDecodeError as e:
                    logger.error(f"Error al parsear JSON de credenciales: {e}")
                    raise GoogleAuthenticationError(f"El archivo de credenciales no es un JSON válido: {str(e)}")
            
            if creds_info is None:
                raise GoogleAuthenticationError("No se pudo leer el archivo de credenciales después de múltiples intentos")
            
            # Usar from_service_account_info en lugar de from_service_account_file
            credentials = service_account.Credentials.from_service_account_info(
                creds_info,
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
    
    def _get_service_account_email(self):
        """
        Obtiene el email del Service Account desde el archivo de credenciales.
        
        Returns:
            str: Email del Service Account
        """
        try:
            import json
            with open(self.config.service_account_file, 'r') as f:
                creds = json.load(f)
                return creds.get('client_email', 'N/A')
        except Exception:
            return 'N/A'
    
    def create_event(self, event_data, existing_meet_uri=None, use_description_only=False):
        """
        Crea un evento en Google Calendar con Google Meet.
        
        Args:
            event_data (dict): Datos del evento
                - summary (str): Título del evento
                - description (str, optional): Descripción (puede incluir link de Meet)
                - start (dict): {'dateTime': '2025-11-25T15:00:00Z', 'timeZone': 'America/Bogota'}
                - end (dict): {'dateTime': '2025-11-25T16:00:00Z', 'timeZone': 'America/Bogota'}
                - attendees (list, optional): [{'email': 'user@example.com'}, ...]
            existing_meet_uri (str, optional): URI de Meet existente (ej: https://meet.google.com/abc-defg-hij)
                Si se proporciona, usa este espacio en lugar de crear uno nuevo
            use_description_only (bool, optional): Si True, NO incluye conferenceData.
                El link de Meet debe estar en la descripción. Útil cuando se crea el espacio
                con Meet API primero y se quiere evitar problemas de asociación.
        
        Returns:
            dict: Datos del evento creado
                - event_id: ID del evento en Google Calendar
                - meet_link: URL de Google Meet (hangoutLink o del existing_meet_uri)
                - html_link: Link al evento en Calendar
                - status: Estado del evento
        
        Raises:
            GoogleMeetCreationError: Si no se puede crear el evento
            GoogleAPIQuotaExceeded: Si se excede la cuota de la API
        """
        try:
            # Si use_description_only=True, NO incluir conferenceData (el link está en la descripción)
            if use_description_only:
                logger.info("Creando evento sin conferenceData (link en descripción)")
                # No agregar conferenceData, el link ya está en la descripción
                meet_link_from_description = existing_meet_uri  # Usar el URI que se pasó
            elif existing_meet_uri:
                # Usar espacio existente creado con Meet API (comportamiento anterior)
                logger.info(f"Usando espacio existente: {existing_meet_uri}")
                # Intentar asociar el meetingUri existente directamente
                event_data['conferenceData'] = {
                    'meetingUri': existing_meet_uri,
                    'entryPoints': [
                        {
                            'entryPointType': 'video',
                            'uri': existing_meet_uri,
                            'label': 'meet.google.com'
                        }
                    ]
                }
                meet_link_from_description = None
            else:
                # Crear nuevo espacio (comportamiento original)
                event_data['conferenceData'] = {
                    'createRequest': {
                        'requestId': f"meet-{uuid.uuid4()}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
                meet_link_from_description = None
            
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
            # Si use_description_only=True, NO incluir conferenceDataVersion
            insert_params = {
                'calendarId': self.config.calendar_id,
                'body': event_data,
                'sendUpdates': 'all'  # Enviar invitaciones por email
            }
            
            # Solo incluir conferenceDataVersion si hay conferenceData
            if 'conferenceData' in event_data:
                insert_params['conferenceDataVersion'] = 1  # Necesario para Google Meet
            
            event = self.service.events().insert(**insert_params).execute()
            
            # Extraer datos relevantes
            meet_link = event.get('hangoutLink', '')
            if not meet_link:
                # Intentar obtener de conferenceData.entryPoints
                conference_data = event.get('conferenceData', {})
                entry_points = conference_data.get('entryPoints', [])
                if entry_points:
                    # El primer entryPoint suele ser el de Meet
                    meet_link = entry_points[0].get('uri', '')
                # Si aún no hay, usar el meetingUri que pasamos (si existe)
                if not meet_link and meet_link_from_description:
                    meet_link = meet_link_from_description
                    logger.info(f"Usando meetingUri proporcionado como meet_link: {meet_link}")
                elif not meet_link and existing_meet_uri:
                    meet_link = existing_meet_uri
                    logger.info(f"Usando meetingUri proporcionado como meet_link: {meet_link}")
            
            result = {
                'event_id': event['id'],
                'meet_link': meet_link,
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
                error_str = str(error)
                error_content = error.content.decode('utf-8') if error.content else ''
                error_reason = ''
                error_message = ''
                
                # Intentar extraer el reason y message del error
                # error_details es una lista: [{'domain': '...', 'reason': '...', 'message': '...'}]
                try:
                    if error.error_details:
                        # error_details puede ser una lista de diccionarios o una lista de listas
                        details = error.error_details
                        if isinstance(details, list) and len(details) > 0:
                            first = details[0]
                            # Si el primer elemento es un diccionario, extraer directamente
                            if isinstance(first, dict):
                                error_reason = first.get('reason', '')
                                error_message = first.get('message', '')
                            # Si el primer elemento es una lista, tomar el primer elemento de esa lista
                            elif isinstance(first, list) and len(first) > 0:
                                if isinstance(first[0], dict):
                                    error_reason = first[0].get('reason', '')
                                    error_message = first[0].get('message', '')
                except Exception as e:
                    logger.warning(f"Error al extraer detalles del error: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                
                # Verificar si es un error de permisos
                # Priorizar error_reason y error_message que vienen de error_details
                is_permission_error = False
                
                # Verificar primero en error_reason (más confiable)
                if error_reason and ('requiredAccessLevel' in error_reason or 'writer' in error_reason.lower()):
                    is_permission_error = True
                # Luego en error_message
                elif error_message and 'writer access' in error_message.lower():
                    is_permission_error = True
                # Finalmente en error_str y error_content como fallback
                else:
                    is_permission_error = (
                        'requiredAccessLevel' in error_str or 
                        'writer access' in error_str.lower() or
                        'requiredAccessLevel' in error_content or
                        'writer access' in error_content.lower()
                    )
                
                if is_permission_error:
                    logger.error("Permisos insuficientes en el calendario")
                    sa_email = self._get_service_account_email()
                    admin_email = self.config.admin_email
                    
                    if admin_email:
                        # Con Domain-Wide Delegation, el error puede ser del usuario delegado
                        error_msg = (
                            f"El usuario '{admin_email}' (delegado por el Service Account) "
                            f"no tiene permisos de escritura en el calendario.\n"
                            f"Service Account: {sa_email}\n"
                            f"Calendar ID: {self.config.calendar_id}\n\n"
                            f"SOLUCIÓN:\n"
                            f"1. Ve a Google Calendar → Settings and sharing del calendario\n"
                            f"2. 'Share with specific people' → Agrega '{admin_email}'\n"
                            f"3. Con permisos 'Make changes to events' (Writer)\n"
                            f"4. O usa el calendario 'primary' del usuario '{admin_email}'"
                        )
                    else:
                        # Sin Domain-Wide Delegation, el error es del Service Account
                        error_msg = (
                            f"El Service Account no tiene permisos de escritura en el calendario.\n"
                            f"Service Account: {sa_email}\n"
                            f"Calendar ID: {self.config.calendar_id}\n\n"
                            f"SOLUCIÓN:\n"
                            f"1. Ve a Google Calendar → Settings and sharing del calendario\n"
                            f"2. 'Share with specific people' → Agrega '{sa_email}'\n"
                            f"3. Con permisos 'Make changes to events' (Writer)"
                        )
                    
                    raise GoogleCalendarError(error_msg)
                else:
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
