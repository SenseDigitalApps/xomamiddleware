"""
Tests unitarios para endpoints de API de grabaciones.

Pruebas de:
- POST /api/v1/meetings/{id}/sync_recording/
- POST /api/v1/recordings/sync_all/
- GET /api/v1/meetings/{id}/recording/
"""

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone

from meetings.models import Meeting, MeetingRecording
from accounts.models import User


class RecordingViewsTestCase(TestCase):
    """Tests para endpoints de API de grabaciones"""

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

    def test_sync_recording_endpoint_success(self):
        """Test de endpoint de sincronización exitosa"""
        url = reverse('meeting-sync-recording', kwargs={'pk': self.meeting.id})
        
        with patch('meetings.views.sync_meeting_recording_task') as mock_task:
            mock_task.delay.return_value = Mock(id='test_task_id')
            
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertIn('task_id', response.data)
            self.assertEqual(response.data['meeting_id'], self.meeting.id)
            self.assertEqual(response.data['status'], 'pending')
            mock_task.delay.assert_called_once_with(self.meeting.id)

    def test_sync_recording_endpoint_meeting_not_found(self):
        """Test de endpoint cuando la reunión no existe"""
        url = reverse('meeting-sync-recording', kwargs={'pk': 99999})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sync_recording_endpoint_no_scheduled_start(self):
        """Test de endpoint cuando la reunión no tiene scheduled_start"""
        self.meeting.scheduled_start = None
        self.meeting.save()
        
        url = reverse('meeting-sync-recording', kwargs={'pk': self.meeting.id})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_sync_recording_endpoint_task_error(self):
        """Test de endpoint cuando hay error al encolar tarea"""
        url = reverse('meeting-sync-recording', kwargs={'pk': self.meeting.id})
        
        with patch('meetings.views.sync_meeting_recording_task') as mock_task:
            mock_task.delay.side_effect = Exception("Task error")
            
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('error', response.data)

    def test_sync_all_endpoint_success(self):
        """Test de endpoint de sincronización masiva exitosa"""
        url = reverse('recording-sync-all')
        
        with patch('meetings.views.sync_all_recordings_task') as mock_task:
            mock_task.delay.return_value = Mock(id='test_task_id')
            
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertIn('task_id', response.data)
            self.assertEqual(response.data['status'], 'pending')
            mock_task.delay.assert_called_once_with(limit=None)

    def test_sync_all_endpoint_with_limit_query_param(self):
        """Test de endpoint de sincronización masiva con límite en query param"""
        url = reverse('recording-sync-all')
        
        with patch('meetings.views.sync_all_recordings_task') as mock_task:
            mock_task.delay.return_value = Mock(id='test_task_id')
            
            response = self.client.post(f'{url}?limit=50')
            
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(response.data['limit'], 50)
            mock_task.delay.assert_called_once_with(limit=50)

    def test_sync_all_endpoint_with_limit_body(self):
        """Test de endpoint de sincronización masiva con límite en body"""
        url = reverse('recording-sync-all')
        
        with patch('meetings.views.sync_all_recordings_task') as mock_task:
            mock_task.delay.return_value = Mock(id='test_task_id')
            
            response = self.client.post(url, {'limit': 30}, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(response.data['limit'], 30)
            mock_task.delay.assert_called_once_with(limit=30)

    def test_sync_all_endpoint_invalid_limit(self):
        """Test de endpoint con límite inválido"""
        url = reverse('recording-sync-all')
        
        response = self.client.post(f'{url}?limit=invalid')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_sync_all_endpoint_negative_limit(self):
        """Test de endpoint con límite negativo"""
        url = reverse('recording-sync-all')
        
        response = self.client.post(f'{url}?limit=-5')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_sync_all_endpoint_task_error(self):
        """Test de endpoint cuando hay error al encolar tarea"""
        url = reverse('recording-sync-all')
        
        with patch('meetings.views.sync_all_recordings_task') as mock_task:
            mock_task.delay.side_effect = Exception("Task error")
            
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('error', response.data)

    def test_get_recording_endpoint_success(self):
        """Test de endpoint para obtener grabación existente"""
        recording = MeetingRecording.objects.create(
            meeting=self.meeting,
            drive_file_id='test_file_id',
            drive_file_name='Test Recording',
            drive_file_url='https://drive.google.com/file/d/test_file_id/view',
            duration_seconds=3600
        )
        
        url = reverse('meeting-recording', kwargs={'pk': self.meeting.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], recording.id)
        self.assertEqual(response.data['drive_file_id'], 'test_file_id')

    def test_get_recording_endpoint_not_found(self):
        """Test de endpoint cuando no hay grabación"""
        url = reverse('meeting-recording', kwargs={'pk': self.meeting.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('message', response.data)

    def test_get_recording_endpoint_meeting_not_found(self):
        """Test de endpoint cuando la reunión no existe"""
        url = reverse('meeting-recording', kwargs={'pk': 99999})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

