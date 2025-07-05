"""
Models package for YouTube Dubbing AI Agent.
Contains all database model definitions.
"""

from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Import all models to ensure they're registered with SQLAlchemy
from .user import User
from .video_task import VideoTask

__all__ = ['db', 'User', 'VideoTask']

def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Optional: Create default admin user for development
        if app.config.get('FLASK_ENV') == 'development':
            create_default_user()

def create_default_user():
    """Create a default user for development/testing."""
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created")
