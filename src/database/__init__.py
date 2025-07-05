"""
Database package for YouTube Dubbing AI Agent.
Handles database configuration, migrations, and initialization.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def init_database(app):
    """Initialize database with Flask app."""
    # Configure database
    configure_database(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    return db

def configure_database(app):
    """Configure database settings for different environments."""
    
    # Railway Production Database (PostgreSQL)
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        database_url = os.getenv('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            # Fix for SQLAlchemy 1.4+ compatibility
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {
                'sslmode': 'require',
                'options': '-c timezone=utc'
            }
        }
    
    # Local Development Database (SQLite)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dubbing_agent.db'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True
        }
    
    # Common database settings
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_RECORD_QUERIES'] = app.config.get('DEBUG', False)

def create_tables(app):
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")

def drop_tables(app):
    """Drop all database tables (use with caution)."""
    with app.app_context():
        db.drop_all()
        print("Database tables dropped")
