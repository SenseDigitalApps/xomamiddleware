"""
Modelos para la aplicación de reuniones.

Incluye:
- Meeting: Reuniones de Google Meet
- MeetingRecording: Grabaciones de las reuniones
- Participant: Participantes de las reuniones
"""

from django.conf import settings
from django.db import models


class Meeting(models.Model):
    """
    Modelo que representa una reunión de Google Meet.
    
    Almacena información de la reunión, el link de Meet,
    participantes invitados y estado de la reunión.
    """
    
    STATUS_CHOICES = (
        ('CREATED', 'Created'),
        ('SCHEDULED', 'Scheduled'),
        ('FINISHED', 'Finished'),
        ('CANCELLED', 'Cancelled'),
    )
    
    google_event_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name='ID de Evento de Google',
        help_text='ID único del evento en Google Calendar (opcional si no se crea en Calendar)'
    )
    
    meet_link = models.URLField(
        verbose_name='Link de Google Meet',
        help_text='URL de la videollamada de Google Meet'
    )
    
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='organized_meetings',
        verbose_name='Organizador',
        help_text='Usuario que crea/organiza la reunión'
    )
    
    invited_emails = models.JSONField(
        default=list,
        verbose_name='Emails Invitados',
        help_text='Lista de correos electrónicos de los invitados'
    )
    
    scheduled_start = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Inicio Programado',
        help_text='Fecha y hora de inicio programada'
    )
    
    scheduled_end = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fin Programado',
        help_text='Fecha y hora de fin programada'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='CREATED',
        verbose_name='Estado',
        help_text='Estado actual de la reunión'
    )
    
    conference_record_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Conference Record ID',
        help_text='ID del conference record de Google Meet (se crea cuando la conferencia inicia)'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Actualización'
    )
    
    class Meta:
        verbose_name = 'Reunión'
        verbose_name_plural = 'Reuniones'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['google_event_id']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['conference_record_id']),
        ]
    
    def __str__(self):
        return f"Meeting {self.id} ({self.google_event_id})"


class MeetingRecording(models.Model):
    """
    Modelo que representa una grabación de una reunión.
    
    Almacena información sobre la grabación almacenada
    en Google Drive, incluyendo URL y metadatos.
    """
    
    RECORDING_STATE_CHOICES = (
        ('STARTED', 'Started'),
        ('ENDED', 'Ended'),
        ('FILE_GENERATED', 'File Generated'),
    )
    
    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name='recording',
        verbose_name='Reunión',
        help_text='Reunión a la que pertenece esta grabación'
    )
    
    drive_file_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='ID de Archivo en Drive',
        help_text='ID del archivo de grabación en Google Drive'
    )
    
    drive_file_url = models.URLField(
        null=True,
        blank=True,
        verbose_name='URL del Archivo en Drive',
        help_text='URL directa al archivo de grabación'
    )
    
    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Duración (segundos)',
        help_text='Duración de la grabación en segundos'
    )
    
    recording_state = models.CharField(
        max_length=20,
        choices=RECORDING_STATE_CHOICES,
        null=True,
        blank=True,
        verbose_name='Estado de Grabación',
        help_text='Estado actual de la grabación según Google Meet API (STARTED, ENDED, FILE_GENERATED)'
    )
    
    recording_start_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Inicio de Grabación',
        help_text='Timestamp de inicio de la grabación desde Google Meet API'
    )
    
    recording_end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fin de Grabación',
        help_text='Timestamp de fin de la grabación desde Google Meet API'
    )
    
    available_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Disponible Desde',
        help_text='Fecha y hora en que la grabación estuvo disponible'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro'
    )
    
    class Meta:
        verbose_name = 'Grabación de Reunión'
        verbose_name_plural = 'Grabaciones de Reuniones'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recording for Meeting {self.meeting.id}"
    
    @property
    def duration_formatted(self):
        """Retorna la duración en formato HH:MM:SS"""
        if not self.duration_seconds:
            return "N/A"
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    @property
    def is_ready(self):
        """Retorna True si la grabación está lista (FILE_GENERATED)"""
        return self.recording_state == 'FILE_GENERATED'


class Participant(models.Model):
    """
    Modelo que representa un participante en una reunión.
    
    Registra los participantes invitados o asistentes a una reunión,
    con su email y rol en la reunión.
    """
    
    ROLE_CHOICES = (
        ('organizer', 'Organizer'),
        ('guest', 'Guest'),
    )
    
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name='Reunión',
        help_text='Reunión a la que pertenece este participante'
    )
    
    email = models.EmailField(
        verbose_name='Email',
        help_text='Correo electrónico del participante'
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='guest',
        verbose_name='Rol',
        help_text='Rol del participante en la reunión'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro'
    )
    
    class Meta:
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
        ordering = ['created_at']
        unique_together = [['meeting', 'email']]
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['meeting', 'email']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
