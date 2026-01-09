"""
Servicios de lógica de negocio para la aplicación de reuniones.

Centraliza la lógica de negocio separada de las vistas:
- Creación de reuniones
- Integración con Google APIs (PASO 7)
- Gestión de participantes
"""

from django.db import transaction
from accounts.models import User
from .models import Meeting, Participant
import uuid
import traceback
import logging

logger = logging.getLogger(__name__)


class MeetingService:
    """
    Servicio para gestionar la lógica de negocio de reuniones.
    """
    
    def create_meeting(self, validated_data):
        """
        Crea una reunión completa:
        1. Busca o crea el usuario organizador por email
        2. Crea evento en Google Calendar (PASO 7 - por ahora mock)
        3. Guarda la reunión en la base de datos
        4. Crea los participantes
        
        Args:
            validated_data (dict): Datos validados desde MeetingCreateSerializer
                - organizer_email: Email del organizador
                - invited_emails: Lista de emails invitados
                - scheduled_start: Fecha de inicio (opcional)
                - scheduled_end: Fecha de fin (opcional)
                - external_reference: Referencia externa (opcional)
        
        Returns:
            Meeting: Instancia de reunión creada
        """
        organizer_email = validated_data.get('organizer_email')
        invited_emails = validated_data.get('invited_emails', [])
        scheduled_start = validated_data.get('scheduled_start')
        scheduled_end = validated_data.get('scheduled_end')
        external_reference = validated_data.get('external_reference')
        create_calendar_event = validated_data.get('create_calendar_event', True)
        auto_record = validated_data.get('auto_record', False)
        
        with transaction.atomic():
            # 1. Buscar o crear usuario organizador
            organizer = self._get_or_create_user_by_email(organizer_email)
            
            # 2. Crear evento en Google Calendar O solo espacio de Meet
            if create_calendar_event:
                # Flujo original: crear en Calendar
                public_access = validated_data.get('public_access', False)
            google_event_data = self._create_google_meet_event(
                organizer_email=organizer_email,
                invited_emails=invited_emails,
                scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    auto_record=auto_record,
                    public_access=public_access
                )
                event_id = google_event_data['event_id']
                meet_link = google_event_data['meet_link']
            else:
                # Nuevo flujo: solo crear espacio de Meet (sin Calendar)
                from integrations.services import GoogleMeetService
                import uuid
                
                google_service = GoogleMeetService()
                
                # Determinar si usar acceso público
                # PRIORIDAD: Si no se crea evento en Calendar, acceso público por defecto
                # Esto permite que los invitados se unan directamente sin solicitar permiso
                public_access = validated_data.get('public_access')
                if public_access is None:
                    # Si no se especificó, usar True por defecto cuando no hay Calendar
                    public_access = True
                # Convertir a bool explícitamente
                public_access = bool(public_access)
                
                # Logging para debug
                logger.info(f"Creando reunión sin Calendar:")
                logger.info(f"  - auto_record: {auto_record}")
                logger.info(f"  - public_access: {public_access}")
                logger.info(f"  - create_calendar_event: {create_calendar_event}")
                
                try:
                    space_data = google_service.create_meeting_space_only(
                        auto_record=auto_record,
                        invited_emails=invited_emails,
                        organizer_email=organizer_email,
                        public_access=public_access
                    )
                    
                    # Verificar que el espacio se creó con la configuración correcta
                    logger.info(f"Espacio creado. public_access en respuesta: {space_data.get('public_access', 'N/A')}")
                    
                    # Generar ID interno para reuniones sin Calendar
                    event_id = f"meet-{uuid.uuid4().hex}"
                    meet_link = space_data['meet_link']
                    
                    logger.info(f"Reunión creada sin Calendar. ID interno: {event_id}")
                    logger.info(f"Miembros agregados: {space_data.get('members_added', 0)}")
                    
                except Exception as e:
                    error_msg = f"Error al crear espacio de Meet: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"Traceback completo: {traceback.format_exc()}")
                    # Re-lanzar la excepción para que el usuario sepa que falló
                    raise Exception(
                        f"No se pudo crear el espacio de Google Meet. "
                        f"Error: {str(e)}. "
                        f"Verifica la configuración de Google y los logs para más detalles."
            )
            
            # 3. Crear reunión en base de datos
            meeting = Meeting.objects.create(
                google_event_id=event_id,
                meet_link=meet_link,
                organizer=organizer,
                invited_emails=invited_emails,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                status='CREATED'
            )
            
            # 4. Crear participantes
            self._create_participants(meeting, organizer_email, invited_emails)
            
            return meeting
    
    def _get_or_create_user_by_email(self, email):
        """
        Busca un usuario por email o lo crea si no existe.
        
        Args:
            email (str): Email del usuario
        
        Returns:
            User: Instancia del usuario
        """
        # Intentar buscar por email
        user = User.objects.filter(email=email).first()
        
        if user:
            return user
        
        # Si no existe, crear uno nuevo
        # Generar username desde el email
        username = email.split('@')[0]
        
        # Asegurar que el username sea único
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Crear usuario
        user = User.objects.create(
            username=username,
            email=email,
            role='external',  # Default role
            is_active=True
        )
        
        # No establecer password (usuario creado automáticamente)
        # En producción: enviar email para establecer password
        
        return user
    
    def _create_google_meet_event(self, organizer_email, invited_emails, 
                                  scheduled_start=None, scheduled_end=None, auto_record=False,
                                  public_access=False):
        """
        Crea un evento real en Google Calendar con Google Meet.
        
        Si Google no está configurado, usa mock como fallback.
        
        Args:
            organizer_email (str): Email del organizador
            invited_emails (list): Lista de emails invitados
            scheduled_start (datetime): Fecha de inicio
            scheduled_end (datetime): Fecha de fin
            auto_record (bool): Si True, habilita grabación automática
            public_access (bool): Si True, configura acceso público (OPEN) al espacio de Meet
        
        Returns:
            dict: Datos del evento creado
                - event_id: ID del evento en Google Calendar
                - meet_link: URL de Google Meet
                - html_link: Link al evento en Calendar
                - recording_enabled: True si la grabación se configuró
        """
        from integrations.config import validate_google_credentials
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Verificar si Google está configurado
        google_configured = validate_google_credentials(raise_exception=False)
        
        if google_configured:
            # Usar integración real con Google
            try:
                from integrations.services import GoogleMeetService
                
                logger.info("Usando integración REAL con Google Calendar API")
                
                google_service = GoogleMeetService()
                event_data = google_service.create_meeting_event(
                    organizer_email=organizer_email,
                    invited_emails=invited_emails,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    auto_record=auto_record,
                    public_access=public_access
                )
                
                return {
                    'event_id': event_data['event_id'],
                    'meet_link': event_data['meet_link'],
                    'html_link': event_data.get('html_link', ''),
                    'recording_enabled': event_data.get('recording_enabled', False)
                }
                
            except Exception as e:
                error_msg = f"Error con Google API: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Traceback completo: {traceback.format_exc()}")
                # Re-lanzar la excepción para que el usuario sepa que falló
                # No usar mock silenciosamente
                raise Exception(
                    f"No se pudo crear el evento en Google Calendar. "
                    f"Error: {str(e)}. "
                    f"Verifica la configuración de Google y los logs para más detalles."
                )
        else:
            # Google no está configurado - lanzar error en lugar de usar mock silenciosamente
            error_msg = (
                "Google Calendar no está configurado correctamente. "
                "Verifica que GOOGLE_SERVICE_ACCOUNT_FILE esté configurado en .env"
            )
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _create_google_meet_event_mock(self, organizer_email, invited_emails,
                                       scheduled_start=None, scheduled_end=None):
        """
        MOCK - Simula la creación de un evento en Google Calendar.
        
        Usado cuando Google Service Account no está configurado.
        Permite probar el sistema sin credenciales de Google.
        
        Args:
            organizer_email (str): Email del organizador
            invited_emails (list): Lista de emails invitados
            scheduled_start (datetime): Fecha de inicio
            scheduled_end (datetime): Fecha de fin
        
        Returns:
            dict: Datos simulados del evento
                - event_id: ID del evento (mock)
                - meet_link: URL de Google Meet (mock)
        """
        # Generar IDs mock
        event_id = f"mock_event_{uuid.uuid4().hex[:12]}"
        meet_code = f"{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}"
        meet_link = f"https://meet.google.com/{meet_code}"
        
        return {
            'event_id': event_id,
            'meet_link': meet_link,
            'html_link': ''
        }
    
    def _create_participants(self, meeting, organizer_email, invited_emails):
        """
        Crea los registros de participantes para una reunión.
        
        Args:
            meeting (Meeting): Instancia de la reunión
            organizer_email (str): Email del organizador
            invited_emails (list): Lista de emails invitados
        """
        # Crear participante organizador
        Participant.objects.create(
            meeting=meeting,
            email=organizer_email,
            role='organizer'
        )
        
        # Crear participantes invitados
        for email in invited_emails:
            # Evitar duplicados (si el organizador está en la lista de invitados)
            if email.lower() != organizer_email.lower():
                Participant.objects.create(
                    meeting=meeting,
                    email=email,
                    role='guest'
                )
    
    def update_meeting_status(self, meeting_id, new_status):
        """
        Actualiza el estado de una reunión.
        
        Args:
            meeting_id (int): ID de la reunión
            new_status (str): Nuevo estado
        
        Returns:
            Meeting: Reunión actualizada
        """
        meeting = Meeting.objects.get(pk=meeting_id)
        meeting.status = new_status
        meeting.save()
        return meeting
    
    def cancel_meeting(self, meeting_id):
        """
        Cancela una reunión.
        
        Args:
            meeting_id (int): ID de la reunión
        
        Returns:
            Meeting: Reunión cancelada
        """
        return self.update_meeting_status(meeting_id, 'CANCELLED')
