"""
Tests unitarios para GoogleDriveClient.

Pruebas de:
- Inicialización del cliente
- Búsqueda de grabaciones
- Obtención de metadatos
- Manejo de errores
"""

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from datetime import datetime, timedelta
from django.utils import timezone

from integrations.drive_client import GoogleDriveClient
from integrations.config import validate_google_credentials


class GoogleDriveClientTestCase(TestCase):
    """Tests para GoogleDriveClient"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = GoogleDriveClient()
        self.mock_file = {
            'id': 'test_file_id_123',
            'name': 'Reunión de Google Meet - 2025-12-26T15:00:00Z.mp4',
            'mimeType': 'video/mp4',
            'createdTime': '2025-12-26T15:00:00.000Z',
            'modifiedTime': '2025-12-26T16:00:00.000Z',
            'size': '524288000',
            'webViewLink': 'https://drive.google.com/file/d/test_file_id_123/view',
            'properties': {
                'event_id': 'test_event_123'
            }
        }

    @patch('integrations.drive_client.validate_google_credentials')
    @patch('integrations.drive_client.service_account.Credentials.from_service_account_file')
    def test_init_with_valid_credentials(self, mock_credentials, mock_validate):
        """Test de inicialización con credenciales válidas"""
        mock_validate.return_value = True
        mock_credentials.return_value = Mock()
        
        client = GoogleDriveClient()
        self.assertIsNotNone(client)
        mock_validate.assert_called_once()

    @patch('integrations.drive_client.validate_google_credentials')
    def test_init_without_credentials(self, mock_validate):
        """Test de inicialización sin credenciales"""
        mock_validate.return_value = False
        
        with self.assertRaises(Exception):
            GoogleDriveClient()

    @patch.object(GoogleDriveClient, '_build_service')
    def test_test_connection_success(self, mock_build_service):
        """Test de conexión exitosa"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        mock_list.execute.return_value = {
            'files': [self.mock_file],
            'nextPageToken': None
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        result = self.client.test_connection()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['files_found'], 1)

    @patch.object(GoogleDriveClient, '_build_service')
    def test_test_connection_error(self, mock_build_service):
        """Test de conexión con error"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        mock_list.execute.side_effect = Exception("API Error")
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        result = self.client.test_connection()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @patch.object(GoogleDriveClient, '_build_service')
    def test_search_recordings_by_date_range(self, mock_build_service):
        """Test de búsqueda de grabaciones por rango de fechas"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        start_time = timezone.now() - timedelta(days=1)
        end_time = timezone.now()
        
        mock_list.execute.return_value = {
            'files': [self.mock_file],
            'nextPageToken': None
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        results = self.client.search_recordings_by_date_range(start_time, end_time)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 'test_file_id_123')
        mock_files.list.assert_called_once()

    @patch.object(GoogleDriveClient, '_build_service')
    def test_search_recording_by_event_id(self, mock_build_service):
        """Test de búsqueda de grabación por event_id"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        mock_list.execute.return_value = {
            'files': [self.mock_file],
            'nextPageToken': None
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        result = self.client.search_recording_by_event_id('test_event_123')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test_file_id_123')

    @patch.object(GoogleDriveClient, '_build_service')
    def test_search_recording_by_event_id_not_found(self, mock_build_service):
        """Test de búsqueda de grabación por event_id no encontrada"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        mock_list.execute.return_value = {
            'files': [],
            'nextPageToken': None
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        result = self.client.search_recording_by_event_id('non_existent_event')
        
        self.assertIsNone(result)

    @patch.object(GoogleDriveClient, '_build_service')
    def test_get_file_metadata(self, mock_build_service):
        """Test de obtención de metadatos de archivo"""
        mock_service = Mock()
        mock_files = Mock()
        mock_get = Mock()
        
        mock_get.execute.return_value = self.mock_file
        mock_files.get.return_value = mock_get
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        result = self.client.get_file_metadata('test_file_id_123')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test_file_id_123')
        self.assertEqual(result['name'], self.mock_file['name'])

    @patch.object(GoogleDriveClient, '_build_service')
    def test_get_file_metadata_not_found(self, mock_build_service):
        """Test de obtención de metadatos de archivo no encontrado"""
        from googleapiclient.errors import HttpError
        
        mock_service = Mock()
        mock_files = Mock()
        mock_get = Mock()
        
        error_response = Mock()
        error_response.status = 404
        mock_get.execute.side_effect = HttpError(error_response, b'Not Found')
        mock_files.get.return_value = mock_get
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        result = self.client.get_file_metadata('non_existent_file_id')
        
        self.assertIsNone(result)

    def test_get_file_url(self):
        """Test de generación de URL de archivo"""
        file_id = 'test_file_id_123'
        expected_url = f'https://drive.google.com/file/d/{file_id}/view'
        
        url = self.client.get_file_url(file_id)
        
        self.assertEqual(url, expected_url)

    @patch.object(GoogleDriveClient, '_build_service')
    def test_find_meet_recordings_folder(self, mock_build_service):
        """Test de búsqueda de carpeta 'Meet Recordings'"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        folder_file = {
            'id': 'folder_id_123',
            'name': 'Meet Recordings',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        mock_list.execute.return_value = {
            'files': [folder_file],
            'nextPageToken': None
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        folder_id = self.client.find_meet_recordings_folder()
        
        self.assertEqual(folder_id, 'folder_id_123')

    @patch.object(GoogleDriveClient, '_build_service')
    def test_list_recordings_in_folder(self, mock_build_service):
        """Test de listado de grabaciones en carpeta"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        mock_list.execute.return_value = {
            'files': [self.mock_file],
            'nextPageToken': None
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        results = self.client.list_recordings_in_folder('folder_id_123')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 'test_file_id_123')

    @patch.object(GoogleDriveClient, '_build_service')
    def test_list_recordings(self, mock_build_service):
        """Test de listado genérico de grabaciones"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        
        mock_list.execute.return_value = {
            'files': [self.mock_file],
            'nextPageToken': None
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files
        mock_build_service.return_value = mock_service
        
        self.client._service = mock_service
        
        results = self.client.list_recordings(limit=10)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 'test_file_id_123')

