"""
Tests unitarios para tareas de Celery relacionadas con grabaciones.

Pruebas de:
- sync_meeting_recording_task
- sync_all_recordings_task
- Retry logic
- Manejo de errores
"""

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from datetime import datetime, timedelta
from django.utils import timezone
from celery import current_app

from meetings.tasks import sync_meeting_recording_task, sync_all_recordings_task
from meetings.models import Meeting, MeetingRecording
from accounts.models import User


class RecordingTasksTestCase(TestCase):
    """Tests para tareas de Celery de grabaciones"""

    def setUp(self):
        """Configuración inicial para cada test"""
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

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_meeting_recording_task_success(self, mock_service_class):
        """Test de tarea de sincronización exitosa"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_recording = Mock()
        mock_recording.id = 1
        mock_recording.drive_file_id = 'test_file_id'
        mock_service.sync_meeting_recording.return_value = mock_recording
        
        result = sync_meeting_recording_task(self.meeting.id)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['meeting_id'], self.meeting.id)
        self.assertIsNotNone(result['recording_id'])
        mock_service.sync_meeting_recording.assert_called_once_with(self.meeting)

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_meeting_recording_task_not_found(self, mock_service_class):
        """Test de tarea cuando no se encuentra grabación"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_meeting_recording.return_value = None
        
        result = sync_meeting_recording_task(self.meeting.id)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['meeting_id'], self.meeting.id)
        self.assertIsNone(result.get('recording_id'))
        self.assertEqual(result['status'], 'not_found')

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_meeting_recording_task_meeting_not_found(self, mock_service_class):
        """Test de tarea cuando la reunión no existe"""
        result = sync_meeting_recording_task(99999)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_meeting_recording_task_exception(self, mock_service_class):
        """Test de tarea con excepción"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_meeting_recording.side_effect = Exception("Test error")
        
        task_instance = Mock()
        task_instance.retry = Mock()
        
        with patch('meetings.tasks.sync_meeting_recording_task.retry', side_effect=Exception("Max retries")):
            result = sync_meeting_recording_task.apply(
                args=(self.meeting.id,),
                throw=True
            )
            
            # La tarea debe fallar después de los reintentos
            self.assertIsNotNone(result)

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_meeting_recording_task_retry(self, mock_service_class):
        """Test de reintento de tarea"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_meeting_recording.side_effect = Exception("Temporary error")
        
        task_instance = Mock()
        task_instance.retry = Mock()
        
        # Simular retry
        try:
            sync_meeting_recording_task.apply(
                args=(self.meeting.id,),
                throw=True
            )
        except Exception:
            pass  # Esperado después de max retries

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_all_recordings_task_success(self, mock_service_class):
        """Test de tarea de sincronización masiva exitosa"""
        # Crear múltiples reuniones sin grabación
        for i in range(3):
            Meeting.objects.create(
                organizer=self.user,
                google_event_id=f'test_event_{i}',
                meet_link=f'https://meet.google.com/test{i}',
                scheduled_start=timezone.now() - timedelta(days=i+1),
                scheduled_end=timezone.now() - timedelta(days=i+1) + timedelta(hours=1),
                status='FINISHED'
            )
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_all_recordings.return_value = {
            'total_processed': 3,
            'synced': 2,
            'not_found': 1,
            'errors': 0
        }
        
        result = sync_all_recordings_task(limit=10)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_processed'], 3)
        self.assertEqual(result['synced'], 2)
        self.assertEqual(result['not_found'], 1)

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_all_recordings_task_with_limit(self, mock_service_class):
        """Test de tarea de sincronización masiva con límite"""
        # Crear múltiples reuniones
        for i in range(10):
            Meeting.objects.create(
                organizer=self.user,
                google_event_id=f'test_event_{i}',
                meet_link=f'https://meet.google.com/test{i}',
                scheduled_start=timezone.now() - timedelta(days=i+1),
                scheduled_end=timezone.now() - timedelta(days=i+1) + timedelta(hours=1),
                status='FINISHED'
            )
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_all_recordings.return_value = {
            'total_processed': 5,
            'synced': 3,
            'not_found': 2,
            'errors': 0
        }
        
        result = sync_all_recordings_task(limit=5)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_processed'], 5)
        mock_service.sync_all_recordings.assert_called_once_with(limit=5)

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_all_recordings_task_no_limit(self, mock_service_class):
        """Test de tarea de sincronización masiva sin límite"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_all_recordings.return_value = {
            'total_processed': 0,
            'synced': 0,
            'not_found': 0,
            'errors': 0
        }
        
        result = sync_all_recordings_task(limit=None)
        
        self.assertTrue(result['success'])
        mock_service.sync_all_recordings.assert_called_once_with(limit=None)

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_all_recordings_task_exception(self, mock_service_class):
        """Test de tarea de sincronización masiva con excepción"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_all_recordings.side_effect = Exception("Test error")
        
        task_instance = Mock()
        task_instance.retry = Mock()
        
        with patch('meetings.tasks.sync_all_recordings_task.retry', side_effect=Exception("Max retries")):
            result = sync_all_recordings_task.apply(
                kwargs={'limit': 10},
                throw=True
            )
            
            # La tarea debe fallar después de los reintentos
            self.assertIsNotNone(result)

    @patch('meetings.tasks.RecordingSyncService')
    def test_sync_all_recordings_task_empty_result(self, mock_service_class):
        """Test de tarea cuando no hay reuniones para procesar"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.sync_all_recordings.return_value = {
            'total_processed': 0,
            'synced': 0,
            'not_found': 0,
            'skipped': 0,
            'errors': 0
        }
        
        result = sync_all_recordings_task()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_processed'], 0)

