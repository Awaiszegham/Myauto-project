from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class VideoTask(db.Model):
    __tablename__ = 'video_tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    youtube_url = db.Column(db.String(500), nullable=False)
    target_language = db.Column(db.String(10), nullable=False)
    source_language = db.Column(db.String(10), default='auto')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, downloading, processing, uploading, completed, failed
    progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text, nullable=True)
    
    # File paths
    original_video_path = db.Column(db.String(500), nullable=True)
    original_audio_path = db.Column(db.String(500), nullable=True)
    transcription_text = db.Column(db.Text, nullable=True)
    translated_text = db.Column(db.Text, nullable=True)
    dubbed_audio_path = db.Column(db.String(500), nullable=True)
    final_video_path = db.Column(db.String(500), nullable=True)
    
    # YouTube upload info
    uploaded_video_id = db.Column(db.String(100), nullable=True)
    uploaded_video_url = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'youtube_url': self.youtube_url,
            'target_language': self.target_language,
            'source_language': self.source_language,
            'status': self.status,
            'user_id': self.user_id,
            'progress': self.progress,
            'error_message': self.error_message,
            'uploaded_video_url': self.uploaded_video_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def update_status(self, status, progress=None, error_message=None):
        self.status = status
        if progress is not None:
            self.progress = progress
        if error_message is not None:
            self.error_message = error_message
        if status == 'completed':
            self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()

