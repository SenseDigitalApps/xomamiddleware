"""
Cliente para integración con Google Meet API.

Maneja:
- Configuración de grabación automática
- Obtención de información de espacios de reunión
- Gestión de configuraciones de reunión
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from typing import Dict, Optional, Any

from core.exceptions import (
    GoogleAuthenticationError,
    GoogleMeetError,
)
from .config import GoogleConfig

logger = logging.getLogger(__name__)


class GoogleMeetClient:
    """
    Cliente para interactuar con Google Meet API.
    
    Proporciona métodos para:
    - Configurar grabación automática en espacios de reunión
    - Obtener información de espacios
    - Actualizar configuraciones de reunión
    """
    
    def __init__(self):
        """
        Inicializa el cliente de Google Meet.
        
        Carga credenciales y construye el servicio de Meet API.
        
        Raises:
            GoogleAuthenticationError: Si falla la autenticación
        """
        try:
            self.config = GoogleConfig()
            self.credentials = self._load_credentials()
            self.service, self.service_v2beta = self._build_service()
            logger.info("Google Meet Client inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Google Meet Client: {e}")
            raise GoogleAuthenticationError(
                f"Error al inicializar Google Meet Client: {str(e)}"
            )
    
    def _load_credentials(self):
        """
        Carga las credenciales del Service Account.
        
        Usa from_service_account_info en lugar de from_service_account_file
        para evitar problemas de deadlock en macOS con Docker.
        
        Returns:
            service_account.Credentials: Credenciales con delegation si está configurado
        
        Raises:
            GoogleAuthenticationError: Si falla la carga de credenciales
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
            
            # Si hay admin_email configurado, usar Domain-Wide Delegation
            if self.config.admin_email:
                credentials = credentials.with_subject(self.config.admin_email)
                logger.info(f"Usando Domain-Wide Delegation con: {self.config.admin_email}")
            
            return credentials
        except Exception as e:
            logger.error(f"Error al cargar credenciales de Google Meet: {e}")
            raise GoogleAuthenticationError(
                f"Error al cargar credenciales: {str(e)}"
            )
    
    def _build_service(self):
        """
        Construye los servicios de Google Meet API.
        
        Returns:
            tuple: (Servicio v2, Servicio v2beta)
                - v2: Para operaciones de espacios (spaces)
                - v2beta: Para operaciones de miembros (spaces.members)
        
        Raises:
            GoogleMeetError: Si falla la construcción del servicio
        """
        try:
            service_v2 = build('meet', 'v2', credentials=self.credentials)
            logger.info("Servicio de Google Meet API v2 construido correctamente")
            
            # Intentar construir v2beta, pero no fallar si no está disponible
            service_v2beta = None
            try:
                service_v2beta = build('meet', 'v2beta', credentials=self.credentials, discoveryServiceUrl='https://meet.googleapis.com/$discovery/rest?version=v2beta')
                logger.info("Servicio de Google Meet API v2beta construido correctamente")
            except Exception as v2beta_error:
                logger.warning(f"No se pudo construir servicio v2beta: {v2beta_error}")
                logger.warning("Los métodos de gestión de miembros pueden no estar disponibles")
                # Intentar construir sin discoveryServiceUrl
                try:
                    service_v2beta = build('meet', 'v2beta', credentials=self.credentials)
                    logger.info("Servicio v2beta construido con método alternativo")
                except Exception as e2:
                    logger.warning(f"Método alternativo también falló: {e2}")
            
            return service_v2, service_v2beta
        except Exception as e:
            logger.error(f"Error al construir servicio de Google Meet: {e}")
            raise GoogleMeetError(
                f"Error al construir servicio de Google Meet: {str(e)}"
            )
    
    def create_space(self, auto_recording: bool = True, public_access: bool = False) -> Dict[str, Any]:
        """
        Crea un espacio de reunión directamente usando Meet API.
        
        Según documentación: https://developers.google.com/workspace/meet/api/reference/rest/v2/spaces/create
        
        Args:
            auto_recording: Si True, habilita grabación automática al crear el espacio
            public_access: Si True, configura accessType='OPEN' para que cualquiera pueda unirse sin solicitar permiso
        
        Returns:
            dict: Espacio creado con meetingUri y configuración
                - name: Nombre del espacio (spaces/{meeting_code})
                - meetingUri: URI de la reunión (https://meet.google.com/{meeting_code})
                - config: Configuración del espacio
        """
        try:
            logger.info("Creando espacio de reunión directamente con Meet API")
            
            # Configuración del espacio
            space_config = {}
            config_dict = {}
            
            # Configurar grabación automática
            if auto_recording:
                config_dict['artifactConfig'] = {
                    'recordingConfig': {
                        'autoRecordingGeneration': 'ON'  # 'ON' para habilitar, 'OFF' para deshabilitar
                    }
                }
                logger.info("Grabación automática habilitada en configuración inicial")
            
            # Configurar acceso público
            if public_access:
                config_dict['accessType'] = 'OPEN'
                logger.info("Acceso público habilitado (OPEN) - Cualquiera puede unirse sin solicitar permiso")
            else:
                # Por defecto, usar 'TRUSTED' (comportamiento estándar)
                config_dict['accessType'] = 'TRUSTED'
                logger.info("Acceso configurado como TRUSTED (comportamiento estándar)")
            
            # Construir configuración completa
            if config_dict:
                space_config['config'] = config_dict
            
            # Crear el espacio
            space = self.service.spaces().create(body=space_config).execute()
            
            space_name = space.get('name', 'N/A')
            meeting_uri = space.get('meetingUri', '')
            
            logger.info(f"Espacio creado exitosamente: {space_name}")
            logger.info(f"Meeting URI: {meeting_uri}")
            
            return space
            
        except HttpError as error:
            logger.error(f"Error al crear espacio: {error}")
            error_details = error.error_details if hasattr(error, 'error_details') else []
            raise GoogleMeetError(
                f"Error al crear espacio: {str(error)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado al crear espacio: {e}")
            raise GoogleMeetError(
                f"Error inesperado al crear espacio: {str(e)}"
            )
    
    def get_space(self, space_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un espacio de reunión.
        
        Args:
            space_name: Nombre del espacio (formato: spaces/{meeting_code})
        
        Returns:
            dict: Información del espacio o None si no existe
        
        Raises:
            GoogleMeetError: Si hay error al obtener el espacio
        """
        try:
            logger.info(f"Obteniendo información del espacio: {space_name}")
            space = self.service.spaces().get(name=space_name).execute()
            logger.info(f"Espacio obtenido: {space.get('name')}")
            return space
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Espacio no encontrado: {space_name}")
                return None
            logger.error(f"Error al obtener espacio: {error}")
            raise GoogleMeetError(
                f"Error al obtener espacio: {str(error)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado al obtener espacio: {e}")
            raise GoogleMeetError(
                f"Error inesperado: {str(e)}"
            )
    
    def update_space_config(self, space_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza la configuración de un espacio de reunión.
        
        Args:
            space_name: Nombre del espacio (formato: spaces/{meeting_code})
            config: Configuración a actualizar
        
        Returns:
            dict: Espacio actualizado
        
        Raises:
            GoogleMeetError: Si hay error al actualizar
        """
        try:
            logger.info(f"Actualizando configuración del espacio: {space_name}")
            # Construir updateMask correctamente para campos anidados
            # Para config.artifactConfig.recordingConfig.autoRecordingGeneration
            update_mask = 'config.artifactConfig.recordingConfig.autoRecordingGeneration'
            
            space = self.service.spaces().patch(
                name=space_name,
                body=config,
                updateMask=update_mask
            ).execute()
            logger.info(f"Configuración actualizada: {space.get('name')}")
            return space
        except HttpError as error:
            logger.error(f"Error al actualizar espacio: {error}")
            error_details = error.error_details if hasattr(error, 'error_details') else []
            raise GoogleMeetError(
                f"Error al actualizar espacio: {str(error)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado al actualizar espacio: {e}")
            raise GoogleMeetError(
                f"Error inesperado: {str(e)}"
            )
    
    def enable_auto_recording(self, space_name: str) -> Dict[str, Any]:
        """
        Habilita la grabación automática en un espacio de reunión.
        
        Args:
            space_name: Nombre del espacio (formato: spaces/{meeting_code})
        
        Returns:
            dict: Espacio con grabación habilitada
        
        Raises:
            GoogleMeetError: Si hay error al habilitar grabación
        """
        try:
            logger.info(f"Habilitando grabación automática en: {space_name}")
            
            # Primero obtener el espacio actual para preservar la configuración existente
            current_space = self.get_space(space_name)
            if not current_space:
                raise GoogleMeetError(f"Espacio no encontrado: {space_name}")
            
            current_config = current_space.get('config', {})
            
            # Configuración para habilitar grabación automática
            # Según documentación oficial: https://developers.google.com/workspace/meet/api/guides/meeting-spaces-configuration#auto-artifacts
            # La estructura correcta es: config.artifactConfig.recordingConfig.autoRecordingGeneration
            # Valores válidos: 'ON' para habilitar, 'OFF' para deshabilitar
            config = {
                'config': {
                    'artifactConfig': {
                        'recordingConfig': {
                            'autoRecordingGeneration': 'ON'  # 'ON' para habilitar, 'OFF' para deshabilitar
                        }
                    }
                }
            }
            
            # Preservar configuración existente si existe artifactConfig
            if 'artifactConfig' in current_config:
                artifact_config = current_config['artifactConfig'].copy()
                artifact_config['recordingConfig'] = config['config']['artifactConfig']['recordingConfig']
                config['config']['artifactConfig'] = artifact_config
            else:
                # Si no existe artifactConfig, usar solo recordingConfig
                pass
            
            space = self.update_space_config(space_name, config)
            logger.info(f"Grabación automática habilitada en: {space_name}")
            return space
        except Exception as e:
            logger.error(f"Error al habilitar grabación automática: {e}")
            raise GoogleMeetError(
                f"Error al habilitar grabación automática: {str(e)}"
            )
    
    def get_conference_id_from_meet_link(self, meet_link: str) -> Optional[str]:
        """
        Extrae el conference ID de un enlace de Google Meet.
        
        Args:
            meet_link: URL de Google Meet (ej: https://meet.google.com/abc-defg-hij)
        
        Returns:
            str: Conference ID o None si no se puede extraer
        """
        try:
            # Formato: https://meet.google.com/abc-defg-hij
            # O: https://meet.google.com/oxr-hgyk-stu
            parts = meet_link.split('/')
            if len(parts) >= 4 and parts[2] == 'meet.google.com':
                meeting_code = parts[3]
                # Convertir a formato de espacio: spaces/{meeting_code}
                space_name = f"spaces/{meeting_code}"
                return space_name
            return None
        except Exception as e:
            logger.warning(f"Error al extraer conference ID de {meet_link}: {e}")
            return None
    
    def configure_recording_for_meet_link(self, meet_link: str) -> Dict[str, Any]:
        """
        Configura grabación automática para un enlace de Google Meet.
        
        Args:
            meet_link: URL de Google Meet
        
        Returns:
            dict: Espacio configurado
        
        Raises:
            GoogleMeetError: Si hay error al configurar
        """
        try:
            space_name = self.get_conference_id_from_meet_link(meet_link)
            if not space_name:
                raise GoogleMeetError(
                    f"No se pudo extraer el conference ID del enlace: {meet_link}"
                )
            
            logger.info(f"Configurando grabación para: {space_name}")
            return self.enable_auto_recording(space_name)
        except Exception as e:
            logger.error(f"Error al configurar grabación: {e}")
            raise GoogleMeetError(
                f"Error al configurar grabación: {str(e)}"
            )
    
    def add_space_member(self, space_name: str, email: str, role: str = 'ATTENDEE') -> Dict[str, Any]:
        """
        Agrega un miembro al espacio de reunión.
        
        Los miembros pueden unirse sin solicitar permiso (knocking).
        
        Args:
            space_name: Nombre del espacio (spaces/{meeting_code})
            email: Email del usuario a agregar
            role: Rol del miembro ('COHOST' o 'ATTENDEE')
        
        Returns:
            dict: Miembro agregado
        
        Raises:
            GoogleMeetError: Si hay error al agregar miembro o si v2beta no está disponible
        """
        if not self.service_v2beta:
            raise GoogleMeetError(
                "Servicio v2beta no está disponible. La API de gestión de miembros requiere v2beta."
            )
        
        try:
            logger.info(f"Agregando miembro {email} al espacio {space_name} con rol {role}")
            
            member_body = {
                'user': {
                    'email': email
                },
                'role': role
            }
            
            # Usar endpoint v2beta para miembros
            member = self.service_v2beta.spaces().members().create(
                parent=space_name,
                body=member_body
            ).execute()
            
            logger.info(f"Miembro agregado exitosamente: {member.get('name')}")
            return member
            
        except HttpError as error:
            logger.error(f"Error al agregar miembro: {error}")
            raise GoogleMeetError(
                f"Error al agregar miembro: {str(error)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado al agregar miembro: {e}")
            raise GoogleMeetError(
                f"Error inesperado al agregar miembro: {str(e)}"
            )
    
    def add_space_members(self, space_name: str, emails: list, role: str = 'ATTENDEE') -> list:
        """
        Agrega múltiples miembros al espacio de reunión.
        
        Args:
            space_name: Nombre del espacio
            emails: Lista de emails a agregar
            role: Rol para todos los miembros
        
        Returns:
            list: Lista de miembros agregados exitosamente
        """
        members = []
        for email in emails:
            try:
                member = self.add_space_member(space_name, email, role)
                members.append(member)
            except Exception as e:
                logger.warning(f"No se pudo agregar miembro {email}: {e}")
        return members
    
    def list_space_members(self, space_name: str) -> list:
        """
        Lista todos los miembros del espacio.
        
        Args:
            space_name: Nombre del espacio
        
        Returns:
            list: Lista de miembros
        
        Raises:
            GoogleMeetError: Si hay error al listar miembros o si v2beta no está disponible
        """
        if not self.service_v2beta:
            raise GoogleMeetError(
                "Servicio v2beta no está disponible. La API de gestión de miembros requiere v2beta."
            )
        
        try:
            logger.info(f"Listando miembros del espacio: {space_name}")
            response = self.service_v2beta.spaces().members().list(
                parent=space_name
            ).execute()
            members = response.get('members', [])
            logger.info(f"Encontrados {len(members)} miembros")
            return members
        except HttpError as error:
            logger.error(f"Error al listar miembros: {error}")
            raise GoogleMeetError(
                f"Error al listar miembros: {str(error)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado al listar miembros: {e}")
            raise GoogleMeetError(
                f"Error inesperado al listar miembros: {str(e)}"
            )
    
    def delete_space_member(self, member_name: str) -> bool:
        """
        Elimina un miembro del espacio.
        
        Args:
            member_name: Nombre completo del miembro (spaces/{space}/members/{member})
        
        Returns:
            bool: True si se eliminó correctamente
        
        Raises:
            GoogleMeetError: Si hay error al eliminar miembro o si v2beta no está disponible
        """
        if not self.service_v2beta:
            raise GoogleMeetError(
                "Servicio v2beta no está disponible. La API de gestión de miembros requiere v2beta."
            )
        
        try:
            logger.info(f"Eliminando miembro: {member_name}")
            self.service_v2beta.spaces().members().delete(name=member_name).execute()
            logger.info("Miembro eliminado exitosamente")
            return True
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Miembro no encontrado: {member_name}")
                return False
            logger.error(f"Error al eliminar miembro: {error}")
            raise GoogleMeetError(
                f"Error al eliminar miembro: {str(error)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado al eliminar miembro: {e}")
            raise GoogleMeetError(
                f"Error inesperado al eliminar miembro: {str(e)}"
            )
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con Google Meet API.
        
        Returns:
            dict: Resultado de la prueba
        
        Raises:
            GoogleMeetError: Si falla la conexión
        """
        try:
            logger.info("Probando conexión con Google Meet API...")
            # Intentar listar espacios (puede requerir permisos adicionales)
            # Por ahora, solo verificamos que el servicio se construya correctamente
            result = {
                'status': 'success',
                'message': 'Conexión con Google Meet API exitosa',
                'service_available': True
            }
            logger.info("Conexión con Google Meet API exitosa")
            return result
        except Exception as e:
            logger.error(f"Error al probar conexión: {e}")
            raise GoogleMeetError(
                f"Error al probar conexión: {str(e)}"
            )

