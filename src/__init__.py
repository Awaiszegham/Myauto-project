"""
YouTube Dubbing AI Agent - Main Package
Enhanced Production-Ready Version with Railway Optimization
"""

import os
import sys
import logging
import time
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Conditional imports with fallbacks
try:
    from flask_migrate import Migrate
    MIGRATE_AVAILABLE = True
except ImportError:
    MIGRATE_AVAILABLE = False
    print("Warning: Flask-Migrate not available. Database migrations disabled.")

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    print("Warning: Celery not available. Background tasks disabled.")

# Package metadata
__version__ = "1.0.0"
__author__ = "YouTube Dubbing AI Team"
__description__ = "AI-powered YouTube video dubbing system with Railway deployment"
__railway_optimized__ = True

# Enhanced logging configuration
log_level = logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/app.log') if os.path.exists('/tmp') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global extensions
db = SQLAlchemy()
migrate = None
celery = None

# Application metrics
app_metrics = {
    'start_time': time.time(),
    'requests_count': 0,
    'errors_count': 0,
    'last_health_check': None
}

def create_app(config_name=None):
    """
    Enhanced application factory pattern for creating Flask app instances.
    Optimized for Railway deployment with comprehensive error handling.
    """
    logger.info(f"Creating YouTube Dubbing AI Agent v{__version__}")
    
    app = Flask(__name__, 
                static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
                instance_relative_config=True)
    
    try:
        # Load configuration with validation
        configure_app(app, config_name)
        
        # Validate environment before proceeding
        validation_result = validate_environment()
        if not validation_result['valid']:
            logger.warning(f"Environment validation issues: {validation_result['missing']}")
        
        # Initialize extensions
        initialize_extensions(app)
        
        # Setup health check endpoints (critical for Railway)
        setup_health_endpoints(app)
        
        # Register blueprints
        register_blueprints(app)
        
        # Setup error handlers and monitoring
        setup_error_handlers(app)
        setup_request_monitoring(app)
        
        # Railway-specific initialization
        if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
            railway_initialization(app)
        
        # Initialize Celery if available
        if CELERY_AVAILABLE:
            initialize_celery(app)
        
        logger.info(f"✅ Application created successfully for {config_name or 'default'} environment")
        return app
        
    except Exception as e:
        logger.error(f"❌ Critical error creating application: {e}")
        raise

def configure_app(app, config_name=None):
    """Enhanced Flask application configuration with Railway optimization."""
    
    logger.info("Configuring application settings...")
    
    # Basic Flask configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-fallback-key-change-in-production')
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['JSON_SORT_KEYS'] = False
    
    # Enhanced database configuration for Railway
    configure_database(app)
    
    # Redis configuration for Celery
    configure_redis(app)
    
    # File upload configuration
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 500 * 1024 * 1024))  # 500MB
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/dubbing_uploads')
    
    # Application-specific settings
    app.config['MAX_VIDEO_DURATION'] = int(os.getenv('MAX_VIDEO_DURATION', 3600))  # 1 hour
    app.config['SUPPORTED_FORMATS'] = ['mp4', 'avi', 'mov', 'mkv', 'webm']
    app.config['DEFAULT_LANGUAGE'] = 'en-US'
    
    # Environment-specific settings
    if os.getenv('RAILWAY_ENVIRONMENT_NAME') or os.getenv('FLASK_ENV') == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['ENV'] = 'production'
        app.config['PROPAGATE_EXCEPTIONS'] = True
    else:
        app.config['DEBUG'] = True
        app.config['ENV'] = 'development'
    
    # Performance settings
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_RECORD_QUERIES'] = app.config['DEBUG']
    
    logger.info("✅ Application configuration completed")

def configure_database(app):
    """Enhanced database configuration with Railway private network support."""
    
    # Try Railway's internal database connection first (private network)
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Handle Railway PostgreSQL URLs
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 20,
            'max_overflow': 10,
            'pool_size': 5,
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 10,
                'application_name': 'youtube_dubbing_ai'
            }
        }
        logger.info("✅ Using Railway PostgreSQL database")
        
    else:
        # Fallback to SQLite for local development
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_timeout': 20
        }
        logger.warning("⚠️ Using SQLite fallback database")

def configure_redis(app):
    """Configure Redis for Celery task queue."""
    
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        app.config['CELERY_BROKER_URL'] = redis_url
        app.config['CELERY_RESULT_BACKEND'] = redis_url
        logger.info("✅ Redis configured for task queue")
    else:
        app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
        app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
        logger.warning("⚠️ Using local Redis fallback")

