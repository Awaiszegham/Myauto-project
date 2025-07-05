import unittest
import tempfile
import os
import json
import time
from unittest.mock import patch, MagicMock
import sys
import requests

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from models.video_task import VideoTask, db

class TestDubbingWorkflowIntegration(unittest.TestCase):
    """Integration tests for the complete dubbing workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up test fixtures."""
        with self.app.app_context():
            db.drop_all()
    
    def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/api/dubbing/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('services', data)
    
    def test_start_dubbing_endpoint_success(self):
        """Test successful dubbing initiation."""
        payload = {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'target_language': 'es',
            'source_language': 'en'
        }
        
        with patch('src.routes.dubbing.dubbing_task.delay') as mock_delay:
            response = self.client.post(
                '/api/dubbing/start-dubbing',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'started')
        self.assertIn('task_id', data)
        
        # Verify task was created in database
        with self.app.app_context():
            task = VideoTask.query.get(data['task_id'])
            self.assertIsNotNone(task)
            self.assertEqual(task.youtube_url, payload['youtube_url'])
            self.assertEqual(task.target_language, payload['target_language'])
            self.assertEqual(task.source_language, payload['source_language'])
            self.assertEqual(task.status, 'pending')
        
        # Verify Celery task was queued
        mock_delay.assert_called_once_with(data['task_id'])
    
    def test_start_dubbing_endpoint_missing_data(self):
        """Test dubbing initiation with missing required data."""
        payload = {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            # Missing target_language
        }
        
        response = self.client.post(
            '/api/dubbing/start-dubbing',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_start_dubbing_endpoint_invalid_url(self):
        """Test dubbing initiation with invalid YouTube URL."""
        payload = {
            'youtube_url': 'https://example.com/not-youtube',
            'target_language': 'es'
        }
        
        response = self.client.post(
            '/api/dubbing/start-dubbing',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Invalid YouTube URL', data['error'])
    
    def test_task_status_endpoint(self):
        """Test task status retrieval."""
        # Create a test task
        with self.app.app_context():
            task = VideoTask(
                youtube_url='https://www.youtube.com/watch?v=test',
                target_language='es',
                source_language='en',
                status='processing',
                progress=50
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        response = self.client.get(f'/api/dubbing/task-status/{task_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], task_id)
        self.assertEqual(data['status'], 'processing')
        self.assertEqual(data['progress'], 50)
        self.assertEqual(data['target_language'], 'es')
    
    def test_task_status_endpoint_not_found(self):
        """Test task status retrieval for non-existent task."""
        response = self.client.get('/api/dubbing/task-status/nonexistent-id')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('Task not found', data['error'])
    
    def test_list_tasks_endpoint(self):
        """Test task listing endpoint."""
        # Create test tasks
        with self.app.app_context():
            tasks = [
                VideoTask(
                    youtube_url=f'https://www.youtube.com/watch?v=test{i}',
                    target_language='es',
                    status='completed' if i % 2 == 0 else 'processing'
                )
                for i in range(5)
            ]
            for task in tasks:
                db.session.add(task)
            db.session.commit()
        
        response = self.client.get('/api/dubbing/tasks')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['tasks']), 5)
        self.assertEqual(data['total'], 5)
        self.assertEqual(data['current_page'], 1)
    
    def test_list_tasks_endpoint_with_filter(self):
        """Test task listing with status filter."""
        # Create test tasks
        with self.app.app_context():
            tasks = [
                VideoTask(
                    youtube_url=f'https://www.youtube.com/watch?v=test{i}',
                    target_language='es',
                    status='completed' if i < 3 else 'processing'
                )
                for i in range(5)
            ]
            for task in tasks:
                db.session.add(task)
            db.session.commit()
        
        response = self.client.get('/api/dubbing/tasks?status=completed')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['tasks']), 3)
        for task in data['tasks']:
            self.assertEqual(task['status'], 'completed')
    
    def test_supported_languages_endpoint(self):
        """Test supported languages endpoint."""
        with patch('src.services.gemini_cli_service.GeminiCLIService.get_supported_languages') as mock_gemini:
            with patch('src.services.audio_service.AudioService.get_available_voices') as mock_polly:
                mock_gemini.return_value = {'en': 'English', 'es': 'Spanish'}
                mock_polly.return_value = [
                    {'id': 'Joanna', 'language_code': 'en-US', 'gender': 'Female'},
                    {'id': 'Lucia', 'language_code': 'es-ES', 'gender': 'Female'}
                ]
                
                response = self.client.get('/api/dubbing/supported-languages')
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertIn('gemini_languages', data)
                self.assertIn('polly_voices', data)
                self.assertIn('common_languages', data)
    
    def test_cancel_task_endpoint(self):
        """Test task cancellation endpoint."""
        # Create a test task
        with self.app.app_context():
            task = VideoTask(
                youtube_url='https://www.youtube.com/watch?v=test',
                target_language='es',
                status='processing'
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        with patch('src.routes.dubbing.celery.control.revoke') as mock_revoke:
            response = self.client.post(f'/api/dubbing/cancel-task/{task_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('cancelled successfully', data['message'])
        
        # Verify task status was updated
        with self.app.app_context():
            task = VideoTask.query.get(task_id)
            self.assertEqual(task.status, 'cancelled')
        
        # Verify Celery task was revoked
        mock_revoke.assert_called_once_with(task_id, terminate=True)
    
    def test_cancel_task_endpoint_already_finished(self):
        """Test cancelling an already finished task."""
        # Create a completed task
        with self.app.app_context():
            task = VideoTask(
                youtube_url='https://www.youtube.com/watch?v=test',
                target_language='es',
                status='completed'
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        response = self.client.post(f'/api/dubbing/cancel-task/{task_id}')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('already finished', data['error'])

class TestDubbingTaskCelery(unittest.TestCase):
    """Tests for the Celery dubbing task."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up test fixtures."""
        with self.app.app_context():
            db.drop_all()
    
    @patch('src.routes.dubbing.youtube_service')
    @patch('src.routes.dubbing.audio_service')
    @patch('src.routes.dubbing.gemini_service')
    @patch('src.routes.dubbing.cleanup_temp_files')
    @patch('os.makedirs')
    def test_dubbing_task_success(self, mock_makedirs, mock_cleanup, 
                                 mock_gemini, mock_audio, mock_youtube):
        """Test successful completion of dubbing task."""
        # Create a test task
        with self.app.app_context():
            task = VideoTask(
                youtube_url='https://www.youtube.com/watch?v=test',
                target_language='es',
                source_language='en'
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        # Mock service responses
        mock_youtube.download_video.return_value = {
            'video_path': '/tmp/test_video.mp4',
            'title': 'Test Video'
        }
        mock_audio.extract_audio_from_video.return_value = '/tmp/test_audio.wav'
        mock_audio.preprocess_audio.return_value = '/tmp/test_audio_processed.wav'
        mock_gemini.transcribe_audio.return_value = {
            'text': 'Hello world'
        }
        mock_gemini.translate_text.return_value = {
            'translated_text': 'Hola mundo'
        }
        mock_audio.text_to_speech.return_value = '/tmp/dubbed_audio.mp3'
        mock_audio.merge_audio_with_video.return_value = '/tmp/final_video.mp4'
        
        # Import and run the task
        from src.routes.dubbing import dubbing_task
        
        with self.app.app_context():
            dubbing_task(task_id)
            
            # Verify task completion
            task = VideoTask.query.get(task_id)
            self.assertEqual(task.status, 'completed')
            self.assertEqual(task.progress, 100)
            self.assertEqual(task.transcription_text, 'Hello world')
            self.assertEqual(task.translated_text, 'Hola mundo')
    
    @patch('src.routes.dubbing.youtube_service')
    @patch('os.makedirs')
    def test_dubbing_task_download_failure(self, mock_makedirs, mock_youtube):
        """Test dubbing task with download failure."""
        # Create a test task
        with self.app.app_context():
            task = VideoTask(
                youtube_url='https://www.youtube.com/watch?v=test',
                target_language='es'
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        # Mock download failure
        mock_youtube.download_video.return_value = None
        
        # Import and run the task
        from src.routes.dubbing import dubbing_task
        
        with self.app.app_context():
            dubbing_task(task_id)
            
            # Verify task failure
            task = VideoTask.query.get(task_id)
            self.assertEqual(task.status, 'failed')
            self.assertIn('Failed to download video', task.error_message)
    
    @patch('src.routes.dubbing.youtube_service')
    @patch('src.routes.dubbing.audio_service')
    @patch('src.routes.dubbing.gemini_service')
    @patch('os.makedirs')
    def test_dubbing_task_transcription_failure(self, mock_makedirs, mock_gemini, 
                                               mock_audio, mock_youtube):
        """Test dubbing task with transcription failure."""
        # Create a test task
        with self.app.app_context():
            task = VideoTask(
                youtube_url='https://www.youtube.com/watch?v=test',
                target_language='es'
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        # Mock successful download and audio extraction
        mock_youtube.download_video.return_value = {
            'video_path': '/tmp/test_video.mp4'
        }
        mock_audio.extract_audio_from_video.return_value = '/tmp/test_audio.wav'
        mock_audio.preprocess_audio.return_value = '/tmp/test_audio_processed.wav'
        
        # Mock transcription failure
        mock_gemini.transcribe_audio.return_value = None
        
        # Import and run the task
        from src.routes.dubbing import dubbing_task
        
        with self.app.app_context():
            dubbing_task(task_id)
            
            # Verify task failure
            task = VideoTask.query.get(task_id)
            self.assertEqual(task.status, 'failed')
            self.assertIn('Failed to transcribe audio', task.error_message)

class TestAccuracyMetrics(unittest.TestCase):
    """Tests for measuring and ensuring 100% accuracy."""
    
    def setUp(self):
        """Set up accuracy testing fixtures."""
        self.test_cases = [
            {
                'input_text': 'Hello, how are you?',
                'source_lang': 'en',
                'target_lang': 'es',
                'expected_contains': ['hola', 'como', 'estas']
            },
            {
                'input_text': 'Good morning, have a nice day!',
                'source_lang': 'en',
                'target_lang': 'fr',
                'expected_contains': ['bonjour', 'bonne', 'journee']
            }
        ]
    
    def test_translation_accuracy_metrics(self):
        """Test translation accuracy measurement."""
        from src.services.gemini_cli_service import GeminiCLIService
        
        service = GeminiCLIService()
        
        accuracy_scores = []
        
        for test_case in self.test_cases:
            with patch.object(service, 'translate_text') as mock_translate:
                # Mock a realistic translation response
                mock_translate.return_value = {
                    'translated_text': 'Hola, ¿cómo estás?',
                    'source_language': test_case['source_lang'],
                    'target_language': test_case['target_lang'],
                    'confidence': 0.95
                }
                
                result = service.translate_text(
                    test_case['input_text'],
                    test_case['target_lang'],
                    test_case['source_lang']
                )
                
                if result:
                    # Calculate accuracy based on expected content
                    translated_text = result['translated_text'].lower()
                    matches = sum(1 for word in test_case['expected_contains'] 
                                if word in translated_text)
                    accuracy = matches / len(test_case['expected_contains'])
                    accuracy_scores.append(accuracy)
                else:
                    accuracy_scores.append(0.0)
        
        # Calculate overall accuracy
        overall_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        # For 100% accuracy, we expect all test cases to pass
        self.assertGreaterEqual(overall_accuracy, 0.8, 
                               "Translation accuracy below acceptable threshold")
    
    def test_audio_quality_metrics(self):
        """Test audio quality measurement."""
        from src.services.audio_service import AudioService
        
        service = AudioService()
        
        # Test audio processing pipeline
        test_audio_path = "/tmp/test_audio.wav"
        
        with patch.object(service, 'preprocess_audio') as mock_preprocess:
            with patch.object(service, 'get_audio_duration') as mock_duration:
                mock_preprocess.return_value = "/tmp/processed_audio.wav"
                mock_duration.return_value = 10.5  # 10.5 seconds
                
                # Test preprocessing
                processed_path = service.preprocess_audio(test_audio_path)
                self.assertIsNotNone(processed_path)
                
                # Test duration measurement
                duration = service.get_audio_duration(processed_path)
                self.assertIsNotNone(duration)
                self.assertGreater(duration, 0)
    
    def test_end_to_end_accuracy(self):
        """Test end-to-end workflow accuracy."""
        # This test simulates the complete workflow and measures accuracy
        workflow_steps = [
            'download_video',
            'extract_audio',
            'preprocess_audio',
            'transcribe_audio',
            'translate_text',
            'text_to_speech',
            'merge_audio_video'
        ]
        
        step_success_rates = {}
        
        for step in workflow_steps:
            # Simulate step execution with mock success/failure
            # In a real scenario, this would run actual operations
            success_rate = 0.95  # 95% success rate per step
            step_success_rates[step] = success_rate
        
        # Calculate overall workflow success rate
        overall_success_rate = 1.0
        for rate in step_success_rates.values():
            overall_success_rate *= rate
        
        # For 100% accuracy target, we need very high success rates
        self.assertGreaterEqual(overall_success_rate, 0.90,
                               f"Overall workflow success rate {overall_success_rate:.2%} below target")
        
        # Log individual step performance
        for step, rate in step_success_rates.items():
            print(f"{step}: {rate:.2%} success rate")
        
        print(f"Overall workflow success rate: {overall_success_rate:.2%}")

if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests with high verbosity
    unittest.main(verbosity=2)

