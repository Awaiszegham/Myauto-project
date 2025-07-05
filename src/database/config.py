"""
Database configuration for different environments.
"""

import os
from urllib.parse import quote_plus

class DatabaseConfig:
    """Base database configuration."""
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = False
    
    # Connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_timeout': 20,
        'max_overflow': 0
    }

class DevelopmentConfig(DatabaseConfig):
    """Development database configuration."""
    
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dubbing_agent_dev.db'
    SQLALCHEMY_RECORD_QUERIES = True
    DEBUG = True

class TestingConfig(DatabaseConfig):
    """Testing database configuration."""
    
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True

class ProductionConfig(DatabaseConfig):
    """Production database configuration for Railway."""
    
    @staticmethod
    def get_database_uri():
        """Get Railway PostgreSQL database URI."""
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Fix SQLAlchemy 1.4+ compatibility
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        return database_url
    
    SQLALCHEMY_DATABASE_URI = get_database_uri.__func__()
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 10,
        'pool_size': 5,
        'connect_args': {
            'sslmode': 'require',
            'options': '-c timezone=utc'
        }
    }

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(environment=None):
    """Get configuration class for environment."""
    if environment is None:
        environment = os.getenv('FLASK_ENV', 'development')
    
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        environment = 'production'
    
    return config_map.get(environment, config_map['default'])