def initialize_extensions(app):
    """Initialize Flask extensions with enhanced error handling."""
    global migrate
    
    try:
        # Initialize CORS with specific configuration
        CORS(app, resources={
            r"/api/*": {
                "origins": ["*"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "expose_headers": ["X-Total-Count", "X-Page-Count"]
            }
        })
        logger.info("✅ CORS initialized")
        
        # Initialize database
        db.init_app(app)
        logger.info("✅ SQLAlchemy initialized")
        
        # Initialize migrations if available
        if MIGRATE_AVAILABLE:
            migrate = Migrate(app, db, compare_type=True)
            logger.info("✅ Flask-Migrate initialized")
        else:
            logger.warning("⚠️ Flask-Migrate not available - using manual table creation")
        
        # Create tables with error handling
        with app.app_context():
            try:
                db.create_all()
                logger.info("✅ Database tables created/verified")
            except Exception as e:
                logger.error(f"❌ Database table creation failed: {e}")
                # Don't raise here, let the app start but log the issue
        
        logger.info("✅ Extensions initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Critical error initializing extensions: {e}")
        raise

def setup_health_endpoints(app):
    """Setup comprehensive health check endpoints for Railway monitoring."""
    
    @app.route('/health')
    def health_check():
        """Primary health check endpoint for Railway."""
        global app_metrics
        
        try:
            app_metrics['last_health_check'] = datetime.utcnow().isoformat()
            
            # Basic health response
            health_data = {
                "status": "healthy",
                "service": "youtube-dubbing-ai",
                "version": __version__,
                "timestamp": app_metrics['last_health_check'],
                "uptime": time.time() - app_metrics['start_time']
            }
            
            return jsonify(health_data), 200
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 503
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check with service status."""
        try:
            # Check database connectivity
            db_healthy = False
            try:
                with app.app_context():
                    db.session.execute('SELECT 1')
                    db_healthy = True
            except:
                pass
            
            # Check environment variables
            env_status = validate_environment()
            
            health_data = {
                "status": "healthy" if db_healthy and env_status['valid'] else "degraded",
                "service": "youtube-dubbing-ai",
                "version": __version__,
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": db_healthy,
                    "environment": env_status['valid'],
                    "migrate_available": MIGRATE_AVAILABLE,
                    "celery_available": CELERY_AVAILABLE
                },
                "metrics": {
                    "uptime_seconds": time.time() - app_metrics['start_time'],
                    "requests_count": app_metrics['requests_count'],
                    "errors_count": app_metrics['errors_count']
                },
                "environment": {
                    "railway": bool(os.getenv('RAILWAY_ENVIRONMENT_NAME')),
                    "flask_env": os.getenv('FLASK_ENV', 'development')
                }
            }
            
            status_code = 200 if health_data["status"] == "healthy" else 503
            return jsonify(health_data), status_code
            
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 503

def register_blueprints(app):
    """Register Flask blueprints with enhanced error handling."""
    try:
        # Import blueprints with error handling
        try:
            from src.routes.user import user_bp
            app.register_blueprint(user_bp, url_prefix='/api/users')
            logger.info("✅ User blueprint registered")
        except ImportError as e:
            logger.error(f"❌ Failed to import user blueprint: {e}")
        
        try:
            from src.routes.dubbing import dubbing_bp
            app.register_blueprint(dubbing_bp, url_prefix='/api/dubbing')
            logger.info("✅ Dubbing blueprint registered")
        except ImportError as e:
            logger.error(f"❌ Failed to import dubbing blueprint: {e}")
        
        logger.info("✅ Blueprint registration completed")
        
    except Exception as e:
        logger.error(f"❌ Critical error registering blueprints: {e}")
        # Don't raise here - let the app start with basic functionality

def setup_error_handlers(app):
    """Setup comprehensive error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        app_metrics['errors_count'] += 1
        logger.warning(f"404 error: {error}")
        return jsonify({
            "error": "Resource not found",
            "status": 404,
            "timestamp": datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app_metrics['errors_count'] += 1
        logger.error(f"500 error: {error}")
        db.session.rollback()
        return jsonify({
            "error": "Internal server error",
            "status": 500,
            "timestamp": datetime.utcnow().isoformat()
        }), 500
    
    @app.errorhandler(413)
    def too_large(error):
        app_metrics['errors_count'] += 1
        logger.warning(f"413 error: {error}")
        return jsonify({
            "error": "File too large",
            "status": 413,
            "max_size": app.config.get('MAX_CONTENT_LENGTH', 'Unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }), 413
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        app_metrics['errors_count'] += 1
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({
            "error": "An unexpected error occurred",
            "status": 500,
            "timestamp": datetime.utcnow().isoformat()
        }), 500

def setup_request_monitoring(app):
    """Setup request monitoring and metrics."""
    
    @app.before_request
    def before_request():
        app_metrics['requests_count'] += 1
    
    @app.after_request
    def after_request(response):
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response

def validate_environment():
    """Validate critical environment variables."""
    
    required_vars = {
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'DATABASE_URL': os.getenv('DATABASE_URL'),
    }
    
    optional_vars = {
        'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        'YOUTUBE_API_KEY': os.getenv('YOUTUBE_API_KEY'),
        'REDIS_URL': os.getenv('REDIS_URL')
    }
    
    missing_required = [key for key, value in required_vars.items() if not value]
    missing_optional = [key for key, value in optional_vars.items() if not value]
    
    result = {
        'valid': len(missing_required) == 0,
        'missing': missing_required,
        'missing_optional': missing_optional,
        'total_vars': len(required_vars) + len(optional_vars),
        'configured_vars': len([v for v in {**required_vars, **optional_vars}.values() if v])
    }
    
    if missing_required:
        logger.error(f"❌ Missing required environment variables: {missing_required}")
    if missing_optional:
        logger.warning(f"⚠️ Missing optional environment variables: {missing_optional}")
    
    return result

def initialize_celery(app):
    """Initialize Celery for background tasks."""
    global celery
    
    try:
        celery = Celery(
            app.import_name,
            broker=app.config['CELERY_BROKER_URL'],
            backend=app.config['CELERY_RESULT_BACKEND']
        )
        
        celery.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=1800,  # 30 minutes
            task_soft_time_limit=1500,  # 25 minutes
            worker_prefetch_multiplier=1,
            task_acks_late=True
        )
        
        logger.info("✅ Celery initialized for background tasks")
        
    except Exception as e:
        logger.error(f"❌ Celery initialization failed: {e}")

def railway_initialization(app):
    """Enhanced Railway-specific initialization."""
    
    logger.info("🚂 Initializing Railway-specific features...")
    
    try:
        # Ensure upload directory exists
        upload_dir = app.config.get('UPLOAD_FOLDER', '/tmp/dubbing_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        logger.info(f"✅ Upload directory ready: {upload_dir}")
        
        # Run database migrations on Railway startup
        if MIGRATE_AVAILABLE and migrate:
            with app.app_context():
                try:
                    from flask_migrate import upgrade
                    upgrade()
                    logger.info("✅ Database migrations completed on Railway")
                except Exception as e:
                    logger.warning(f"⚠️ Migration warning on Railway: {e}")
        
        # Log environment information
        logger.info(f"🚂 Railway Environment: {os.getenv('RAILWAY_ENVIRONMENT_NAME', 'Unknown')}")
        logger.info(f"🚂 Railway Service: {os.getenv('RAILWAY_SERVICE_NAME', 'Unknown')}")
        
        # Set up Railway-specific monitoring
        setup_railway_monitoring(app)
        
        logger.info("✅ Railway initialization completed")
        
    except Exception as e:
        logger.error(f"❌ Railway initialization error: {e}")

def setup_railway_monitoring(app):
    """Setup Railway-specific monitoring and health checks."""
    
    @app.route('/metrics')
    def metrics():
        """Expose application metrics for monitoring."""
        return jsonify({
            "metrics": app_metrics,
            "environment": {
                "railway_env": os.getenv('RAILWAY_ENVIRONMENT_NAME'),
                "service_name": os.getenv('RAILWAY_SERVICE_NAME'),
                "deployment_id": os.getenv('RAILWAY_DEPLOYMENT_ID')
            }
        })

# Export main components
__all__ = [
    'create_app', 
    'db', 
    'migrate', 
    'celery',
    'validate_environment',
    'app_metrics'
]

# Package initialization logging
logger.info(f"🎬 YouTube Dubbing AI Agent package v{__version__} loaded successfully")
logger.info(f"🚂 Railway optimization: {'✅ Enabled' if __railway_optimized__ else '❌ Disabled'}")

# Startup environment validation
startup_validation = validate_environment()
if startup_validation['valid']:
    logger.info("✅ Environment validation passed on package load")
else:
    logger.warning(f"⚠️ Environment validation issues detected: {startup_validation['missing']}")
