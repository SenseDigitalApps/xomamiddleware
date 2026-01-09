"""
Tests de integración end-to-end para sincronización de grabaciones.

Pruebas de:
- Flujo completo de sincronización
- Integración entre componentes
- Casos reales de uso
"""

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone

from meetings.models import Meeting, MeetingRecording
from accounts.models import User
from integrations.recording_service import RecordingSyncService


class RecordingSyncIntegrationTestCase(TransactionTestCase):
    """Tests de integración para sincronización de grabaciones"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        
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

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_full_sync_flow(self, mock_drive_client_class):
        """Test de flujo completo de sincronización"""
        # Mock del cliente de Drive
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = self.mock_drive_file
        
        # Ejecutar sincronización
        service = RecordingSyncService()
        recording = service.sync_meeting_recording(self.meeting)
        
        # Verificar resultados
        self.assertIsNotNone(recording)
        self.assertIsInstance(recording, MeetingRecording)
        self.assertEqual(recording.drive_file_id, 'drive_file_123')
        self.assertEqual(recording.meeting, self.meeting)
        
        # Verificar que se guardó en la base de datos
        saved_recording = MeetingRecording.objects.get(meeting=self.meeting)
        self.assertEqual(saved_recording.drive_file_id, 'drive_file_123')

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_sync_via_api_endpoint(self, mock_drive_client_class):
        """Test de sincronización a través del endpoint de API"""
        # Mock del cliente de Drive
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = self.mock_drive_file
        
        # Llamar al endpoint
        url = reverse('meeting-sync-recording', kwargs={'pk': self.meeting.id})
        
        with patch('meetings.views.sync_meeting_recording_task') as mock_task:
            mock_task.delay.return_value = Mock(id='test_task_id')
            
            response = self.client.post(url)
            
            # Verificar respuesta del endpoint
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertIn('task_id', response.data)
            
            # Simular ejecución de la tarea
            service = RecordingSyncService()
            recording = service.sync_meeting_recording(self.meeting)
            
            # Verificar que se creó la grabación
            self.assertIsNotNone(recording)
            self.assertEqual(recording.drive_file_id, 'drive_file_123')

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_sync_multiple_meetings(self, mock_drive_client_class):
        """Test de sincronización de múltiples reuniones"""
        # Crear múltiples reuniones
        meetings = []
        for i in range(3):
            meeting = Meeting.objects.create(
                organizer=self.user,
                google_event_id=f'test_event_{i}',
                meet_link=f'https://meet.google.com/test{i}',
                scheduled_start=timezone.now() - timedelta(days=i+1),
                scheduled_end=timezone.now() - timedelta(days=i+1) + timedelta(hours=1),
                status='FINISHED'
            )
            meetings.append(meeting)
        
        # Mock del cliente de Drive
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        
        # Configurar respuestas para cada reunión
        mock_drive_client.search_recording_by_event_id.side_effect = [
            {**self.mock_drive_file, 'id': f'file_{i}', 'properties': {'event_id': f'test_event_{i}'}}
            for i in range(3)
        ]
        
        # Sincronizar todas
        service = RecordingSyncService()
        result = service.sync_all_recordings(limit=10)
        
        # Verificar resultados
        self.assertEqual(result['total_processed'], 3)
        self.assertEqual(result['synced'], 3)
        
        # Verificar que se crearon todas las grabaciones
        recordings_count = MeetingRecording.objects.filter(
            meeting__in=meetings
        ).count()
        self.assertEqual(recordings_count, 3)

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_sync_with_date_range_fallback(self, mock_drive_client_class):
        """Test de sincronización usando búsqueda por rango de fechas como fallback"""
        # Mock del cliente de Drive
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        
        # No encontrar por event_id, pero sí por rango de fechas
        mock_drive_client.search_recording_by_event_id.return_value = None
        mock_drive_client.search_recordings_by_date_range.return_value = [self.mock_drive_file]
        
        # Ejecutar sincronización
        service = RecordingSyncService()
        recording = service.sync_meeting_recording(self.meeting)
        
        # Verificar que se encontró por rango de fechas
        self.assertIsNotNone(recording)
        self.assertEqual(recording.drive_file_id, 'drive_file_123')
        mock_drive_client.search_recordings_by_date_range.assert_called_once()

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_sync_updates_existing_recording(self, mock_drive_client_class):
        """Test de actualización de grabación existente"""
        # Crear grabación existente
        existing_recording = MeetingRecording.objects.create(
            meeting=self.meeting,
            drive_file_id='old_file_id',
            drive_file_name='Old Name',
            drive_file_url='https://drive.google.com/file/d/old_file_id/view'
        )
        
        # Mock del cliente de Drive
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = self.mock_drive_file
        
        # Ejecutar sincronización
        service = RecordingSyncService()
        updated_recording = service.sync_meeting_recording(self.meeting)
        
        # Verificar que se actualizó el mismo registro
        self.assertEqual(updated_recording.id, existing_recording.id)
        self.assertEqual(updated_recording.drive_file_id, 'drive_file_123')
        self.assertEqual(updated_recording.drive_file_name, self.mock_drive_file['name'])
        
        # Verificar que solo hay un registro
        recordings_count = MeetingRecording.objects.filter(meeting=self.meeting).count()
        self.assertEqual(recordings_count, 1)

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_sync_handles_multiple_candidates(self, mock_drive_client_class):
        """Test de manejo de múltiples archivos candidatos"""
        # Mock del cliente de Drive
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = None
        
        # Múltiples archivos en el rango
        file1 = {
            **self.mock_drive_file,
            'id': 'file1',
            'createdTime': '2025-12-26T15:00:00.000Z',
            'name': 'Reunión de Google Meet - 2025-12-26T15:00:00Z.mp4'
        }
        file2 = {
            **self.mock_drive_file,
            'id': 'file2',
            'createdTime': '2025-12-26T15:30:00.000Z',
            'name': 'Reunión de Google Meet - 2025-12-26T15:30:00Z.mp4'
        }
        
        mock_drive_client.search_recordings_by_date_range.return_value = [file1, file2]
        
        # Ejecutar sincronización
        service = RecordingSyncService()
        recording = service.sync_meeting_recording(self.meeting)
        
        # Debe seleccionar uno de los archivos
        self.assertIsNotNone(recording)
        self.assertIn(recording.drive_file_id, ['file1', 'file2'])

    def test_get_recording_after_sync(self):
        """Test de obtención de grabación después de sincronización"""
        # Crear grabación
        recording = MeetingRecording.objects.create(
            meeting=self.meeting,
            drive_file_id='test_file_id',
            drive_file_name='Test Recording',
            drive_file_url='https://drive.google.com/file/d/test_file_id/view',
            duration_seconds=3600
        )
        
        # Obtener grabación vía API
        url = reverse('meeting-recording', kwargs={'pk': self.meeting.id})
        response = self.client.get(url)
        
        # Verificar respuesta
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], recording.id)
        self.assertEqual(response.data['drive_file_id'], 'test_file_id')
        self.assertEqual(response.data['drive_file_url'], recording.drive_file_url)

    @patch('integrations.recording_service.GoogleDriveClient')
    def test_sync_skips_meetings_with_recording(self, mock_drive_client_class):
        """Test de que sync_all omite reuniones con grabación existente"""
        # Crear grabación para la reunión
        MeetingRecording.objects.create(
            meeting=self.meeting,
            drive_file_id='existing_file',
            drive_file_name='Existing',
            drive_file_url='https://drive.google.com/file/d/existing_file/view'
        )
        
        # Crear otra reunión sin grabación
        meeting2 = Meeting.objects.create(
            organizer=self.user,
            google_event_id='test_event_456',
            meet_link='https://meet.google.com/test2',
            scheduled_start=timezone.now() - timedelta(days=2),
            scheduled_end=timezone.now() - timedelta(days=2) + timedelta(hours=1),
            status='FINISHED'
        )
        
        # Mock del cliente de Drive
        mock_drive_client = Mock()
        mock_drive_client_class.return_value = mock_drive_client
        mock_drive_client.search_recording_by_event_id.return_value = self.mock_drive_file
        
        # Ejecutar sincronización masiva
        service = RecordingSyncService()
        result = service.sync_all_recordings()
        
        # Verificar que solo procesó la reunión sin grabación
        self.assertEqual(result['total_processed'], 1)
        self.assertEqual(result['skipped'], 1)
        
        # Verificar que no se creó grabación duplicada
        recordings_count = MeetingRecording.objects.filter(meeting=self.meeting).count()
        self.assertEqual(recordings_count, 1)

