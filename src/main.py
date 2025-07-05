"""
Main application entry point for YouTube Dubbing AI Agent.
"""

import os
from src import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Get port from environment (Railway sets this automatically)
    port = int(os.getenv('PORT', 5000))
    
    # Run application
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=os.getenv('FLASK_ENV') == 'development'
    )
