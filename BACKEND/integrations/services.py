"""
Servicios de integración con Google Workspace.

Capa de servicio que usa los clientes de Google y maneja
la lógica de negocio de integración.
"""

import logging
from datetime import datetime, timedelta

from .google_client import GoogleCalendarClient, format_datetime_for_google
from .meet_client import GoogleMeetClient
from .config import validate_google_credentials
from core.exceptions import GoogleMeetCreationError, GoogleCalendarError, GoogleMeetError

logger = logging.getLogger(__name__)


class GoogleMeetService:
    """
    Servicio para gestionar reuniones de Google Meet.
    
    Proporciona métodos de alto nivel para:
    - Crear reuniones con Google Meet
    - Configurar grabación automática
    - Actualizar reuniones
    - Cancelar reuniones
    """
    
    def __init__(self):
        """Inicializa el servicio con los clientes de Calendar y Meet."""
        # Inicializar Calendar client solo si Google está configurado
        self.calendar_client = None
        try:
            if validate_google_credentials(raise_exception=False):
        self.calendar_client = GoogleCalendarClient()
            else:
                logger.warning("Google Calendar Client no disponible (credenciales no configuradas)")
        except Exception as e:
            logger.warning(f"No se pudo inicializar Google Calendar Client: {e}")
            self.calendar_client = None
        
        # Inicializar Meet client solo si Google está configurado
        try:
            if validate_google_credentials(raise_exception=False):
                self.meet_client = GoogleMeetClient()
            else:
                self.meet_client = None
                logger.warning("Google Meet Client no disponible (credenciales no configuradas)")
        except Exception as e:
            logger.warning(f"No se pudo inicializar Google Meet Client: {e}")
            self.meet_client = None
    
    def create_meeting_event(self, organizer_email, invited_emails,
                            scheduled_start=None, scheduled_end=None,
                            title=None, description=None, auto_record=False,
                            public_access=False):
        """
        Crea un evento de reunión con Google Meet.
        
        FLUJO: Si auto_record o public_access está habilitado:
        1. Crea el espacio directamente con Meet API primero (síncrono)
        2. Obtiene el meetingUri inmediatamente
        3. Inyecta el link de Meet en la descripción del evento
        4. Crea el evento en Calendar SIN conferenceData (el link está en la descripción)
        
        Si auto_record=False y public_access=False:
        - Usa el comportamiento original (crea evento con conferenceData)
        
        Args:
            organizer_email (str): Email del organizador
            invited_emails (list): Lista de emails de invitados
            scheduled_start (datetime, optional): Fecha/hora de inicio
            scheduled_end (datetime, optional): Fecha/hora de fin
            title (str, optional): Título personalizado del evento
            description (str, optional): Descripción del evento (se le agregará el link si aplica)
            auto_record (bool, optional): Si True, habilita grabación automática
            public_access (bool, optional): Si True, configura acceso público (OPEN)
        
        Returns:
            dict: Datos del evento creado
                - event_id: ID del evento en Google Calendar
                - meet_link: URL de Google Meet
                - html_link: Link al evento en Calendar
                - recording_enabled: True si la grabación se configuró exitosamente
                - space_name: Nombre del espacio creado (spaces/{meeting_code}) si aplica
        
        Raises:
            GoogleMeetCreationError: Si no se puede crear la reunión
        """
        try:
            # Convertir fechas de string ISO a datetime si es necesario
            if scheduled_start and isinstance(scheduled_start, str):
                try:
                    from django.utils.dateparse import parse_datetime
                    scheduled_start = parse_datetime(scheduled_start)
                except:
                    try:
                        scheduled_start = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
                    except:
                        pass
            
            if scheduled_end and isinstance(scheduled_end, str):
                try:
                    from django.utils.dateparse import parse_datetime
                    scheduled_end = parse_datetime(scheduled_end)
                except:
                    try:
                        scheduled_end = datetime.fromisoformat(scheduled_end.replace('Z', '+00:00'))
                    except:
                        pass
            
            # Generar título por defecto si no se proporciona
            if not title:
                if scheduled_start:
                    if isinstance(scheduled_start, datetime):
                    title = f"Reunión - {scheduled_start.strftime('%d/%m/%Y %H:%M')}"
                    else:
                        title = "Reunión de videollamada"
                else:
                    title = "Reunión de videollamada"
            
            # Si no hay fechas, usar fecha actual + 1 hora de duración
            if not scheduled_start:
                scheduled_start = datetime.now() + timedelta(hours=1)
            
            if not scheduled_end:
                scheduled_end = scheduled_start + timedelta(hours=1)
            
            # Construir lista de asistentes
            attendees = [{'email': email} for email in invited_emails]
            
            # NUEVO FLUJO: Crear espacio PRIMERO con acceso público y grabación automática
            # REQUISITO DE NEGOCIO: Todos los eventos con Calendar deben tener:
            # - Acceso público (public_access=True)
            # - Grabación automática (auto_record=True)
            # Esto permite inyectar el link en la descripción ANTES de crear el evento
            meeting_uri = None
            space_name = None
            recording_enabled = False
            use_description_with_link = False  # Flag para indicar si usar descripción con link
            
            # Para eventos con Calendar, SIEMPRE crear espacio con ambos habilitados
            if self.meet_client:
                try:
                    logger.info("Creando espacio directamente con Meet API (antes de crear evento)...")
                    logger.info("  Configuración: auto_record=True, public_access=True (requisito de negocio)")
                    space = self.meet_client.create_space(
                        auto_recording=True,  # SIEMPRE habilitado para eventos con Calendar
                        public_access=True   # SIEMPRE habilitado para eventos con Calendar
                    )
                    
                    meeting_uri = space.get('meetingUri')
                    space_name = space.get('name')
                    
                    if meeting_uri:
                        logger.info(f"Espacio creado exitosamente: {space_name}")
                        logger.info(f"Meeting URI: {meeting_uri}")
                        recording_enabled = True  # SIEMPRE habilitado para eventos con Calendar
                        use_description_with_link = True  # Usar descripción con link en lugar de conferenceData
                        
                        # Verificar configuración del espacio creado
                        config = space.get('config', {})
                        access_type = config.get('accessType', 'N/A')
                        artifact_config = config.get('artifactConfig', {})
                        recording_config = artifact_config.get('recordingConfig', {})
                        auto_recording = recording_config.get('autoRecordingGeneration', 'N/A')
                        
                        logger.info(f"  Verificación de configuración:")
                        logger.info(f"    - accessType: {access_type} (esperado: OPEN)")
                        logger.info(f"    - autoRecordingGeneration: {auto_recording} (esperado: ON)")
                        
                        if access_type != 'OPEN':
                            logger.warning(f"  ⚠️  PROBLEMA: accessType={access_type}, esperado OPEN")
                        if auto_recording != 'ON':
                            logger.warning(f"  ⚠️  PROBLEMA: autoRecordingGeneration={auto_recording}, esperado ON")
                    else:
                        logger.warning("Espacio creado pero no se obtuvo meetingUri")
                        
                except Exception as e:
                    logger.warning(f"Error al crear espacio directamente: {e}")
                    logger.warning("Continuando con creación de evento sin espacio pre-creado")
                    # Continuar sin espacio pre-creado (fallback al comportamiento original)
            
            # Construir descripción (con link si tenemos meeting_uri)
            if not description:
                description = (
                    f"Reunión organizada por {organizer_email}\n\n"
                    f"Participantes:\n" +
                    "\n".join([f"- {email}" for email in invited_emails])
                )
            
            # Inyectar link de Meet en la descripción si tenemos meeting_uri
            if meeting_uri and use_description_with_link:
                description += f"\n\n🔗 Unirse a la reunión: {meeting_uri}"
                logger.info(f"Link de Meet agregado a la descripción: {meeting_uri}")
            
            # Construir datos del evento para Google Calendar
            event_data = {
                'summary': title,
                'description': description,
                'start': format_datetime_for_google(scheduled_start),
                'end': format_datetime_for_google(scheduled_end),
                'attendees': attendees,
                'guestsCanModify': False,
                'guestsCanInviteOthers': False,
                'guestsCanSeeOtherGuests': True,
            }
            
            logger.info(f"Creando evento de Google Meet para: {organizer_email}")
            
            # Crear evento usando el cliente
            # Si use_description_with_link=True, crear sin conferenceData (el link está en la descripción)
            # Si use_description_with_link=False, usar comportamiento original (conferenceData)
            result = self.calendar_client.create_event(
                event_data, 
                existing_meet_uri=None if use_description_with_link else meeting_uri,
                use_description_only=use_description_with_link
            )
            
            logger.info(f"Evento creado exitosamente: {result['event_id']}")
            
            # Si usamos descripción con link, asegurar que meet_link esté en el resultado
            if use_description_with_link and meeting_uri:
                result['meet_link'] = meeting_uri
                logger.info(f"Meet link desde espacio pre-creado: {meeting_uri}")
            
            result['recording_enabled'] = recording_enabled
            if space_name:
                result['space_name'] = space_name
            
            return result
            
        except GoogleCalendarError as e:
            logger.error(f"Error de Google Calendar: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al crear reunión: {e}")
            raise GoogleMeetCreationError(
                f"Error al crear reunión de Google Meet: {str(e)}"
            )
    
    def create_meeting_space_only(self, auto_record=False, 
                                  invited_emails=None,
                                  organizer_email=None,
                                  public_access=False):
        """
        Crea solo un espacio de Meet con grabación automática.
        NO crea evento en Calendar.
        
        Puede configurar acceso público (cualquiera puede unirse) o agregar miembros específicos.
        
        Args:
            auto_record: Si True, habilita grabación automática
            invited_emails: Lista de emails que tendrán acceso directo (si public_access=False y v2beta disponible)
            organizer_email: Email del organizador (también se agrega como miembro si v2beta disponible)
            public_access: Si True, configura acceso público (OPEN) - cualquiera puede unirse sin solicitar permiso
        
        Returns:
            dict: {
                'meet_link': str,
                'space_name': str,
                'recording_enabled': bool,
                'members_added': int,  # Cantidad de miembros agregados exitosamente
                'public_access': bool  # Si el acceso es público
            }
        
        Raises:
            GoogleMeetError: Si hay error al crear el espacio o agregar miembros
        """
        try:
            if not self.meet_client:
                raise GoogleMeetError("Google Meet Client no está disponible")
            
            # 1. Crear espacio con grabación automática y configuración de acceso
            logger.info("Creando espacio de Meet sin Calendar...")
            logger.info(f"  Parámetros recibidos: auto_record={auto_record}, public_access={public_access}")
            space = self.meet_client.create_space(
                auto_recording=auto_record,
                public_access=public_access
            )
            
            # Verificar configuración del espacio creado
            config = space.get('config', {})
            access_type = config.get('accessType', 'N/A')
            logger.info(f"  Espacio creado con accessType: {access_type}")
            if access_type != 'OPEN' and public_access:
                logger.warning(f"  ⚠️  PROBLEMA: Se solicitó public_access=True pero el espacio tiene accessType={access_type}")
            
            meeting_uri = space.get('meetingUri')
            space_name = space.get('name')
            
            if not meeting_uri or not space_name:
                raise GoogleMeetError("No se pudo obtener meetingUri o space_name del espacio creado")
            
            logger.info(f"Espacio creado: {space_name}, URI: {meeting_uri}")
            
            # 2. Agregar miembros para acceso directo (solo si NO es acceso público y v2beta está disponible)
            members_added = 0
            
            if not public_access:
                # Solo agregar miembros si NO es acceso público
                all_emails = []
                
                # Agregar organizador si se proporciona
                if organizer_email:
                    all_emails.append(organizer_email)
                
                # Agregar invitados
                if invited_emails:
                    all_emails.extend(invited_emails)
                
                # Eliminar duplicados manteniendo orden
                seen = set()
                unique_emails = []
                for email in all_emails:
                    if email not in seen:
                        seen.add(email)
                        unique_emails.append(email)
                
                # Intentar agregar miembros solo si v2beta está disponible
                if self.meet_client.service_v2beta:
                    # Agregar cada miembro
                    for email in unique_emails:
                        try:
                            # Organizador como COHOST, otros como ATTENDEE
                            role = 'COHOST' if email == organizer_email else 'ATTENDEE'
                            self.meet_client.add_space_member(space_name, email, role)
                            members_added += 1
                            logger.info(f"Miembro agregado: {email} con rol {role}")
                        except Exception as e:
                            logger.warning(f"No se pudo agregar miembro {email}: {e}")
                            # Continuar con los demás miembros aunque uno falle
                    
                    logger.info(f"Espacio creado con {members_added} miembros agregados")
                else:
                    logger.warning(
                        "⚠️  API v2beta no está disponible. Los miembros NO se agregaron automáticamente. "
                        "Los usuarios pueden necesitar solicitar permiso para unirse. "
                        "Sugerencia: Usa public_access=True para permitir acceso público sin v2beta."
                    )
            else:
                logger.info("✅ Acceso público configurado (OPEN) - Cualquiera puede unirse sin solicitar permiso")
            
            return {
                'meet_link': meeting_uri,
                'space_name': space_name,
                'recording_enabled': auto_record,
                'members_added': members_added,
                'public_access': public_access
            }
            
        except GoogleMeetError:
            raise
        except Exception as e:
            logger.error(f"Error inesperado al crear espacio sin Calendar: {e}")
            raise GoogleMeetError(
                f"Error al crear espacio: {str(e)}"
            )
    
    def update_meeting_event(self, event_id, updates):
        """
        Actualiza un evento existente.
        
        Args:
            event_id (str): ID del evento a actualizar
            updates (dict): Campos a actualizar
        
        Returns:
            dict: Evento actualizado
        """
        try:
            return self.calendar_client.update_event(event_id, updates)
        except Exception as e:
            logger.error(f"Error al actualizar evento: {e}")
            raise GoogleCalendarError(f"Error al actualizar evento: {e}")
    
    def cancel_meeting_event(self, event_id):
        """
        Cancela un evento de reunión.
        
        Args:
            event_id (str): ID del evento a cancelar
        
        Returns:
            dict: Evento cancelado
        """
        try:
            return self.calendar_client.cancel_event(event_id)
        except Exception as e:
            logger.error(f"Error al cancelar evento: {e}")
            raise GoogleCalendarError(f"Error al cancelar evento: {e}")
    
    def delete_meeting_event(self, event_id):
        """
        Elimina completamente un evento.
        
        Args:
            event_id (str): ID del evento a eliminar
        
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            return self.calendar_client.delete_event(event_id)
        except Exception as e:
            logger.error(f"Error al eliminar evento: {e}")
            raise GoogleCalendarError(f"Error al eliminar evento: {e}")
    
    def get_meeting_event(self, event_id):
        """
        Obtiene los detalles de un evento.
        
        Args:
            event_id (str): ID del evento
        
        Returns:
            dict: Detalles del evento
        """
        try:
            return self.calendar_client.get_event(event_id)
        except Exception as e:
            logger.error(f"Error al obtener evento: {e}")
            raise GoogleCalendarError(f"Error al obtener evento: {e}")
