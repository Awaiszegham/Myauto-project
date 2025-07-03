
import unittest
import requests
import json
import time

class TestRemoteDubbingWorkflowIntegration(unittest.TestCase):
    """Integration tests for the deployed dubbing workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "https://myauto-project-production.up.railway.app"
        self.task_id = None

    def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        response = requests.get(f"{self.base_url}/api/dubbing/health")
        self.assertEqual(response.status_code, 200, f"Error: {response.text}")
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('services', data)

    def test_start_dubbing_endpoint_success(self):
        """Test successful dubbing initiation."""
        payload = {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'target_language': 'es',
            'source_language': 'en'
        }
        response = requests.post(f"{self.base_url}/api/dubbing/start-dubbing", json=payload)
        self.assertEqual(response.status_code, 202, f"Error: {response.text}")
        data = response.json()
        self.assertEqual(data['status'], 'started')
        self.assertIn('task_id', data)
        self.task_id = data['task_id']

    def test_start_dubbing_endpoint_missing_data(self):
        """Test dubbing initiation with missing required data."""
        payload = {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            # Missing target_language
        }
        response = requests.post(f"{self.base_url}/api/dubbing/start-dubbing", json=payload)
        self.assertEqual(response.status_code, 400, f"Error: {response.text}")
        data = response.json()
        self.assertIn('error', data)

    def test_start_dubbing_endpoint_invalid_url(self):
        """Test dubbing initiation with invalid YouTube URL."""
        payload = {
            'youtube_url': 'https://example.com/not-youtube',
            'target_language': 'es'
        }
        response = requests.post(f"{self.base_url}/api/dubbing/start-dubbing", json=payload)
        self.assertEqual(response.status_code, 400, f"Error: {response.text}")
        data = response.json()
        self.assertIn('Invalid YouTube URL', data['error'])

    def test_task_status_endpoint(self):
        """Test task status retrieval."""
        # First, start a task to get a task_id
        payload = {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'target_language': 'es',
            'source_language': 'en'
        }
        response = requests.post(f"{self.base_url}/api/dubbing/start-dubbing", json=payload)
        self.assertEqual(response.status_code, 202, f"Error: {response.text}")
        data = response.json()
        task_id = data['task_id']

        # Now, check the status
        response = requests.get(f"{self.base_url}/api/dubbing/task-status/{task_id}")
        self.assertEqual(response.status_code, 200, f"Error: {response.text}")
        data = response.json()
        self.assertEqual(data['id'], task_id)

    def test_list_tasks_endpoint(self):
        """Test task listing endpoint."""
        response = requests.get(f"{self.base_url}/api/dubbing/tasks")
        self.assertEqual(response.status_code, 200, f"Error: {response.text}")
        data = response.json()
        self.assertIn('tasks', data)

    def test_supported_languages_endpoint(self):
        """Test supported languages endpoint."""
        response = requests.get(f"{self.base_url}/api/dubbing/supported-languages")
        self.assertEqual(response.status_code, 200, f"Error: {response.text}")
        data = response.json()
        self.assertIn('gemini_languages', data)
        self.assertIn('polly_voices', data)
        self.assertIn('common_languages', data)

    def test_cancel_task_endpoint(self):
        """Test task cancellation endpoint."""
        # First, start a task to get a task_id
        payload = {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'target_language': 'es',
            'source_language': 'en'
        }
        response = requests.post(f"{self.base_url}/api/dubbing/start-dubbing", json=payload)
        self.assertEqual(response.status_code, 202, f"Error: {response.text}")
        data = response.json()
        task_id = data['task_id']

        # Now, cancel the task
        response = requests.post(f"{self.base_url}/api/dubbing/cancel-task/{task_id}")
        self.assertEqual(response.status_code, 200, f"Error: {response.text}")
        data = response.json()
        self.assertIn('cancelled successfully', data['message'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
