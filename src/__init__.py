"""
YouTube Dubbing AI Agent - Main Package
"""

import os
import sys
import logging
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Conditional import for Flask-Migrate
try:
    from flask_migrate import Migrate
    MIGRATE_AVAILABLE = True
except ImportError:
    MIGRATE_AVAILABLE = False
    print("Warning: Flask-Migrate not available. Database migrations disabled.")

# Package metadata
__version__ = "1.0.0"
__author__ = "Your Name"

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global extensions
db = SQLAlchemy()
migrate = None

def create_app(config_name=None):
    """Application factory pattern for creating Flask app instances."""
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
    
    # Load configuration
    configure_app(app, config_name)
    
    # Initialize extensions
    initialize_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
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
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {'sslmode': 'require'}
        }
    else:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True
        }
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Environment-specific settings
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['ENV'] = 'production'
    else:
        app.config['DEBUG'] = True
        app.config['ENV'] = 'development'

def initialize_extensions(app):
    """Initialize Flask extensions."""
    global migrate
    
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
        
        # Initialize migrations if available
        if MIGRATE_AVAILABLE:
            migrate = Migrate(app, db)
            logger.info("Flask-Migrate initialized successfully")
        else:
            logger.warning("Flask-Migrate not available - manual table creation will be used")
        
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
        from src.routes.user import user_bp
        from src.routes.dubbing import dubbing_bp
        
        app.register_blueprint(user_bp, url_prefix='/api')
        app.register_blueprint(dubbing_bp, url_prefix='/api/dubbing')
        
        logger.info("Blueprints registered successfully")
        
    except ImportError as e:
        logger.error(f"Error importing blueprints: {e}")
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

def railway_initialization(app):
    """Special initialization for Railway deployment."""
    try:
        upload_dir = '/tmp/dubbing_uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        # Only run migrations if Flask-Migrate is available
        if MIGRATE_AVAILABLE and migrate:
            with app.app_context():
                try:
                    from flask_migrate import upgrade
                    upgrade()
                    logger.info("Database migrations completed on Railway")
                except Exception as e:
                    logger.warning(f"Migration warning on Railway: {e}")
        
        logger.info("Railway initialization completed")
        
    except Exception as e:
        logger.error(f"Railway initialization error: {e}")

# Export main components
__all__ = ['create_app', 'db']

logger.info(f"YouTube Dubbing AI Agent package v{__version__} loaded")
