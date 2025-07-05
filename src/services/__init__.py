"""
Services package for YouTube Dubbing AI Agent.
Contains all service classes for video processing, audio generation, and API integrations.
"""

import logging
import os

# Initialize logging for services
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all services
try:
    from .adaptive_mitigation_service import AdaptiveMitigationService
    from .audio_service import AudioService
    from .gemini_cli_service import GeminiCLIService
    from .youtube_service import YouTubeService
    
    logger.info("All services imported successfully")
    
except ImportError as e:
    logger.error(f"Failed to import services: {e}")
    raise

# Export all services
__all__ = [
    'AdaptiveMitigationService',
    'AudioService',
    'GeminiCLIService', 
    'YouTubeService'
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Your Name"
__description__ = "Services for YouTube Dubbing AI Agent"

# Validate required environment variables
def validate_environment():
    """Validate that required environment variables are set."""
    required_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    return True

# Initialize package
def initialize_services():
    """Initialize all services with proper configuration."""
    try:
        validate_environment()
        logger.info("Services package initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False

# Auto-initialize when package is imported
if __name__ != "__main__":
    initialize_services()
