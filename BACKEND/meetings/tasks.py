"""
Tareas asíncronas de Celery para reuniones.

Incluye tareas para:
- Sincronización de grabaciones de Google Meet
- Sincronización masiva de grabaciones
"""

import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from integrations.recording_service import RecordingSyncService
from meetings.models import Meeting

logger = logging.getLogger(__name__)


@shared_task(name='meetings.sync_meeting_recording', bind=True, max_retries=3)
def sync_meeting_recording_task(self, meeting_id: int):
    """
    Tarea para sincronizar grabación de una reunión específica.
    
    Busca la grabación en Google Drive y la asocia con la reunión.
    Si no se encuentra, no es un error (la reunión puede no haberse grabado).
    
    Args:
        meeting_id (int): ID de la reunión a sincronizar
    
    Returns:
        dict: Resultado de la sincronización
            - success (bool): Si la tarea se completó exitosamente
            - meeting_id (int): ID de la reunión
            - recording_found (bool): Si se encontró grabación
            - recording_id (int, optional): ID de la grabación si se encontró
            - error (str, optional): Mensaje de error si hubo problema
    
    Raises:
        Retry: Si hay error temporal, reintenta hasta 3 veces
    """
    try:
        logger.info(f"Iniciando sincronización de grabación para Meeting {meeting_id}")
        
        # Obtener reunión
        try:
            meeting = Meeting.objects.get(pk=meeting_id)
        except ObjectDoesNotExist:
            error_msg = f"Meeting {meeting_id} no encontrado"
            logger.error(error_msg)
            return {
                'success': False,
                'meeting_id': meeting_id,
                'recording_found': False,
                'error': error_msg
            }
        
        # Sincronizar grabación
        sync_service = RecordingSyncService()
        recording = sync_service.sync_meeting_recording(meeting)
        
        if recording:
            logger.info(f"Grabación encontrada y sincronizada para Meeting {meeting_id}: {recording.id}")
            return {
                'success': True,
                'meeting_id': meeting_id,
                'recording_found': True,
                'recording_id': recording.id,
                'drive_file_id': recording.drive_file_id,
                'duration_seconds': recording.duration_seconds
            }
        else:
            logger.info(f"No se encontró grabación para Meeting {meeting_id} (puede ser normal)")
            return {
                'success': True,
                'meeting_id': meeting_id,
                'recording_found': False,
                'message': 'No se encontró grabación en Drive'
            }
            
    except Exception as e:
        error_msg = f"Error al sincronizar grabación para Meeting {meeting_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Reintentar si es un error temporal
        if self.request.retries < self.max_retries:
            logger.warning(f"Reintentando sincronización (intento {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))  # Backoff exponencial
        
        # Si se agotaron los reintentos, retornar error
        return {
            'success': False,
            'meeting_id': meeting_id,
            'recording_found': False,
            'error': error_msg
        }


@shared_task(name='meetings.sync_all_recordings', bind=True, max_retries=2)
def sync_all_recordings_task(self, limit: int = None):
    """
    Tarea periódica para sincronizar todas las grabaciones pendientes.
    
    Busca grabaciones para todas las reuniones que:
    - Tienen status FINISHED o SCHEDULED
    - No tienen grabación asociada
    - Tienen scheduled_start definido
    
    Args:
        limit (int, optional): Límite de reuniones a procesar
    
    Returns:
        dict: Estadísticas de sincronización
            - success (bool): Si la tarea se completó exitosamente
            - processed (int): Número de reuniones procesadas
            - found (int): Número de grabaciones encontradas
            - created (int): Número de grabaciones creadas
            - updated (int): Número de grabaciones actualizadas
            - errors (int): Número de errores
            - error (str, optional): Mensaje de error si hubo problema crítico
    
    Raises:
        Retry: Si hay error temporal, reintenta hasta 2 veces
    """
    try:
        logger.info(f"Iniciando sincronización masiva de grabaciones (limit: {limit})")
        
        sync_service = RecordingSyncService()
        stats = sync_service.sync_all_recordings(limit=limit)
        
        logger.info(f"Sincronización masiva completada: {stats}")
        
        return {
            'success': True,
            **stats
        }
        
    except Exception as e:
        error_msg = f"Error en sincronización masiva: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Reintentar si es un error temporal
        if self.request.retries < self.max_retries:
            logger.warning(f"Reintentando sincronización masiva (intento {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=300)  # 5 minutos entre reintentos
        
        # Si se agotaron los reintentos, retornar error
        return {
            'success': False,
            'processed': 0,
            'found': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error': error_msg
        }
