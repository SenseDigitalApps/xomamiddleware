"""
Cliente para integración con Google Drive API.

Maneja:
- Autenticación con Service Account
- Búsqueda de archivos de grabación
- Obtención de metadatos de archivos
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from core.exceptions import (
    GoogleAuthenticationError,
    GoogleDriveError,
    GoogleAPIQuotaExceeded
)
from .config import GoogleConfig

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """
    Cliente para interactuar con Google Drive API.
    
    Proporciona métodos para:
    - Buscar archivos de grabación
    - Obtener metadatos de archivos
    - Generar URLs de acceso
    """
    
    def __init__(self):
        """
        Inicializa el cliente de Google Drive.
        
        Carga credenciales y construye el servicio de Drive API.
        
        Raises:
            GoogleAuthenticationError: Si falla la autenticación
        """
        try:
            self.config = GoogleConfig()
            self.credentials = self._load_credentials()
            self.service = self._build_service()
            logger.info("Google Drive Client inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Google Drive Client: {e}")
            raise GoogleAuthenticationError(
                f"No se pudo autenticar con Google Drive: {str(e)}"
            )
    
    def _load_credentials(self):
        """
        Carga credenciales del Service Account desde archivo JSON.
        
        Incluye scopes de Drive para acceso a archivos.
        Usa from_service_account_info en lugar de from_service_account_file
        para evitar problemas de deadlock en macOS con Docker.
        
        Returns:
            service_account.Credentials: Credenciales cargadas
        
        Raises:
            GoogleAuthenticationError: Si no se pueden cargar las credenciales
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
                scopes=self.config.all_scopes  # Incluye Calendar + Drive
            )
            
            # Delegar dominio si está configurado
            if self.config.admin_email:
                credentials = credentials.with_subject(self.config.admin_email)
                logger.info(f"Credentials delegadas a: {self.config.admin_email}")
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error al cargar credenciales: {e}")
            raise GoogleAuthenticationError(
                f"No se pudieron cargar las credenciales: {str(e)}"
            )
    
    def _build_service(self):
        """
        Construye el servicio de Google Drive API.
        
        Returns:
            Resource: Servicio de Drive API v3
        
        Raises:
            GoogleAuthenticationError: Si la API no está habilitada
        """
        try:
            return build('drive', 'v3', credentials=self.credentials)
        except Exception as e:
            error_msg = str(e)
            if 'not enabled' in error_msg.lower() or 'not found' in error_msg.lower():
                raise GoogleAuthenticationError(
                    "Google Drive API no está habilitada. "
                    "Habilítala en Google Cloud Console: "
                    "https://console.cloud.google.com/apis/library/drive.googleapis.com"
                )
            raise GoogleAuthenticationError(
                f"Error al construir servicio de Drive: {str(e)}"
            )
    
    def test_connection(self):
        """
        Prueba la conexión con Google Drive API.
        
        Intenta listar un archivo para verificar que:
        - La API está habilitada
        - Los scopes están configurados correctamente
        - Las credenciales funcionan
        
        Returns:
            dict: Información de la prueba
                - success (bool): Si la conexión fue exitosa
                - message (str): Mensaje descriptivo
                - error (str, optional): Mensaje de error si falla
        
        Raises:
            GoogleDriveError: Si hay error de permisos o configuración
        """
        try:
            # Intentar listar archivos (solo 1 para prueba)
            result = self.service.files().list(
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            files = result.get('files', [])
            
            return {
                'success': True,
                'message': 'Conexión a Google Drive exitosa',
                'files_count': len(files)
            }
            
        except HttpError as error:
            if error.resp.status == 403:
                error_str = str(error)
                
                # Verificar si es error de permisos (scopes)
                if 'insufficient' in error_str.lower() or 'permission' in error_str.lower():
                    raise GoogleDriveError(
                        "Permisos insuficientes para acceder a Google Drive.\n"
                        "Verifica que los siguientes scopes estén en Domain-Wide Delegation:\n"
                        "- https://www.googleapis.com/auth/drive.readonly\n"
                        "- https://www.googleapis.com/auth/drive.metadata.readonly"
                    )
                elif 'quota' in error_str.lower() or 'rate' in error_str.lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                else:
                    raise GoogleDriveError(f"Error de permisos en Google Drive: {error}")
            elif error.resp.status == 401:
                raise GoogleAuthenticationError("Credenciales de Google Drive inválidas o expiradas")
            else:
                raise GoogleDriveError(f"Error al conectar con Google Drive: {error}")
        except Exception as e:
            logger.error(f"Error inesperado al probar conexión: {e}")
            raise GoogleDriveError(f"Error inesperado: {str(e)}")
    
    def search_recordings_by_date_range(self, start_time: datetime, end_time: datetime, 
                                       limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca archivos de grabación (video/mp4) en un rango de fechas.
        
        Estrategia principal para encontrar grabaciones de Google Meet.
        Busca archivos de video creados entre start_time y end_time.
        
        Args:
            start_time (datetime): Fecha/hora de inicio del rango
            end_time (datetime): Fecha/hora de fin del rango
            limit (int): Límite de resultados (default: 50)
        
        Returns:
            List[Dict]: Lista de archivos encontrados con sus metadatos
        
        Raises:
            GoogleDriveError: Si hay error al buscar archivos
        """
        try:
            # Formatear fechas para query de Drive API (RFC 3339)
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Query: archivos de video creados en el rango de tiempo
            query = (
                f"mimeType='video/mp4' and "
                f"createdTime >= '{start_str}' and "
                f"createdTime <= '{end_str}' and "
                f"trashed=false"
            )
            
            logger.info(f"Buscando grabaciones entre {start_str} y {end_str}")
            
            result = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, "
                       "webViewLink, webContentLink, videoMediaMetadata, parents)",
                orderBy="createdTime desc"
            ).execute()
            
            files = result.get('files', [])
            logger.info(f"Encontrados {len(files)} archivos de video en el rango")
            
            return files
            
        except HttpError as error:
            if error.resp.status == 403:
                if 'quota' in str(error).lower() or 'rate' in str(error).lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                raise GoogleDriveError(f"Error de permisos al buscar grabaciones: {error}")
            elif error.resp.status == 401:
                raise GoogleAuthenticationError("Credenciales inválidas o expiradas")
            else:
                raise GoogleDriveError(f"Error al buscar grabaciones: {error}")
        except Exception as e:
            logger.error(f"Error inesperado al buscar grabaciones: {e}")
            raise GoogleDriveError(f"Error inesperado al buscar grabaciones: {str(e)}")
    
    def search_recording_by_event_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Intenta buscar grabación usando el google_event_id.
        
        Nota: Google Meet generalmente NO guarda el event_id en metadatos,
        pero intentamos buscar por:
        1. Properties del archivo
        2. Nombre del archivo
        3. Descripción
        
        Args:
            event_id (str): ID del evento de Google Calendar
        
        Returns:
            Dict: Información del archivo encontrado, o None si no se encuentra
        
        Raises:
            GoogleDriveError: Si hay error al buscar
        """
        try:
            # Estrategia 1: Buscar en properties (poco probable que funcione)
            try:
                query = f"properties has {{ key='event_id' and value='{event_id}' }}"
                result = self.service.files().list(
                    q=query,
                    pageSize=1,
                    fields="files(id, name, properties)"
                ).execute()
                
                files = result.get('files', [])
                if files:
                    logger.info(f"Grabación encontrada por event_id en properties: {event_id}")
                    return files[0]
            except Exception:
                pass  # Es normal que falle, no todos los archivos tienen properties
            
            # Estrategia 2: Buscar en nombre del archivo
            query = f"name contains '{event_id}' and mimeType='video/mp4' and trashed=false"
            result = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id, name, createdTime)"
            ).execute()
            
            files = result.get('files', [])
            if files:
                logger.info(f"Grabación encontrada por event_id en nombre: {event_id}")
                return files[0]
            
            logger.debug(f"No se encontró grabación por event_id: {event_id}")
            return None
            
        except HttpError as error:
            if error.resp.status == 403:
                if 'quota' in str(error).lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                # No es crítico si falla esta búsqueda
                logger.warning(f"Error al buscar por event_id (puede ser normal): {error}")
                return None
            else:
                logger.warning(f"Error al buscar por event_id: {error}")
                return None
        except Exception as e:
            logger.warning(f"Error inesperado al buscar por event_id: {e}")
            return None
    
    def search_recording_by_meeting_code(self, meeting_code: str) -> Optional[Dict[str, Any]]:
        """
        Busca grabación usando el código de Meet en el nombre del archivo.
        
        Las grabaciones de Google Meet se guardan con el formato:
        {meeting_code} (YYYY-MM-DD HH:MM GMT-5)
        
        Ejemplo: "ydo-jbsi-vhd (2026-01-06 08:15 GMT-5)"
        
        Args:
            meeting_code (str): Código de Meet (ej: "ydo-jbsi-vhd")
        
        Returns:
            Dict: Información del archivo encontrado, o None si no se encuentra
        
        Raises:
            GoogleDriveError: Si hay error al buscar
        """
        try:
            # Buscar archivos de video cuyo nombre contenga el código de Meet
            query = (
                f"name contains '{meeting_code}' and "
                f"mimeType='video/mp4' and "
                f"trashed=false"
            )
            
            logger.info(f"Buscando grabación por código de Meet: {meeting_code}")
            
            result = self.service.files().list(
                q=query,
                pageSize=10,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, "
                       "webViewLink, webContentLink, videoMediaMetadata, parents)",
                orderBy="createdTime desc"
            ).execute()
            
            files = result.get('files', [])
            
            if files:
                # Filtrar para asegurar que el código esté al inicio del nombre
                # (para evitar falsos positivos)
                matching_files = [
                    f for f in files 
                    if f.get('name', '').startswith(meeting_code)
                ]
                
                if matching_files:
                    # Retornar la más reciente
                    logger.info(f"Grabación encontrada por código de Meet: {meeting_code}")
                    return matching_files[0]
            
            logger.debug(f"No se encontró grabación por código de Meet: {meeting_code}")
            return None
            
        except HttpError as error:
            if error.resp.status == 403:
                if 'quota' in str(error).lower() or 'rate' in str(error).lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                raise GoogleDriveError(f"Error de permisos al buscar grabación: {error}")
            elif error.resp.status == 401:
                raise GoogleAuthenticationError("Credenciales inválidas o expiradas")
            else:
                raise GoogleDriveError(f"Error al buscar grabación: {error}")
        except Exception as e:
            logger.error(f"Error inesperado al buscar grabación por código: {e}")
            raise GoogleDriveError(f"Error inesperado: {str(e)}")
            
        except HttpError as error:
            if error.resp.status == 403:
                if 'quota' in str(error).lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                # No es crítico si falla esta búsqueda
                logger.warning(f"Error al buscar por event_id (puede ser normal): {error}")
                return None
            else:
                logger.warning(f"Error al buscar por event_id: {error}")
                return None
        except Exception as e:
            logger.warning(f"Error inesperado al buscar por event_id: {e}")
            return None
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Obtiene metadatos completos de un archivo en Google Drive.
        
        Args:
            file_id (str): ID del archivo en Google Drive
        
        Returns:
            Dict: Metadatos completos del archivo, incluyendo:
                - Información básica (id, name, mimeType, size)
                - Fechas (createdTime, modifiedTime)
                - Enlaces (webViewLink, webContentLink)
                - Metadatos de video (durationMillis, width, height)
                - Properties y appProperties
                - Parents (carpetas)
        
        Raises:
            GoogleDriveError: Si el archivo no existe o hay error de acceso
        """
        try:
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, "
                       "webViewLink, webContentLink, thumbnailLink, "
                       "parents, properties, appProperties, description, "
                       "videoMediaMetadata, owners, permissions"
            ).execute()
            
            logger.debug(f"Metadatos obtenidos para archivo: {file_id}")
            return file_metadata
            
        except HttpError as error:
            if error.resp.status == 404:
                raise GoogleDriveError(f"Archivo no encontrado: {file_id}")
            elif error.resp.status == 403:
                raise GoogleDriveError(f"Sin permisos para acceder al archivo: {file_id}")
            elif error.resp.status == 401:
                raise GoogleAuthenticationError("Credenciales inválidas o expiradas")
            else:
                raise GoogleDriveError(f"Error al obtener metadatos: {error}")
        except Exception as e:
            logger.error(f"Error inesperado al obtener metadatos: {e}")
            raise GoogleDriveError(f"Error inesperado: {str(e)}")
    
    def get_file_url(self, file_id: str) -> str:
        """
        Genera URL de acceso a un archivo en Google Drive.
        
        Args:
            file_id (str): ID del archivo en Google Drive
        
        Returns:
            str: URL para ver el archivo en Drive
                Formato: https://drive.google.com/file/d/{file_id}/view
        """
        return f"https://drive.google.com/file/d/{file_id}/view"
    
    def find_meet_recordings_folder(self) -> Optional[str]:
        """
        Busca la carpeta "Meet Recordings" en Google Drive.
        
        Returns:
            str: ID de la carpeta si se encuentra, None si no existe
        
        Raises:
            GoogleDriveError: Si hay error al buscar
        """
        try:
            # Buscar carpeta "Meet Recordings"
            query = (
                "mimeType='application/vnd.google-apps.folder' and "
                "(name='Meet Recordings' or name='Grabaciones de Meet') and "
                "trashed=false"
            )
            
            result = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            folders = result.get('files', [])
            if folders:
                folder_id = folders[0].get('id')
                logger.info(f"Carpeta 'Meet Recordings' encontrada: {folder_id}")
                return folder_id
            
            logger.debug("Carpeta 'Meet Recordings' no encontrada")
            return None
            
        except HttpError as error:
            if error.resp.status == 403:
                if 'quota' in str(error).lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                logger.warning(f"Error de permisos al buscar carpeta (puede ser normal): {error}")
                return None
            else:
                logger.warning(f"Error al buscar carpeta: {error}")
                return None
        except Exception as e:
            logger.warning(f"Error inesperado al buscar carpeta: {e}")
            return None
    
    def list_recordings_in_folder(self, folder_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Lista archivos de grabación (video/mp4) en una carpeta específica.
        
        Args:
            folder_id (str): ID de la carpeta en Google Drive
            limit (int): Límite de resultados (default: 100)
        
        Returns:
            List[Dict]: Lista de archivos de video encontrados
        
        Raises:
            GoogleDriveError: Si hay error al listar archivos
        """
        try:
            query = (
                f"'{folder_id}' in parents and "
                f"mimeType='video/mp4' and "
                f"trashed=false"
            )
            
            result = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, "
                       "webViewLink, videoMediaMetadata)",
                orderBy="createdTime desc"
            ).execute()
            
            files = result.get('files', [])
            logger.info(f"Encontrados {len(files)} archivos de video en la carpeta")
            
            return files
            
        except HttpError as error:
            if error.resp.status == 403:
                if 'quota' in str(error).lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                raise GoogleDriveError(f"Error de permisos al listar archivos: {error}")
            elif error.resp.status == 401:
                raise GoogleAuthenticationError("Credenciales inválidas o expiradas")
            else:
                raise GoogleDriveError(f"Error al listar archivos: {error}")
        except Exception as e:
            logger.error(f"Error inesperado al listar archivos: {e}")
            raise GoogleDriveError(f"Error inesperado: {str(e)}")
    
    def list_recordings(self, folder_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Lista archivos de grabación (video/mp4) en Google Drive.
        
        Si se proporciona folder_id, busca solo en esa carpeta.
        Si no, busca en todo el Drive.
        
        Args:
            folder_id (str, optional): ID de carpeta específica (opcional)
            limit (int): Límite de resultados (default: 100)
        
        Returns:
            List[Dict]: Lista de archivos de video encontrados
        
        Raises:
            GoogleDriveError: Si hay error al listar archivos
        """
        if folder_id:
            return self.list_recordings_in_folder(folder_id, limit)
        
        try:
            # Buscar todos los archivos de video
            query = "mimeType='video/mp4' and trashed=false"
            
            result = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, "
                       "webViewLink, videoMediaMetadata, parents)",
                orderBy="createdTime desc"
            ).execute()
            
            files = result.get('files', [])
            logger.info(f"Encontrados {len(files)} archivos de video en Drive")
            
            return files
            
        except HttpError as error:
            if error.resp.status == 403:
                if 'quota' in str(error).lower():
                    raise GoogleAPIQuotaExceeded("Cuota de Google Drive API excedida")
                raise GoogleDriveError(f"Error de permisos al listar grabaciones: {error}")
            elif error.resp.status == 401:
                raise GoogleAuthenticationError("Credenciales inválidas o expiradas")
            else:
                raise GoogleDriveError(f"Error al listar grabaciones: {error}")
        except Exception as e:
            logger.error(f"Error inesperado al listar grabaciones: {e}")
            raise GoogleDriveError(f"Error inesperado: {str(e)}")

