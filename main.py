"""
Main application entry point for YouTube Dubbing AI Agent.
Railway deployment entry point.
"""

import os
import sys
import logging
from src import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask application using factory pattern
app = create_app()

# Railway health check endpoint
@app.route('/health')
def health():
    return {"status": "ok"}

if __name__ == '__main__':
    # Get port from Railway environment
    port = int(os.getenv('PORT', 8080))
    
    # Log startup information
    logger.info(f"Starting application on port {port}")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    
    # Run application
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=False
    )
