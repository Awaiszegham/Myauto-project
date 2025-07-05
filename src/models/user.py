from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from typing import Dict, Any

db = SQLAlchemy()

class User(db.Model):
    """User model for YouTube Dubbing AI Agent."""
    
    __tablename__ = 'users'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # User information
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Optional user details
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    video_tasks = db.relationship('VideoTask', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user instance to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'total_tasks': self.video_tasks.count()
        }
    
    def from_dict(self, data: Dict[str, Any], new_user: bool = False):
        """Update user instance from dictionary."""
        for field in ['username', 'email', 'first_name', 'last_name', 'is_active']:
            if field in data:
                setattr(self, field, data[field])
        
        if new_user and not self.created_at:
            self.created_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format."""
        import re
        # Username should be 3-80 characters, alphanumeric and underscores only
        pattern = r'^[a-zA-Z0-9_]{3,80}$'
        return re.match(pattern, username) is not None
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_active_tasks(self):
        """Get all active (non-completed/failed) tasks for this user."""
        return self.video_tasks.filter(
            VideoTask.status.in_(['pending', 'downloading', 'processing', 'uploading'])
        ).all()
    
    def get_completed_tasks(self):
        """Get all completed tasks for this user."""
        return self.video_tasks.filter(VideoTask.status == 'completed').all()
