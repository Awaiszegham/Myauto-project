"""
Pytest configuration for Railway deployment testing.
"""

import pytest
import os
import requests
import time

@pytest.fixture(scope="session")
def railway_base_url():
    """Get Railway deployment URL."""
    return "https://myauto-project-production.up.railway.app"

@pytest.fixture(scope="session")
def wait_for_deployment(railway_base_url):
    """Wait for Railway deployment to be ready."""
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{railway_base_url}/health", timeout=10)
            if response.status_code == 200:
                return True
        except:
            pass
        
        if attempt < max_attempts - 1:
            time.sleep(10)
    
    pytest.fail("Railway deployment not ready after 5 minutes")

@pytest.fixture
def api_client(railway_base_url):
    """Create API client for testing."""
    class APIClient:
        def __init__(self, base_url):
            self.base_url = base_url
        
        def get(self, endpoint, **kwargs):
            return requests.get(f"{self.base_url}{endpoint}", **kwargs)
        
        def post(self, endpoint, **kwargs):
            return requests.post(f"{self.base_url}{endpoint}", **kwargs)
    
    return APIClient(railway_base_url)
