"""
YouTube Dubbing AI Agent - Main Package
=============================================

A comprehensive AI-powered system for automatically dubbing YouTube videos
into different languages using advanced speech synthesis and translation.

Features:
- YouTube video downloading and processing
- Audio extraction and preprocessing  
- AI-powered transcription using Gemini CLI
- Multi-language translation capabilities
- High-quality text-to-speech with AWS Polly
- Video-audio merging and final output generation
- Celery-based asynchronous task processing
- Railway deployment ready

Author: Your Name
Version: 1.0.0
Environment: Production-ready for Railway deployment
"""

import os
import sys
import logging
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Package metadata
__version__ = "1.0.0"
__author__ = "Your Name"
__description__ = "AI-powered YouTube video dubbing system"
__railway_compatible__ = True

# Initialize logging for the entire package
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global extensions (will be initialized in create_app)
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    """
    Application factory pattern for creating Flask app instances.
    
    Args:
        config_name: Configuration environment ('development', 'production', 'testing')
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
    
    # Load configuration
    configure_app(app, config_name)
    
    # Initialize extensions
    initialize_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Setup static file serving
    setup_static_routes(app)
    
    # Railway-specific initialization
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        railway_initialization(app)
    
    logger.info(f"Application created successfully for {config_name or 'default'} environment")
    return app

def configure_app(app, config_name=None):
    """Configure Flask application settings."""
    
    # Basic Flask configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
    
    # Database configuration
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres'):
        # Railway PostgreSQL configuration
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {'sslmode': 'require'}
        }
    else:
        # Local SQLite configuration
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True
        }
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Environment-specific settings
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        # Production settings for Railway
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['ENV'] = 'production'
    else:
        # Development settings
        app.config['DEBUG'] = True
        app.config['ENV'] = 'development'
    
    # Celery configuration
    app.config['CELERY_BROKER_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    app.config['CELERY_RESULT_BACKEND'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # File upload settings
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/dubbing_uploads')
    
    logger.info("Application configuration completed")

def initialize_extensions(app):
    """Initialize Flask extensions."""
    try:
        # Initialize CORS
        CORS(app, resources={
            r"/api/*": {
                "origins": ["*"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        })
        
        # Initialize database
        db.init_app(app)
        
        # Initialize migrations
        migrate.init_app(app, db)
        
        # Create tables if they don't exist
        with app.app_context():
            db.create_all()
        
        logger.info("Extensions initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing extensions: {e}")
        raise

def register_blueprints(app):
    """Register Flask blueprints."""
    try:
        # Import blueprints
        from src.routes.user import user_bp
        from src.routes.dubbing import dubbing_bp
        
        # Register blueprints
        app.register_blueprint(user_bp, url_prefix='/api')
        app.register_blueprint(dubbing_bp, url_prefix='/api/dubbing')
        
        logger.info("Blueprints registered successfully")
        
    except ImportError as e:
        logger.error(f"Error importing blueprints: {e}")
        raise
    except Exception as e:
        logger.error(f"Error registering blueprints: {e}")
        raise

def setup_error_handlers(app):
    """Setup global error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error"}, 500
    
    @app.errorhandler(413)
    def too_large(error):
        return {"error": "File too large"}, 413
    
    logger.info("Error handlers configured")

def setup_static_routes(app):
    """Setup static file serving for frontend."""
    from flask import send_from_directory
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404
        
        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "Frontend not found", 404

def railway_initialization(app):
    """Special initialization for Railway deployment."""
    try:
        # Ensure upload directory exists
        upload_dir = app.config.get('UPLOAD_FOLDER', '/tmp/dubbing_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Run database migrations on Railway startup
        with app.app_context():
            try:
                from flask_migrate import upgrade
                upgrade()
                logger.info("Database migrations completed on Railway")
            except Exception as e:
                logger.warning(f"Migration warning on Railway: {e}")
        
        # Validate required environment variables
        required_vars = ['DATABASE_URL', 'REDIS_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing environment variables on Railway: {missing_vars}")
        
        logger.info("Railway initialization completed")
        
    except Exception as e:
        logger.error(f"Railway initialization error: {e}")

# Package-level imports for clean usage
def get_services():
    """Get all service instances."""
    try:
        from src.services import (
            YouTubeService,
            AudioService, 
            GeminiCLIService,
            AdaptiveMitigationService
        )
        
        return {
            'youtube': YouTubeService(),
            'audio': AudioService(),
            'gemini': GeminiCLIService(),
            'adaptive_mitigation': AdaptiveMitigationService()
        }
    except ImportError as e:
        logger.error(f"Error importing services: {e}")
        return {}

def get_models():
    """Get all model classes."""
    try:
        from src.models.user import User
        from src.models.video_task import VideoTask
        
        return {
            'User': User,
            'VideoTask': VideoTask
        }
    except ImportError as e:
        logger.error(f"Error importing models: {e}")
        return {}

def validate_environment():
    """Validate environment configuration."""
    checks = {
        'database': bool(os.getenv('DATABASE_URL')),
        'redis': bool(os.getenv('REDIS_URL')), 
        'aws_access_key': bool(os.getenv('AWS_ACCESS_KEY_ID')),
        'aws_secret_key': bool(os.getenv('AWS_SECRET_ACCESS_KEY')),
        'secret_key': bool(os.getenv('SECRET_KEY'))
    }
    
    missing = [key for key, value in checks.items() if not value]
    
    if missing:
        logger.warning(f"Missing environment variables: {missing}")
        return False, missing
    
    return True, []

# Export main components for easy importing
__all__ = [
    'create_app',
    'db', 
    'migrate',
    'get_services',
    'get_models',
    'validate_environment'
]

# Package initialization
logger.info(f"YouTube Dubbing AI Agent package v{__version__} loaded")

# Auto-validate environment on import
is_valid, missing_vars = validate_environment()
if not is_valid:
    logger.warning(f"Environment validation failed. Missing: {missing_vars}")
