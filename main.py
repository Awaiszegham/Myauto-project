"""
Main application entry point for YouTube Dubbing AI Agent.
Railway deployment entry point.
"""

import os
import sys
from src import create_app

# Create Flask application using factory pattern
app = create_app()

# Railway health check endpoint
@app.route('/health')
def health():
    return {"status": "healthy", "service": "youtube-dubbing-ai"}, 200

if __name__ == '__main__':
    # Get port from Railway environment (correct default for Railway)
    port = int(os.getenv('PORT', 8080))  # ← Fixed: Railway default port
    
    # Run application (only for local development)
    print(f"Starting development server on port {port}")
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=False
    )
