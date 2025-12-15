"""
Serializers para la aplicación de reuniones.

Incluye serializers para:
- Creación de reuniones (input desde Xoma)
- Serialización de reuniones (output)
- Grabaciones y participantes
"""

from rest_framework import serializers
from .models import Meeting, MeetingRecording, Participant
from accounts.serializers import UserSerializer


class MeetingCreateSerializer(serializers.Serializer):
    """
    Serializer para recibir datos desde Xoma y crear reuniones.
    
    No está basado en el modelo, recibe datos específicos
    que serán procesados por el servicio de Google Meet.
    """
    
    organizer_email = serializers.EmailField(
        help_text='Email del organizador de la reunión'
    )
    
    invited_emails = serializers.ListField(
        child=serializers.EmailField(),
        help_text='Lista de emails de los participantes invitados',
        allow_empty=False
    )
    
    scheduled_start = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Fecha y hora de inicio programada (opcional)'
    )
    
    scheduled_end = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Fecha y hora de fin programada (opcional)'
    )
    
    external_reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text='Referencia externa de Xoma (ej: appointment_id)'
    )
    
    def validate_invited_emails(self, value):
        """Valida que la lista de emails no esté vacía y sean únicos."""
        if not value:
            raise serializers.ValidationError(
                "Debe proporcionar al menos un email invitado."
            )
        
        # Verificar emails únicos
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Los emails invitados deben ser únicos."
            )
        
        return value
    
    def validate(self, data):
        """
        Validación a nivel de objeto para verificar coherencia
        entre scheduled_start y scheduled_end.
        """
        scheduled_start = data.get('scheduled_start')
        scheduled_end = data.get('scheduled_end')
        
        # Si ambos están presentes, validar que end > start
        if scheduled_start and scheduled_end:
            if scheduled_end <= scheduled_start:
                raise serializers.ValidationError({
                    'scheduled_end': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })
        
        # Si solo uno está presente, advertir
        if (scheduled_start and not scheduled_end) or (scheduled_end and not scheduled_start):
            # Esto es válido pero podría necesitar lógica adicional
            pass
        
        return data


class ParticipantSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Participant.
    """
    
    role_display = serializers.CharField(
        source='get_role_display',
        read_only=True
    )
    
    class Meta:
        model = Participant
        fields = [
            'id',
            'meeting',
            'email',
            'role',
            'role_display',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MeetingRecordingSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo MeetingRecording.
    """
    
    meeting_id = serializers.ReadOnlyField(source='meeting.id')
    duration_formatted = serializers.ReadOnlyField()
    
    class Meta:
        model = MeetingRecording
        fields = [
            'id',
            'meeting',
            'meeting_id',
            'drive_file_id',
            'drive_file_url',
            'duration_seconds',
            'duration_formatted',
            'available_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MeetingSerializer(serializers.ModelSerializer):
    """
    Serializer básico para el modelo Meeting.
    
    Usado para listados y respuestas simples.
    """
    
    organizer_username = serializers.ReadOnlyField(source='organizer.username')
    organizer_email = serializers.ReadOnlyField(source='organizer.email')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Campos computados
    participants_count = serializers.SerializerMethodField()
    has_recording = serializers.SerializerMethodField()
    
    class Meta:
        model = Meeting
        fields = [
            'id',
            'google_event_id',
            'meet_link',
            'organizer',
            'organizer_username',
            'organizer_email',
            'invited_emails',
            'scheduled_start',
            'scheduled_end',
            'status',
            'status_display',
            'participants_count',
            'has_recording',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'google_event_id',
            'created_at',
            'updated_at'
        ]
    
    def get_participants_count(self, obj):
        """Retorna el número de participantes."""
        return obj.participants.count()
    
    def get_has_recording(self, obj):
        """Retorna si la reunión tiene grabación."""
        return hasattr(obj, 'recording')


class MeetingDetailSerializer(serializers.ModelSerializer):
    """
    Serializer extendido para el modelo Meeting.
    
    Incluye información anidada de:
    - Organizador (UserSerializer)
    - Participantes (ParticipantSerializer)
    - Grabación (MeetingRecordingSerializer)
    
    Usado para respuestas detalladas de una reunión específica.
    """
    
    organizer = UserSerializer(read_only=True)
    participants = ParticipantSerializer(many=True, read_only=True)
    recording = MeetingRecordingSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Campos computados
    participants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Meeting
        fields = [
            'id',
            'google_event_id',
            'meet_link',
            'organizer',
            'invited_emails',
            'scheduled_start',
            'scheduled_end',
            'status',
            'status_display',
            'participants',
            'participants_count',
            'recording',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'google_event_id',
            'created_at',
            'updated_at'
        ]
    
    def get_participants_count(self, obj):
        """Retorna el número de participantes."""
        return obj.participants.count()


class MeetingListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de reuniones.
    
    Versión ligera sin datos anidados para mejorar performance
    en listados con muchos registros.
    """
    
    organizer_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Meeting
        fields = [
            'id',
            'google_event_id',
            'meet_link',
            'organizer_name',
            'scheduled_start',
            'status',
            'status_display',
            'created_at'
        ]
    
    def get_organizer_name(self, obj):
        """Retorna el nombre completo del organizador o username."""
        if obj.organizer.first_name and obj.organizer.last_name:
            return f"{obj.organizer.first_name} {obj.organizer.last_name}"
        return obj.organizer.username
