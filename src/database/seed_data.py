"""
Database seeding utilities for development and testing.
"""

from src.models.user import User
from src.models.video_task import VideoTask
from database import db
from datetime import datetime, timedelta
import uuid

def seed_development_data(app):
    """Seed database with development data."""
    with app.app_context():
        print("Seeding development data...")
        
        # Create test users
        create_test_users()
        
        # Create sample tasks
        create_sample_tasks()
        
        print("Development data seeded successfully")

def create_test_users():
    """Create test users for development."""
    test_users = [
        {
            'username': 'admin',
            'email': 'admin@dubbing-agent.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_active': True
        },
        {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        },
        {
            'username': 'demo',
            'email': 'demo@example.com',
            'first_name': 'Demo',
            'last_name': 'Account',
            'is_active': True
        }
    ]
    
    for user_data in test_users:
        existing_user = User.query.filter_by(username=user_data['username']).first()
        if not existing_user:
            user = User(**user_data)
            db.session.add(user)
            print(f"Created user: {user_data['username']}")
    
    db.session.commit()

def create_sample_tasks():
    """Create sample video tasks for testing."""
    # Get test user
    test_user = User.query.filter_by(username='testuser').first()
    if not test_user:
        return
    
    sample_tasks = [
        {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'video_title': 'Sample Video 1',
            'target_language': 'es-ES',
            'source_language': 'en-US',
            'status': 'completed',
            'progress': 100,
            'video_duration': 212,
            'voice_style': 'natural',
            'quality_level': 'high'
        },
        {
            'youtube_url': 'https://www.youtube.com/watch?v=example123',
            'video_title': 'Sample Video 2',
            'target_language': 'fr-FR',
            'source_language': 'en-US',
            'status': 'processing',
            'progress': 65,
            'video_duration': 145,
            'voice_style': 'expressive',
            'quality_level': 'medium'
        }
    ]
    
    for task_data in sample_tasks:
        task = VideoTask(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            **task_data
        )
        
        # Set appropriate timestamps
        task.created_at = datetime.utcnow() - timedelta(hours=2)
        if task.status == 'completed':
            task.completed_at = datetime.utcnow() - timedelta(minutes=30)
            task.started_at = task.created_at + timedelta(minutes=5)
        elif task.status == 'processing':
            task.started_at = datetime.utcnow() - timedelta(minutes=45)
        
        db.session.add(task)
        print(f"Created task: {task_data['video_title']}")
    
    db.session.commit()

def clear_all_data(app):
    """Clear all data from database (use with caution)."""
    with app.app_context():
        print("Clearing all database data...")
        
        # Delete in reverse order of dependencies
        VideoTask.query.delete()
        User.query.delete()
        
        db.session.commit()
        print("All data cleared")

def reset_database(app):
    """Reset database with fresh seed data."""
    clear_all_data(app)
    seed_development_data(app)
