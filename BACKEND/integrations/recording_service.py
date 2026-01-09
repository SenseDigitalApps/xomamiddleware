"""
Servicio de sincronización de grabaciones de Google Meet.

Maneja la lógica de negocio para:
- Buscar grabaciones en Google Drive
- Asociar grabaciones con reuniones
- Crear/actualizar registros de grabaciones en la base de datos
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from django.utils import timezone
from django.db import transaction, models
from django.db.models import Case, When, IntegerField

from .drive_client import GoogleDriveClient
from .meet_conference_client import GoogleMeetConferenceClient
from meetings.models import Meeting, MeetingRecording
from core.exceptions import GoogleDriveError, GoogleMeetError

logger = logging.getLogger(__name__)


class RecordingSyncService:
    """
    Servicio para sincronizar grabaciones de Google Meet desde Google Drive.
    
    Proporciona métodos de alto nivel para:
    - Sincronizar grabación de una reunión específica
    - Sincronizar todas las grabaciones pendientes
    - Asociar grabaciones con reuniones usando fecha/hora
    """
    
    def __init__(self):
        """Inicializa el servicio con los clientes de Drive y Meet Conference."""
        try:
            self.drive_client = GoogleDriveClient()
            try:
                self.conference_client = GoogleMeetConferenceClient()
                logger.info("RecordingSyncService inicializado con Conference Client")
            except Exception as e:
                logger.warning(f"No se pudo inicializar Conference Client: {e}")
                self.conference_client = None
            logger.info("RecordingSyncService inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar RecordingSyncService: {e}")
            raise
    
    def sync_meeting_recording(self, meeting: Meeting) -> Optional[MeetingRecording]:
        """
        Sincroniza la grabación para una reunión específica.
        
        Estrategia mejorada:
        1. Si tenemos conference_record_id, usar Conference Records API (más preciso)
        2. Si no, buscar en Drive como fallback
        
        Args:
            meeting (Meeting): Reunión para la cual buscar grabación
        
        Returns:
            MeetingRecording: Grabación encontrada y asociada, o None si no se encuentra
        
        Raises:
            GoogleDriveError: Si hay error al buscar en Drive (no crítico)
        """
        try:
            logger.info(f"Sincronizando grabación para Meeting {meeting.id} (Event ID: {meeting.google_event_id})")
            
            # Verificar si ya tiene grabación
            if hasattr(meeting, 'recording'):
                logger.info(f"Meeting {meeting.id} ya tiene grabación asociada")
                return meeting.recording
            
            # Estrategia 1: Intentar obtener desde Conference Records API (si tenemos ID)
            if meeting.conference_record_id and self.conference_client:
                recording_data = self._find_recording_from_conference_record(meeting)
                if recording_data:
                    logger.info(f"Grabación encontrada desde Conference Records API para Meeting {meeting.id}")
                    recording = self._create_or_update_recording_from_api(meeting, recording_data)
                    logger.info(f"Grabación sincronizada exitosamente desde API para Meeting {meeting.id}")
                    return recording
            
            # Estrategia 2: Buscar en Drive (fallback)
            logger.debug(f"Buscando grabación en Drive para Meeting {meeting.id}")
            drive_file = self._find_recording_in_drive(meeting)
            
            if not drive_file:
                logger.info(f"No se encontró grabación para Meeting {meeting.id}")
                return None
            
            # Crear o actualizar registro de grabación desde Drive
            recording = self._create_or_update_recording_from_drive(meeting, drive_file)
            
            logger.info(f"Grabación sincronizada exitosamente desde Drive para Meeting {meeting.id}")
            return recording
            
        except (GoogleDriveError, GoogleMeetError) as e:
            logger.warning(f"Error de Google API al sincronizar Meeting {meeting.id}: {e}")
            # No es crítico, puede que simplemente no haya grabación
            return None
        except Exception as e:
            logger.error(f"Error inesperado al sincronizar Meeting {meeting.id}: {e}")
            # No fallar completamente, solo loguear
            return None
    
    def sync_all_recordings(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Sincroniza grabaciones para todas las reuniones sin grabación.
        
        Estrategia mejorada (a la luz de los cambios recientes):
        - Busca reuniones que NO tienen grabación asociada
        - Prioriza reuniones con conference_record_id (búsqueda más precisa)
        - Requiere meet_link (necesario para búsqueda por código de Meet)
        - No requiere scheduled_start (la búsqueda puede usar created_at como fallback)
        - Incluye todos los status (CREATED, SCHEDULED, FINISHED) ya que la búsqueda
          por código de Meet funciona independientemente del status
        
        Args:
            limit (int, optional): Límite de reuniones a procesar
        
        Returns:
            dict: Estadísticas de sincronización
                - processed: Número de reuniones procesadas
                - found: Número de grabaciones encontradas
                - created: Número de grabaciones creadas
                - updated: Número de grabaciones actualizadas
                - errors: Número de errores
        """
        try:
            logger.info("Iniciando sincronización masiva de grabaciones")
            
            # Obtener reuniones sin grabación
            # Criterios:
            # 1. No tener grabación asociada
            # 2. Tener meet_link (necesario para búsqueda por código de Meet)
            # 3. Priorizar reuniones con conference_record_id (más precisas)
            base_queryset = Meeting.objects.exclude(
                recording__isnull=False
            ).filter(
                meet_link__isnull=False  # Requerido para búsqueda por código de Meet
            )
            
            # Priorizar reuniones con conference_record_id (búsqueda más precisa)
            # Ordenar: primero las que tienen conference_record_id (prioridad 0), luego las que no (prioridad 1)
            # Luego ordenar por fecha más reciente (scheduled_start si existe, sino created_at)
            queryset = base_queryset.annotate(
                has_conference_id=Case(
                    When(conference_record_id__isnull=False, then=0),
                    default=1,
                    output_field=IntegerField()
                )
            ).order_by(
                'has_conference_id',  # 0 primero (tienen conference_record_id), 1 después
                '-scheduled_start',  # Más recientes primero (NULLs al final)
                '-created_at'  # Fallback si no hay scheduled_start
            )
            
            if limit:
                queryset = queryset[:limit]
            
            meetings = list(queryset)
            logger.info(f"Encontradas {len(meetings)} reuniones sin grabación")
            
            # Log de estadísticas de las reuniones encontradas
            with_conference_id = sum(1 for m in meetings if m.conference_record_id)
            with_scheduled = sum(1 for m in meetings if m.scheduled_start)
            logger.info(f"  - Con conference_record_id: {with_conference_id}")
            logger.info(f"  - Con scheduled_start: {with_scheduled}")
            logger.info(f"  - Sin scheduled_start (usará created_at): {len(meetings) - with_scheduled}")
            
            stats = {
                'processed': 0,
                'found': 0,
                'created': 0,
                'updated': 0,
                'errors': 0
            }
            
            for meeting in meetings:
                try:
                    stats['processed'] += 1
                    
                    # Sincronizar grabación
                    recording = self.sync_meeting_recording(meeting)
                    
                    if recording:
                        stats['found'] += 1
                        # Verificar si fue creada o actualizada
                        # Comparar timestamps con tolerancia de 1 segundo (por posibles diferencias de precisión)
                        time_diff = abs((recording.created_at - meeting.created_at).total_seconds())
                        if time_diff < 1:
                            stats['created'] += 1
                        else:
                            stats['updated'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error al sincronizar Meeting {meeting.id}: {e}")
            
            logger.info(f"Sincronización masiva completada: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error inesperado en sincronización masiva: {e}")
            raise
    
    def _find_recording_in_drive(self, meeting: Meeting) -> Optional[Dict[str, Any]]:
        """
        Busca grabación en Google Drive para una reunión.
        
        Estrategia implementada:
        1. Buscar por código de Meet en el nombre
        2. Buscar por event_id 
        3. Buscar por rango de fechas usando scheduled_start 
        4. Buscar por rango de fechas usando created_at
        5. Filtrar resultados por nombre si hay múltiples
        
        Args:
            meeting (Meeting): Reunión para la cual buscar
        
        Returns:
            dict: Información del archivo de Drive, o None si no se encuentra
        """
        try:
            # Estrategia 1: Buscar por código de Meet en el nombre (MÁS CONFIABLE)
            # Las grabaciones se guardan como: "{meeting_code} (YYYY-MM-DD HH:MM GMT-5)"
            if meeting.meet_link:
                # Extraer código de Meet del link
                # Formato: https://meet.google.com/{meeting_code} o https://meet.google.com/{meeting_code}?...
                try:
                    meeting_code = meeting.meet_link.split('meet.google.com/')[-1].split('?')[0].split('/')[0]
                    if meeting_code and len(meeting_code) > 5:  # Validar que sea un código válido
                        logger.info(f"Buscando grabación por código de Meet: {meeting_code}")
                        drive_file = self.drive_client.search_recording_by_meeting_code(meeting_code)
                        if drive_file:
                            logger.info(f"✅ Grabación encontrada por código de Meet para Meeting {meeting.id}")
                            return drive_file
                except Exception as e:
                    logger.debug(f"No se pudo extraer código de Meet: {e}")
            
            # Estrategia 2: Buscar por event_id (poco probable)
            if meeting.google_event_id:
                drive_file = self.drive_client.search_recording_by_event_id(meeting.google_event_id)
                if drive_file:
                    logger.info(f"Grabación encontrada por event_id para Meeting {meeting.id}")
                    return drive_file
            
            # Estrategia 3: Buscar por rango de fechas
            # Determinar qué fecha usar para la búsqueda
            if meeting.scheduled_start and meeting.scheduled_start <= timezone.now():
                # Si scheduled_start es válido y en el pasado, usarlo
                search_start = meeting.scheduled_start - timedelta(minutes=5)
                if meeting.scheduled_end:
                    search_end = meeting.scheduled_end + timedelta(minutes=15)
                else:
                    search_end = meeting.scheduled_start + timedelta(hours=2)
                logger.debug(f"Buscando grabación usando scheduled_start: {search_start} a {search_end}")
            elif meeting.created_at:
                # Si scheduled_start es futuro o no existe, usar fecha de creación del meeting
                # Las grabaciones se crean poco después de que termina la reunión
                search_start = meeting.created_at - timedelta(hours=1)
                search_end = meeting.created_at + timedelta(hours=2)
                logger.info(f"scheduled_start no válido o futuro. Buscando usando created_at: {search_start} a {search_end}")
            else:
                logger.debug(f"Meeting {meeting.id} no tiene scheduled_start ni created_at, no se puede buscar")
                return None
            
            recordings = self.drive_client.search_recordings_by_date_range(
                search_start, 
                search_end, 
                limit=20
            )
            
            if not recordings:
                logger.debug(f"No se encontraron grabaciones en el rango para Meeting {meeting.id}")
                return None
            
            # Si hay múltiples, intentar filtrar por código de Meet o nombre
            if len(recordings) > 1:
                logger.debug(f"Múltiples grabaciones encontradas ({len(recordings)}), filtrando...")
                
                # Intentar filtrar por código de Meet si está disponible
                if meeting.meet_link:
                    try:
                        meeting_code = meeting.meet_link.split('meet.google.com/')[-1].split('?')[0].split('/')[0]
                        matching = [r for r in recordings if meeting_code in r.get('name', '')]
                        if matching:
                            logger.info(f"Grabación filtrada por código de Meet: {meeting_code}")
                            return matching[0]
                    except Exception:
                        pass
                
                # Filtrar por nombre del evento si es posible
                filtered = self._filter_recordings_by_meeting(recordings, meeting)
                if filtered:
                    return filtered
                # Si no se puede filtrar, usar la más reciente
                logger.debug("Usando la grabación más reciente")
                return recordings[0]
            
            # Una sola grabación encontrada
            logger.debug(f"Grabación única encontrada para Meeting {meeting.id}")
            return recordings[0]
            
        except GoogleDriveError as e:
            logger.warning(f"Error de Google Drive al buscar grabación: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al buscar grabación: {e}")
            return None
    
    def _filter_recordings_by_meeting(self, recordings: List[Dict[str, Any]], 
                                     meeting: Meeting) -> Optional[Dict[str, Any]]:
        """
        Filtra grabaciones por nombre del evento si es posible.
        
        Intenta encontrar la grabación cuyo nombre coincida con el título
        del evento en Google Calendar.
        
        Args:
            recordings (List[Dict]): Lista de grabaciones encontradas
            meeting (Meeting): Reunión para filtrar
        
        Returns:
            dict: Grabación que mejor coincide, o None
        """
        try:
            # Obtener título del evento desde Google Calendar
            from integrations.google_client import GoogleCalendarClient
            calendar_client = GoogleCalendarClient()
            event = calendar_client.get_event(meeting.google_event_id)
            
            event_title = event.get('summary', '').lower()
            if not event_title:
                return None
            
            # Buscar grabación cuyo nombre contenga palabras del título
            event_words = set(event_title.split())
            
            best_match = None
            best_score = 0
            
            for recording in recordings:
                recording_name = recording.get('name', '').lower()
                recording_words = set(recording_name.split())
                
                # Calcular score: palabras comunes
                common_words = event_words.intersection(recording_words)
                score = len(common_words)
                
                if score > best_score:
                    best_score = score
                    best_match = recording
            
            if best_match and best_score > 0:
                logger.debug(f"Grabación filtrada por nombre (score: {best_score})")
                return best_match
            
            return None
            
        except Exception as e:
            logger.debug(f"Error al filtrar por nombre (puede ser normal): {e}")
            return None
    
    def _find_recording_from_conference_record(self, meeting: Meeting) -> Optional[Dict[str, Any]]:
        """
        Obtiene grabación desde Conference Records API.
        
        Según documentación:
        https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords.recordings
        
        Args:
            meeting (Meeting): Reunión con conference_record_id
        
        Returns:
            dict: Datos de la grabación desde API, o None si no se encuentra
        """
        try:
            if not meeting.conference_record_id or not self.conference_client:
                return None
            
            conference_name = f"conferenceRecords/{meeting.conference_record_id}"
            
            # Listar grabaciones (solo las listas: FILE_GENERATED)
            recordings = self.conference_client.list_recordings(
                conference_name, 
                only_ready=True
            )
            
            if recordings:
                # Usar la más reciente si hay múltiples
                # Ordenar por endTime descendente
                recordings.sort(
                    key=lambda x: x.get('endTime', ''),
                    reverse=True
                )
                logger.info(f"Encontrada grabación desde API para Meeting {meeting.id}")
                return recordings[0]
            
            logger.debug(f"No se encontraron grabaciones listas para Meeting {meeting.id}")
            return None
            
        except GoogleMeetError as e:
            logger.warning(f"Error al obtener grabación desde API: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error inesperado al obtener desde API: {e}")
            return None
    
    def _create_or_update_recording_from_api(self, meeting: Meeting, 
                                            recording_data: Dict[str, Any]) -> MeetingRecording:
        """
        Crea o actualiza grabación desde datos de Conference Records API.
        
        Extrae información de:
        - driveDestination.file: fileId directo
        - driveDestination.exportUri: URL optimizada
        - state: Estado de la grabación
        - startTime/endTime: Timestamps para duración
        
        Args:
            meeting (Meeting): Reunión asociada
            recording_data (dict): Datos de la grabación desde API
        
        Returns:
            MeetingRecording: Grabación creada o actualizada
        """
        try:
            # Extraer driveDestination
            drive_dest = recording_data.get('driveDestination', {})
            file_id = drive_dest.get('file')
            file_url = drive_dest.get('exportUri')
            
            if not file_id:
                logger.warning(f"No se encontró fileId en recording_data para Meeting {meeting.id}")
                return None
            
            # Extraer estado
            recording_state = recording_data.get('state')
            
            # Calcular duración desde timestamps
            duration_seconds = self._calculate_duration_from_timestamps(
                recording_data.get('startTime'),
                recording_data.get('endTime')
            )
            
            # Parsear timestamps
            recording_start_time = self._parse_timestamp(recording_data.get('startTime'))
            recording_end_time = self._parse_timestamp(recording_data.get('endTime'))
            
            # Usar endTime como available_at si está disponible
            available_at = recording_end_time
            
            # Crear o actualizar registro
            with transaction.atomic():
                recording, created = MeetingRecording.objects.update_or_create(
                    meeting=meeting,
                    defaults={
                        'drive_file_id': file_id,
                        'drive_file_url': file_url,
                        'duration_seconds': duration_seconds,
                        'recording_state': recording_state,
                        'recording_start_time': recording_start_time,
                        'recording_end_time': recording_end_time,
                        'available_at': available_at,
                    }
                )
                
                action = "creada" if created else "actualizada"
                logger.info(f"Grabación {action} desde API para Meeting {meeting.id}: {file_id}")
                
                return recording
                
        except Exception as e:
            logger.error(f"Error al crear/actualizar grabación desde API: {e}")
            raise
    
    def _create_or_update_recording_from_drive(self, meeting: Meeting, 
                                              drive_file_info: Dict[str, Any]) -> MeetingRecording:
        """
        Crea o actualiza grabación desde datos de Drive (método legacy).
        
        Args:
            meeting (Meeting): Reunión asociada
            drive_file_info (dict): Información del archivo de Drive
        
        Returns:
            MeetingRecording: Grabación creada o actualizada
        """
        try:
            file_id = drive_file_info.get('id')
            
            # Obtener metadatos completos del archivo
            metadata = self.drive_client.get_file_metadata(file_id)
            
            # Extraer información
            duration_seconds = self._extract_duration_from_metadata(metadata)
            available_at = self._extract_available_date(metadata)
            file_url = metadata.get('webViewLink') or self.drive_client.get_file_url(file_id)
            
            # Crear o actualizar registro
            with transaction.atomic():
                recording, created = MeetingRecording.objects.update_or_create(
                    meeting=meeting,
                    defaults={
                        'drive_file_id': file_id,
                        'drive_file_url': file_url,
                        'duration_seconds': duration_seconds,
                        'available_at': available_at,
                    }
                )
                
                action = "creada" if created else "actualizada"
                logger.info(f"Grabación {action} desde Drive para Meeting {meeting.id}: {file_id}")
                
                return recording
                
        except Exception as e:
            logger.error(f"Error al crear/actualizar grabación desde Drive: {e}")
            raise
    
    def _create_or_update_recording(self, meeting: Meeting, 
                                   drive_file_info: Dict[str, Any]) -> MeetingRecording:
        """
        Método legacy - redirige a _create_or_update_recording_from_drive.
        
        Mantenido para compatibilidad.
        """
        return self._create_or_update_recording_from_drive(meeting, drive_file_info)
        """
        Crea o actualiza un registro de MeetingRecording.
        
        Extrae metadatos del archivo de Drive y los guarda en la base de datos.
        
        Args:
            meeting (Meeting): Reunión asociada
            drive_file_info (dict): Información del archivo de Drive
        
        Returns:
            MeetingRecording: Grabación creada o actualizada
        """
        try:
            file_id = drive_file_info.get('id')
            
            # Obtener metadatos completos del archivo
            metadata = self.drive_client.get_file_metadata(file_id)
            
            # Extraer información
            duration_seconds = self._extract_duration_from_metadata(metadata)
            available_at = self._extract_available_date(metadata)
            file_url = metadata.get('webViewLink') or self.drive_client.get_file_url(file_id)
            
            # Crear o actualizar registro
            with transaction.atomic():
                recording, created = MeetingRecording.objects.update_or_create(
                    meeting=meeting,
                    defaults={
                        'drive_file_id': file_id,
                        'drive_file_url': file_url,
                        'duration_seconds': duration_seconds,
                        'available_at': available_at,
                    }
                )
                
                action = "creada" if created else "actualizada"
                logger.info(f"Grabación {action} para Meeting {meeting.id}: {file_id}")
                
                return recording
                
        except Exception as e:
            logger.error(f"Error al crear/actualizar grabación: {e}")
            raise
    
    def _extract_duration_from_metadata(self, metadata: Dict[str, Any]) -> Optional[int]:
        """
        Extrae la duración de los metadatos de Drive.
        
        Args:
            metadata (dict): Metadatos del archivo de Drive
        
        Returns:
            int: Duración en segundos, o None si no está disponible
        """
        try:
            video_meta = metadata.get('videoMediaMetadata', {})
            duration_ms = video_meta.get('durationMillis')
            
            if duration_ms:
                # Convertir de milisegundos a segundos
                duration_seconds = int(duration_ms) // 1000
                logger.debug(f"Duración extraída: {duration_seconds} segundos")
                return duration_seconds
            
            return None
            
        except Exception as e:
            logger.warning(f"Error al extraer duración: {e}")
            return None
    
    def _extract_available_date(self, metadata: Dict[str, Any]) -> Optional[datetime]:
        """
        Extrae la fecha de disponibilidad de los metadatos.
        
        Usa la fecha de creación del archivo como fecha de disponibilidad.
        
        Args:
            metadata (dict): Metadatos del archivo de Drive
        
        Returns:
            datetime: Fecha de disponibilidad, o None si no está disponible
        """
        try:
            created_time_str = metadata.get('createdTime')
            
            if created_time_str:
                # Parsear fecha ISO 8601
                # Formato: "2025-12-26T10:35:00.000Z"
                created_time = datetime.fromisoformat(created_time_str.replace('Z', '+00:00'))
                # Convertir a timezone aware si es necesario
                if timezone.is_naive(created_time):
                    created_time = timezone.make_aware(created_time)
                
                logger.debug(f"Fecha de disponibilidad extraída: {created_time}")
                return created_time
            
            return None
            
        except Exception as e:
            logger.warning(f"Error al extraer fecha de disponibilidad: {e}")
            return None
    
    def _calculate_duration_from_timestamps(self, start_time: Optional[str], 
                                           end_time: Optional[str]) -> Optional[int]:
        """
        Calcula duración en segundos desde timestamps de la API.
        
        Args:
            start_time: Timestamp ISO 8601 (ej: "2025-01-15T10:00:00Z")
            end_time: Timestamp ISO 8601 (ej: "2025-01-15T11:30:00Z")
        
        Returns:
            int: Duración en segundos, o None si hay error
        """
        try:
            if not start_time or not end_time:
                return None
            
            start = self._parse_timestamp(start_time)
            end = self._parse_timestamp(end_time)
            
            if start and end:
                duration = (end - start).total_seconds()
                duration_seconds = int(duration)
                logger.debug(f"Duración calculada desde timestamps: {duration_seconds} segundos")
                return duration_seconds
            
            return None
            
        except Exception as e:
            logger.warning(f"Error al calcular duración desde timestamps: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """
        Parsea un timestamp ISO 8601 a datetime.
        
        Args:
            timestamp_str: Timestamp en formato ISO 8601 (ej: "2025-01-15T10:00:00Z")
        
        Returns:
            datetime: Objeto datetime o None si hay error
        """
        try:
            if not timestamp_str:
                return None
            
            # Reemplazar 'Z' con '+00:00' para compatibilidad con fromisoformat
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            
            dt = datetime.fromisoformat(timestamp_str)
            
            # Convertir a timezone aware si es necesario
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            
            return dt
            
        except Exception as e:
            logger.warning(f"Error al parsear timestamp {timestamp_str}: {e}")
            return None

