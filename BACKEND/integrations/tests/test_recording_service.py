"""
Tests unitarios para RecordingSyncService.

Pruebas de:
- Sincronización individual de grabaciones
- Sincronización masiva
- Casos edge (sin grabación, múltiples archivos, etc.)
"""

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from datetime import datetime, timedelta
from django.utils import timezone

from integrations.recording_service import RecordingSyncService
from meetings.models import Meeting, MeetingRecording
from accounts.models import User


class RecordingSyncServiceTestCase(TestCase):
    """Tests para RecordingSyncService"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.service = RecordingSyncService()
        
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear reunión de prueba
        self.meeting = Meeting.objects.create(
            organizer=self.user,
            google_event_id='test_event_123',
            meet_link='https://meet.google.com/test',
            scheduled_start=timezone.now() - timedelta(days=1),
            scheduled_end=timezone.now() - timedelta(days=1) + timedelta(hours=1),
            status='FINISHED'
        )
        
        self.mock_drive_file = {
            'id': 'drive_file_123',
            'name': 'Reunión de Google Meet - 2025-12-26T15:00:00Z.mp4',
            'mimeType': 'video/mp4',
            'createdTime': '2025-12-26T15:00:00.000Z',
            'modifiedTime': '2025-12-26T16:00:00.000Z',
            'size': '524288000',
            'webViewLink': 'https://drive.google.com/file/d/drive_file_123/view',
            'properties': {
                'event_id': 'test_event_123'
            }
        }

    @patch.object(RecordingSyncService, '_find_recording_in_drive')
    def test_sync_meeting_recording_success(self, mock_find):
        """Test de sincronización exitosa de grabación"""
        mock_find.return_value = self.mock_drive_file
        
        result = self.service.sync_meeting_recording(self.meeting)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MeetingRecording)
        self.assertEqual(result.drive_file_id, 'drive_file_123')
        self.assertEqual(result.meeting, self.meeting)
        mock_find.assert_called_once_with(self.meeting)

    @patch.object(RecordingSyncService, '_find_recording_in_drive')
    def test_sync_meeting_recording_not_found(self, mock_find):
        """Test de sincronización cuando no se encuentra grabación"""
        mock_find.return_value = None
        
        result = self.service.sync_meeting_recording(self.meeting)
        
        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.meeting)

    @patch.object(RecordingSyncService, '_find_recording_in_drive')
    def test_sync_meeting_recording_updates_existing(self, mock_find):
        """Test de actualización de grabación existente"""
        # Crear grabación existente
        existing_recording = MeetingRecording.objects.create(
            meeting=self.meeting,
            drive_file_id='old_file_id',
            drive_file_name='Old Name',
            drive_file_url='https://drive.google.com/file/d/old_file_id/view'
        )
        
        mock_find.return_value = self.mock_drive_file
        
        result = self.service.sync_meeting_recording(self.meeting)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.id, existing_recording.id)  # Mismo registro
        self.assertEqual(result.drive_file_id, 'drive_file_123')  # Actualizado
        self.assertEqual(result.drive_file_name, self.mock_drive_file['name'])

    @patch.object(RecordingSyncService, '_find_recording_in_drive')
    def test_sync_meeting_recording_without_scheduled_start(self, mock_find):
        """Test de sincronización con reunión sin scheduled_start"""
        self.meeting.scheduled_start = None
        self.meeting.save()
        
        result = self.service.sync_meeting_recording(self.meeting)
        
        self.assertIsNone(result)
        mock_find.assert_not_called()

    @patch.object(RecordingSyncService, '_find_recording_in_drive')
    def test_sync_all_recordings(self, mock_find):
        """Test de sincronización masiva"""
        # Crear múltiples reuniones sin grabación
        meeting2 = Meeting.objects.create(
            organizer=self.user,
            google_event_id='test_event_456',
            meet_link='https://meet.google.com/test2',
            scheduled_start=timezone.now() - timedelta(days=2),
            scheduled_end=timezone.now() - timedelta(days=2) + timedelta(hours=1),
            status='FINISHED'
        )
        
        mock_find.side_effect = [self.mock_drive_file, None]
        
        result = self.service.sync_all_recordings(limit=10)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['total_processed'], 2)
        self.assertEqual(result['synced'], 1)
        self.assertEqual(result['not_found'], 1)
        self.assertEqual(mock_find.call_count, 2)

    @patch.object(RecordingSyncService, '_find_recording_in_drive')
    def test_sync_all_recordings_with_limit(self, mock_find):
        """Test de sincronización masiva con límite"""
        # Crear múltiples reuniones
        for i in range(5):
            Meeting.objects.create(
                organizer=self.user,
                google_event_id=f'test_event_{i}',
                meet_link=f'https://meet.google.com/test{i}',
                scheduled_start=timezone.now() - timedelta(days=i+1),
                scheduled_end=timezone.now() - timedelta(days=i+1) + timedelta(hours=1),
                status='FINISHED'
            )
        
        mock_find.return_value = None
        
        result = self.service.sync_all_recordings(limit=3)
        
        self.assertEqual(result['total_processed'], 3)
        self.assertEqual(mock_find.call_count, 3)

    @patch.object(RecordingSyncService, '_find_recording_in_drive')
    def test_sync_all_recordings_skips_with_recording(self, mock_find):
        """Test de que sync_all omite reuniones con grabación existente"""
        # Crear grabación para la reunión
        MeetingRecording.objects.create(
            meeting=self.meeting,
            drive_file_id='existing_file',
            drive_file_name='Existing',
            drive_file_url='https://drive.google.com/file/d/existing_file/view'
        )
        
        result = self.service.sync_all_recordings()
        
        self.assertEqual(result['total_processed'], 0)
        self.assertEqual(result['skipped'], 1)
        mock_find.assert_not_called()

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_find_recording_in_drive_by_event_id(self, mock_drive_client_class):
        """Test de búsqueda de grabación por event_id"""
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = self.mock_drive_file
        
        service = RecordingSyncService()
        result = service._find_recording_in_drive(self.meeting)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'drive_file_123')
        mock_drive_client.search_recording_by_event_id.assert_called_once_with('test_event_123')

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_find_recording_in_drive_by_date_range(self, mock_drive_client_class):
        """Test de búsqueda de grabación por rango de fechas"""
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = None
        mock_drive_client.search_recordings_by_date_range.return_value = [self.mock_drive_file]
        
        service = RecordingSyncService()
        result = service._find_recording_in_drive(self.meeting)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'drive_file_123')
        mock_drive_client.search_recordings_by_date_range.assert_called_once()

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_find_recording_in_drive_multiple_files(self, mock_drive_client_class):
        """Test de búsqueda cuando hay múltiples archivos candidatos"""
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = None
        
        # Múltiples archivos en el rango de fechas
        file1 = {**self.mock_drive_file, 'id': 'file1', 'createdTime': '2025-12-26T15:00:00.000Z'}
        file2 = {**self.mock_drive_file, 'id': 'file2', 'createdTime': '2025-12-26T15:30:00.000Z'}
        
        mock_drive_client.search_recordings_by_date_range.return_value = [file1, file2]
        
        service = RecordingSyncService()
        result = service._find_recording_in_drive(self.meeting)
        
        # Debe seleccionar el más cercano a la fecha de la reunión
        self.assertIsNotNone(result)
        self.assertIn(result['id'], ['file1', 'file2'])

    def test_create_or_update_recording(self):
        """Test de creación/actualización de grabación"""
        result = self.service._create_or_update_recording(self.meeting, self.mock_drive_file)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MeetingRecording)
        self.assertEqual(result.drive_file_id, 'drive_file_123')
        self.assertEqual(result.meeting, self.meeting)
        self.assertIsNotNone(result.drive_file_url)

    def test_extract_duration_from_metadata(self):
        """Test de extracción de duración de metadatos"""
        metadata_with_duration = {
            **self.mock_drive_file,
            'videoMediaMetadata': {
                'durationMillis': '3600000'  # 1 hora en milisegundos
            }
        }
        
        duration = self.service._extract_duration_from_metadata(metadata_with_duration)
        
        self.assertEqual(duration, 3600)  # 1 hora en segundos

    def test_extract_duration_from_metadata_no_duration(self):
        """Test de extracción de duración cuando no está disponible"""
        duration = self.service._extract_duration_from_metadata(self.mock_drive_file)
        
        self.assertIsNone(duration)

    def test_extract_available_date(self):
        """Test de extracción de fecha de disponibilidad"""
        available_date = self.service._extract_available_date(self.mock_drive_file)
        
        self.assertIsNotNone(available_date)
        self.assertIsInstance(available_date, datetime)

    def test_extract_available_date_no_date(self):
        """Test de extracción de fecha cuando no está disponible"""
        file_without_date = {**self.mock_drive_file}
        del file_without_date['createdTime']
        
        available_date = self.service._extract_available_date(file_without_date)
        
        self.assertIsNone(available_date)

