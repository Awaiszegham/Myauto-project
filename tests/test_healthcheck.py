"""
Dedicated healthcheck tests for Railway deployment debugging.
"""

import unittest
import requests
import json
import time
from tests import get_base_url, TEST_CONFIG

class TestHealthCheckEndpoints(unittest.TestCase):
    """Test all health check endpoints for Railway deployment."""
    
    def setUp(self):
        self.base_url = get_base_url()
        self.timeout = TEST_CONFIG['TEST_TIMEOUT']
    
    def test_main_health_endpoint(self):
        """Test main /health endpoint that Railway checks."""
        try:
            response = requests.get(
                f"{self.base_url}/health", 
                timeout=self.timeout
            )
            
            print(f"Health endpoint status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get('service'), 'youtube-dubbing-ai')
            else:
                self.fail(f"Health check failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            self.fail(f"Health check request failed: {e}")
    
    def test_api_health_endpoint(self):
        """Test API health endpoint with service details."""
        try:
            response = requests.get(
                f"{self.base_url}/api/dubbing/health",
                timeout=self.timeout
            )
            
            print(f"API health status: {response.status_code}")
            print(f"API health response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.assertIn('services', data)
                print(f"Service status: {data.get('services', {})}")
            
        except requests.exceptions.RequestException as e:
            print(f"API health check failed: {e}")
    
    def test_service_connectivity(self):
        """Test individual service connectivity."""
        endpoints_to_test = [
            '/api/dubbing/supported-languages',
            '/api/dubbing/tasks'
        ]
        
        for endpoint in endpoints_to_test:
            with self.subTest(endpoint=endpoint):
                try:
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        timeout=self.timeout
                    )
                    print(f"{endpoint}: {response.status_code}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"{endpoint} failed: {e}")

if __name__ == '__main__':
    # Run with maximum verbosity for debugging
    unittest.main(verbosity=2)
