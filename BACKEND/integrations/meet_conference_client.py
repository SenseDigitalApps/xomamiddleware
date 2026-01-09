"""
Cliente para interactuar con Conference Records de Google Meet API.

Según documentación oficial:
https://developers.google.com/workspace/meet/api/guides/artifacts

Permite obtener información sobre grabaciones usando el recurso
conferenceRecords en lugar de solo buscar en Drive.
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from typing import Dict, Optional, Any, List

from core.exceptions import (
    GoogleAuthenticationError,
    GoogleMeetError,
)
from .config import GoogleConfig

logger = logging.getLogger(__name__)


class GoogleMeetConferenceClient:
    """
    Cliente para interactuar con Conference Records de Google Meet API.
    
    Proporciona métodos para:
    - Obtener información de grabaciones desde la API de Meet
    - Listar grabaciones de una conferencia
    - Obtener detalles de grabaciones específicas
    """
    
    def __init__(self):
        """
        Inicializa el cliente de Conference Records.
        
        Raises:
            GoogleAuthenticationError: Si falla la autenticación
        """
        try:
            self.config = GoogleConfig()
            self.credentials = self._load_credentials()
            self.service = self._build_service()
            logger.info("Google Meet Conference Client inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Google Meet Conference Client: {e}")
            raise GoogleAuthenticationError(
                f"Error al inicializar Google Meet Conference Client: {str(e)}"
            )
    
    def _load_credentials(self):
        """
        Carga las credenciales del Service Account.
        
        Usa from_service_account_info en lugar de from_service_account_file
        para evitar problemas de deadlock en macOS con Docker.
        """
        try:
            # Leer el archivo en memoria primero para evitar deadlock en macOS/Docker
            import json
            import time
            
            # Intentar leer con retry para manejar problemas temporales
            max_retries = 3
            retry_delay = 0.1
            
            for attempt in range(max_retries):
                try:
                    with open(self.config.service_account_file, 'r') as f:
                        creds_info = json.load(f)
                    break
                except OSError as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Intento {attempt + 1} falló al leer credenciales, reintentando...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise
            
            # Usar from_service_account_info en lugar de from_service_account_file
            credentials = service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=self.config.all_scopes
            )
            
            if self.config.admin_email:
                credentials = credentials.with_subject(self.config.admin_email)
                logger.info(f"Usando Domain-Wide Delegation con: {self.config.admin_email}")
            
            return credentials
        except Exception as e:
            logger.error(f"Error al cargar credenciales: {e}")
            raise GoogleAuthenticationError(
                f"Error al cargar credenciales: {str(e)}"
            )
    
    def _build_service(self):
        """Construye el servicio de Google Meet API v2."""
        try:
            service = build('meet', 'v2', credentials=self.credentials)
            logger.info("Servicio de Google Meet Conference API construido correctamente")
            return service
        except Exception as e:
            logger.error(f"Error al construir servicio: {e}")
            raise GoogleMeetError(
                f"Error al construir servicio de Google Meet: {str(e)}"
            )
    
    def get_conference_record(self, conference_record_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un conference record.
        
        Args:
            conference_record_name: Nombre del conference record
                Formato: conferenceRecords/{conference_record_id}
        
        Returns:
            dict: Información del conference record o None si no existe
        """
        try:
            logger.info(f"Obteniendo conference record: {conference_record_name}")
            record = self.service.conferenceRecords().get(
                name=conference_record_name
            ).execute()
            logger.info(f"Conference record obtenido: {record.get('name')}")
            return record
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Conference record no encontrado: {conference_record_name}")
                return None
            logger.error(f"Error al obtener conference record: {error}")
            raise GoogleMeetError(
                f"Error al obtener conference record: {str(error)}"
            )
    
    def list_recordings(self, conference_record_name: str, 
                       only_ready: bool = True) -> List[Dict[str, Any]]:
        """
        Lista todas las grabaciones de un conference record.
        
        Según documentación: https://developers.google.com/workspace/meet/api/guides/artifacts#recordings
        https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords.recordings
        
        Args:
            conference_record_name: Nombre del conference record
                Formato: conferenceRecords/{conference_record_id}
            only_ready: Si True, filtra solo grabaciones con state == FILE_GENERATED
        
        Returns:
            List[Dict]: Lista de grabaciones con información de Drive y estado
        """
        try:
            logger.info(f"Listando grabaciones para: {conference_record_name} (only_ready={only_ready})")
            
            recordings = []
            page_token = None
            
            while True:
                request_params = {
                    'parent': conference_record_name,
                    'pageSize': 100
                }
                
                if page_token:
                    request_params['pageToken'] = page_token
                
                response = self.service.conferenceRecords().recordings().list(
                    **request_params
                ).execute()
                
                all_recordings = response.get('recordings', [])
                
                if only_ready:
                    # Filtrar solo grabaciones listas (FILE_GENERATED)
                    ready_recordings = [
                        r for r in all_recordings 
                        if r.get('state') == 'FILE_GENERATED'
                    ]
                    recordings.extend(ready_recordings)
                    logger.debug(f"Filtradas {len(ready_recordings)} grabaciones listas de {len(all_recordings)} totales")
                else:
                    recordings.extend(all_recordings)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Encontradas {len(recordings)} grabaciones")
            return recordings
            
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Conference record no encontrado: {conference_record_name}")
                return []
            logger.error(f"Error al listar grabaciones: {error}")
            raise GoogleMeetError(
                f"Error al listar grabaciones: {str(error)}"
            )
    
    def get_recording(self, recording_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene detalles de una grabación específica.
        
        Args:
            recording_name: Nombre de la grabación
                Formato: conferenceRecords/{conference_record_id}/recordings/{recording_id}
        
        Returns:
            dict: Detalles de la grabación incluyendo DriveDestination y State
        """
        try:
            logger.info(f"Obteniendo grabación: {recording_name}")
            recording = self.service.conferenceRecords().recordings().get(
                name=recording_name
            ).execute()
            logger.info(f"Grabación obtenida: {recording.get('name')}")
            return recording
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Grabación no encontrada: {recording_name}")
                return None
            logger.error(f"Error al obtener grabación: {error}")
            raise GoogleMeetError(
                f"Error al obtener grabación: {str(error)}"
            )
    
    def find_conference_record_by_space(self, space_name: str) -> Optional[str]:
        """
        Intenta encontrar el conference record asociado a un espacio.
        
        Nota: Esto puede requerir buscar en conferenceRecords usando el meeting_code
        o esperar a que se genere el conference record después de la reunión.
        
        Args:
            space_name: Nombre del espacio (formato: spaces/{meeting_code})
        
        Returns:
            str: Nombre del conference record o None si no se encuentra
        """
        # La relación entre space y conference record no es directa
        # El conference record se crea cuando la reunión tiene lugar
        # Por ahora, retornamos None ya que necesitaríamos buscar
        # en conferenceRecords por meeting_code o esperar a que se genere
        logger.warning("find_conference_record_by_space no implementado completamente")
        return None

