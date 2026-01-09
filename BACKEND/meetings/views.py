"""
ViewSets para la aplicación de reuniones.

Expone endpoints REST para:
- Crear reuniones de Google Meet
- Listar y consultar reuniones
- Actualizar estado de reuniones
- Cancelar reuniones
- Obtener grabaciones
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Meeting, MeetingRecording, Participant
from .serializers import (
    MeetingCreateSerializer,
    MeetingSerializer,
    MeetingDetailSerializer,
    MeetingListSerializer,
    MeetingRecordingSerializer,
    ParticipantSerializer
)
from .services import MeetingService
from .tasks import sync_meeting_recording_task, sync_all_recordings_task

# Instancia del servicio de negocio
meeting_service = MeetingService()


class MeetingViewSet(viewsets.ViewSet):
    """
    ViewSet para gestionar reuniones de Google Meet.
    
    Proporciona endpoints para:
    - POST /meetings/ - Crear reunión
    - GET /meetings/ - Listar reuniones
    - GET /meetings/{id}/ - Detalle de reunión
    - PATCH /meetings/{id}/ - Actualizar reunión
    - DELETE /meetings/{id}/ - Cancelar reunión
    - GET /meetings/{id}/recording/ - Obtener grabación
    """
    
    def create(self, request):
        """
        Crea una nueva reunión de Google Meet.
        
        Recibe datos desde XOMA, valida y crea:
        - Evento en Google Calendar
        - Reunión en base de datos
        - Participantes
        
        Returns:
            201: Reunión creada exitosamente
            400: Datos inválidos
            500: Error al crear reunión
        """
        serializer = MeetingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Llamar al servicio de negocio
            meeting = meeting_service.create_meeting(serializer.validated_data)
            
            # Serializar respuesta
            response_serializer = MeetingSerializer(meeting)
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al crear reunión: {str(e)}", exc_info=True)
            
            # Proporcionar mensaje de error más detallado
            error_message = str(e)
            if "Google Calendar" in error_message or "Google" in error_message:
                error_message = (
                    f"Error al crear evento en Google Calendar: {str(e)}. "
                    "Verifica la configuración de Google y los logs del servidor."
                )
            
            return Response(
                {
                    'error': error_message,
                    'detail': 'No se pudo crear el evento en Google Calendar. '
                             'La reunión no se guardó en la base de datos.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request):
        """
        Lista todas las reuniones.
        
        Query Parameters:
            - organizer: Filtrar por ID de organizador
            - status: Filtrar por estado (CREATED, SCHEDULED, FINISHED, CANCELLED)
            - scheduled_start__gte: Filtrar por fecha mínima
            - scheduled_start__lte: Filtrar por fecha máxima
        
        Returns:
            200: Lista de reuniones
        """
        queryset = Meeting.objects.select_related('organizer').all().order_by('-created_at')
        
        # Aplicar filtros desde query params
        organizer_id = request.query_params.get('organizer')
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('scheduled_start__gte')
        date_to = request.query_params.get('scheduled_start__lte')
        
        if organizer_id:
            queryset = queryset.filter(organizer_id=organizer_id)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if date_from:
            queryset = queryset.filter(scheduled_start__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(scheduled_start__lte=date_to)
        
        # Usar serializer ligero para listados
        serializer = MeetingListSerializer(queryset, many=True)
        
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """
        Obtiene el detalle completo de una reunión.
        
        Incluye información anidada de:
        - Organizador
        - Participantes
        - Grabación (si existe)
        
        Returns:
            200: Detalle de la reunión
            404: Reunión no encontrada
        """
        meeting = get_object_or_404(
            Meeting.objects.select_related('organizer')
                           .prefetch_related('participants', 'recording'),
            pk=pk
        )
        
        serializer = MeetingDetailSerializer(meeting)
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        """
        Actualiza parcialmente una reunión.
        
        Campos actualizables:
        - status: Estado de la reunión
        - scheduled_start: Fecha de inicio
        - scheduled_end: Fecha de fin
        
        Returns:
            200: Reunión actualizada
            400: Datos inválidos
            404: Reunión no encontrada
        """
        meeting = get_object_or_404(Meeting, pk=pk)
        
        # Solo permitir actualizar ciertos campos
        allowed_fields = ['status', 'scheduled_start', 'scheduled_end']
        update_data = {
            k: v for k, v in request.data.items() 
            if k in allowed_fields
        }
        
        serializer = MeetingSerializer(
            meeting,
            data=update_data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    def destroy(self, request, pk=None):
        """
        Cancela una reunión.
        
        No elimina la reunión, solo cambia su estado a CANCELLED.
        Esto mantiene el historial y la trazabilidad.
        
        Returns:
            200: Reunión cancelada exitosamente
            404: Reunión no encontrada
        """
        meeting = get_object_or_404(Meeting, pk=pk)
        
        # Cambiar estado a cancelado (soft delete)
        meeting.status = 'CANCELLED'
        meeting.save()
        
        # TODO PASO 7: Cancelar evento en Google Calendar
        # google_service.cancel_event(meeting.google_event_id)
        
        return Response(
            {
                'message': 'Reunión cancelada exitosamente',
                'meeting_id': meeting.id,
                'status': meeting.status
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def recording(self, request, pk=None):
        """
        Obtiene la grabación de una reunión si existe.
        
        Custom endpoint: GET /meetings/{id}/recording/
        
        Returns:
            200: Información de la grabación
            404: Reunión no encontrada o sin grabación
        """
        meeting = get_object_or_404(Meeting, pk=pk)
        
        if not hasattr(meeting, 'recording'):
            return Response(
                {
                    'message': 'Esta reunión no tiene grabación disponible',
                    'meeting_id': meeting.id
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MeetingRecordingSerializer(meeting.recording)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """
        Obtiene la lista de participantes de una reunión.
        
        Custom endpoint: GET /meetings/{id}/participants/
        
        Returns:
            200: Lista de participantes
            404: Reunión no encontrada
        """
        meeting = get_object_or_404(Meeting, pk=pk)
        participants = meeting.participants.all()
        
        serializer = ParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def sync_recording(self, request, pk=None):
        """
        Sincroniza la grabación de una reunión específica.
        
        Busca la grabación en Google Drive y la asocia con la reunión.
        La sincronización se ejecuta de forma asíncrona mediante Celery.
        
        Custom endpoint: POST /api/v1/meetings/{id}/sync-recording/
        
        Returns:
            202: Sincronización iniciada (async)
                {
                    "message": "Sincronización iniciada",
                    "meeting_id": 123,
                    "task_id": "abc-123-def",
                    "status": "pending"
                }
            404: Reunión no encontrada
            400: Error en la solicitud
        """
        meeting = get_object_or_404(Meeting, pk=pk)
        
        # Verificar que la reunión tenga scheduled_start
        if not meeting.scheduled_start:
            return Response(
                {
                    'error': 'La reunión no tiene fecha/hora programada',
                    'message': 'No se puede sincronizar grabación sin scheduled_start'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Encolar tarea de sincronización
        try:
            task = sync_meeting_recording_task.delay(meeting.id)
            
            return Response(
                {
                    'message': 'Sincronización de grabación iniciada',
                    'meeting_id': meeting.id,
                    'task_id': task.id,
                    'status': 'pending',
                    'meeting_status': meeting.status,
                    'scheduled_start': meeting.scheduled_start.isoformat() if meeting.scheduled_start else None
                },
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Error al iniciar sincronización',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParticipantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para participantes.
    
    Endpoints:
    - GET /participants/ - Listar participantes
    - GET /participants/{id}/ - Detalle de participante
    """
    
    queryset = Participant.objects.select_related('meeting').all()
    serializer_class = ParticipantSerializer
    
    def get_queryset(self):
        """Permite filtrar por meeting_id"""
        queryset = super().get_queryset()
        meeting_id = self.request.query_params.get('meeting')
        
        if meeting_id:
            queryset = queryset.filter(meeting_id=meeting_id)
        
        return queryset


class MeetingRecordingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para grabaciones.
    
    Endpoints:
    - GET /recordings/ - Listar grabaciones
    - GET /recordings/{id}/ - Detalle de grabación
    - POST /recordings/sync-all/ - Sincronizar todas las grabaciones
    """
    
    queryset = MeetingRecording.objects.select_related('meeting').all()
    serializer_class = MeetingRecordingSerializer
    
    def get_queryset(self):
        """Permite filtrar por meeting_id"""
        queryset = super().get_queryset()
        meeting_id = self.request.query_params.get('meeting')
        
        if meeting_id:
            queryset = queryset.filter(meeting_id=meeting_id)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def sync_all(self, request):
        """
        Sincroniza grabaciones para todas las reuniones sin grabación.
        
        Busca grabaciones en Google Drive para todas las reuniones que:
        - Tienen status FINISHED o SCHEDULED
        - No tienen grabación asociada
        - Tienen scheduled_start definido
        
        La sincronización se ejecuta de forma asíncrona mediante Celery.
        
        Custom endpoint: POST /api/v1/recordings/sync-all/
        
        Query Parameters (opcional):
            - limit: Límite de reuniones a procesar (query param o body)
        
        Request Body (opcional):
            {
                "limit": 50
            }
        
        Returns:
            202: Sincronización iniciada (async)
                {
                    "message": "Sincronización masiva iniciada",
                    "task_id": "abc-123-def",
                    "status": "pending",
                    "limit": 50
                }
            400: Error en la solicitud
            500: Error al iniciar sincronización
        """
        # Obtener límite de query params o body
        limit = request.query_params.get('limit')
        if not limit and request.data:
            limit = request.data.get('limit')
        
        # Convertir a int si está presente
        if limit is not None:
            try:
                limit = int(limit)
                if limit <= 0:
                    return Response(
                        {
                            'error': 'El límite debe ser un número positivo'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {
                        'error': 'El límite debe ser un número válido'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Encolar tarea de sincronización masiva
        try:
            task = sync_all_recordings_task.delay(limit=limit)
            
            return Response(
                {
                    'message': 'Sincronización masiva de grabaciones iniciada',
                    'task_id': task.id,
                    'status': 'pending',
                    'limit': limit
                },
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Error al iniciar sincronización masiva',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
