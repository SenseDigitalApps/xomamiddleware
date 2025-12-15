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
        
        with transaction.atomic():
            # 1. Buscar o crear usuario organizador
            organizer = self._get_or_create_user_by_email(organizer_email)
            
            # 2. Crear evento en Google Calendar (INTEGRACIÓN REAL - PASO 7)
            google_event_data = self._create_google_meet_event(
                organizer_email=organizer_email,
                invited_emails=invited_emails,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end
            )
            
            # 3. Crear reunión en base de datos
            meeting = Meeting.objects.create(
                google_event_id=google_event_data['event_id'],
                meet_link=google_event_data['meet_link'],
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
                                  scheduled_start=None, scheduled_end=None):
        """
        Crea un evento real en Google Calendar con Google Meet.
        
        Si Google no está configurado, usa mock como fallback.
        
        Args:
            organizer_email (str): Email del organizador
            invited_emails (list): Lista de emails invitados
            scheduled_start (datetime): Fecha de inicio
            scheduled_end (datetime): Fecha de fin
        
        Returns:
            dict: Datos del evento creado
                - event_id: ID del evento en Google Calendar
                - meet_link: URL de Google Meet
                - html_link: Link al evento en Calendar
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
                    scheduled_end=scheduled_end
                )
                
                return {
                    'event_id': event_data['event_id'],
                    'meet_link': event_data['meet_link'],
                    'html_link': event_data.get('html_link', '')
                }
                
            except Exception as e:
                logger.warning(f"Error con Google API, usando mock: {e}")
                # Fallback a mock si falla Google
                return self._create_google_meet_event_mock(
                    organizer_email, invited_emails, scheduled_start, scheduled_end
                )
        else:
            # Usar mock si Google no está configurado
            logger.info("Google no configurado. Usando MOCK para meet_link")
            return self._create_google_meet_event_mock(
                organizer_email, invited_emails, scheduled_start, scheduled_end
            )
    
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
