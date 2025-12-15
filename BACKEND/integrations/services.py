"""
Servicios de integración con Google Workspace.

Capa de servicio que usa los clientes de Google y maneja
la lógica de negocio de integración.
"""

import logging
from datetime import datetime, timedelta

from .google_client import GoogleCalendarClient, format_datetime_for_google
from core.exceptions import GoogleMeetCreationError, GoogleCalendarError

logger = logging.getLogger(__name__)


class GoogleMeetService:
    """
    Servicio para gestionar reuniones de Google Meet.
    
    Proporciona métodos de alto nivel para:
    - Crear reuniones con Google Meet
    - Actualizar reuniones
    - Cancelar reuniones
    """
    
    def __init__(self):
        """Inicializa el servicio con el cliente de Calendar."""
        self.calendar_client = GoogleCalendarClient()
    
    def create_meeting_event(self, organizer_email, invited_emails,
                            scheduled_start=None, scheduled_end=None,
                            title=None, description=None):
        """
        Crea un evento de reunión con Google Meet.
        
        Args:
            organizer_email (str): Email del organizador
            invited_emails (list): Lista de emails de invitados
            scheduled_start (datetime, optional): Fecha/hora de inicio
            scheduled_end (datetime, optional): Fecha/hora de fin
            title (str, optional): Título personalizado del evento
            description (str, optional): Descripción del evento
        
        Returns:
            dict: Datos del evento creado
                - event_id: ID del evento en Google Calendar
                - meet_link: URL de Google Meet
                - html_link: Link al evento en Calendar
        
        Raises:
            GoogleMeetCreationError: Si no se puede crear la reunión
        """
        try:
            # Generar título por defecto si no se proporciona
            if not title:
                if scheduled_start:
                    title = f"Reunión - {scheduled_start.strftime('%d/%m/%Y %H:%M')}"
                else:
                    title = "Reunión de videollamada"
            
            # Generar descripción por defecto
            if not description:
                description = (
                    f"Reunión organizada por {organizer_email}\n\n"
                    f"Participantes:\n" +
                    "\n".join([f"- {email}" for email in invited_emails])
                )
            
            # Si no hay fechas, usar fecha actual + 1 hora de duración
            if not scheduled_start:
                scheduled_start = datetime.now() + timedelta(hours=1)
            
            if not scheduled_end:
                scheduled_end = scheduled_start + timedelta(hours=1)
            
            # Construir lista de asistentes
            attendees = [{'email': email} for email in invited_emails]
            
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
            result = self.calendar_client.create_event(event_data)
            
            logger.info(f"Evento creado exitosamente: {result['event_id']}")
            
            return result
            
        except GoogleCalendarError as e:
            logger.error(f"Error de Google Calendar: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al crear reunión: {e}")
            raise GoogleMeetCreationError(
                f"Error al crear reunión de Google Meet: {str(e)}"
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
