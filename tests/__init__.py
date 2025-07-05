"""
Test package for YouTube Dubbing AI Agent.
Contains comprehensive test suites for all components.
"""

import os
import sys
import unittest
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test configuration
TEST_CONFIG = {
    'RAILWAY_BASE_URL': 'https://myauto-project-production.up.railway.app',
    'LOCAL_BASE_URL': 'http://localhost:5000',
    'TEST_TIMEOUT': 30,
    'INTEGRATION_TESTS_ENABLED': os.getenv('RUN_INTEGRATION_TESTS', 'false').lower() == 'true'
}

def get_base_url():
    """Get the appropriate base URL for testing."""
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        return TEST_CONFIG['RAILWAY_BASE_URL']
    return TEST_CONFIG['LOCAL_BASE_URL']

__all__ = ['TEST_CONFIG', 'get_base_url']
