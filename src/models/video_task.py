from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from typing import Dict, Any, Optional

db = SQLAlchemy()

class VideoTask(db.Model):
    """Video dubbing task model for tracking the entire dubbing process."""
    
    __tablename__ = 'video_tasks'

    # Primary key - UUID for better security and scalability
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Task identification
    celery_task_id = db.Column(db.String(100), nullable=True, index=True)
    
    # Video information
    youtube_url = db.Column(db.String(500), nullable=False)
    video_title = db.Column(db.String(200), nullable=True)
    video_duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    video_id = db.Column(db.String(20), nullable=True)  # YouTube video ID
    
    # Language settings
    target_language = db.Column(db.String(10), nullable=False)
    source_language = db.Column(db.String(10), default='auto')
    
    # User relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Task status and progress
    status = db.Column(db.String(50), default='pending', nullable=False, index=True)
    # Status options: pending, downloading, processing, uploading, completed, failed, cancelled
    progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text, nullable=True)
    
    # Quality and voice settings
    voice_style = db.Column(db.String(50), default='natural')  # natural, expressive, calm
    quality_level = db.Column(db.String(20), default='high')  # low, medium, high, premium
    
    # File paths for different stages
    original_video_path = db.Column(db.String(500), nullable=True)
    original_audio_path = db.Column(db.String(500), nullable=True)
    dubbed_audio_path = db.Column(db.String(500), nullable=True)
    final_video_path = db.Column(db.String(500), nullable=True)
    
    # Processing data
    transcription_text = db.Column(db.Text, nullable=True)
    translated_text = db.Column(db.Text, nullable=True)
    transcription_confidence = db.Column(db.Float, nullable=True)
    translation_confidence = db.Column(db.Float, nullable=True)
    
    # YouTube upload information
    uploaded_video_id = db.Column(db.String(100), nullable=True)
    uploaded_video_url = db.Column(db.String(500), nullable=True)
    upload_privacy = db.Column(db.String(20), default='private')  # private, public, unlisted
    
    # Processing metrics
    processing_time = db.Column(db.Integer, nullable=True)  # Total processing time in seconds
    file_size_mb = db.Column(db.Float, nullable=True)  # Final video file size in MB
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Constraints and indexes
    __table_args__ = (
        db.Index('idx_user_status', 'user_id', 'status'),
        db.Index('idx_created_status', 'created_at', 'status'),
        db.CheckConstraint('progress >= 0 AND progress <= 100', name='check_progress_range'),
    )
    
    def __repr__(self):
        return f'<VideoTask {self.id} - {self.status}>'

    def to_dict(self) -> Dict[str, Any]:
        """Convert task instance to dictionary."""
        return {
            'id': self.id,
            'celery_task_id': self.celery_task_id,
            'youtube_url': self.youtube_url,
            'video_title': self.video_title,
            'video_duration': self.video_duration,
            'video_id': self.video_id,
            'target_language': self.target_language,
            'source_language': self.source_language,
            'user_id': self.user_id,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'voice_style': self.voice_style,
            'quality_level': self.quality_level,
            'transcription_confidence': self.transcription_confidence,
            'translation_confidence': self.translation_confidence,
            'uploaded_video_url': self.uploaded_video_url,
            'upload_privacy': self.upload_privacy,
            'processing_time': self.processing_time,
            'file_size_mb': self.file_size_mb,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'estimated_completion': self.get_estimated_completion(),
            'duration_formatted': self.get_duration_formatted()
        }

    def from_dict(self, data: Dict[str, Any]):
        """Update task instance from dictionary."""
        allowed_fields = [
            'youtube_url', 'target_language', 'source_language', 'voice_style',
            'quality_level', 'upload_privacy', 'video_title', 'video_duration', 'video_id'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(self, field, data[field])
        
        self.updated_at = datetime.utcnow()

    def update_status(self, status: str, progress: Optional[int] = None, 
                     error_message: Optional[str] = None):
        """Update task status with validation."""
        valid_statuses = [
            'pending', 'downloading', 'processing', 'uploading', 
            'completed', 'failed', 'cancelled'
        ]
        
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        self.status = status
        
        if progress is not None:
            if not 0 <= progress <= 100:
                raise ValueError("Progress must be between 0 and 100")
            self.progress = progress
        
        if error_message is not None:
            self.error_message = error_message
        
        # Set timestamps based on status
        if status in ['downloading', 'processing'] and not self.started_at:
            self.started_at = datetime.utcnow()
        
        if status == 'completed':
            self.completed_at = datetime.utcnow()
            self.progress = 100
            
            # Calculate processing time
            if self.started_at:
                processing_delta = self.completed_at - self.started_at
                self.processing_time = int(processing_delta.total_seconds())
        
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def get_estimated_completion(self) -> Optional[str]:
        """Get estimated completion time based on video duration and current progress."""
        if not self.video_duration or self.progress == 0:
            return None
        
        if self.status == 'completed':
            return "Completed"
        
        if self.status in ['failed', 'cancelled']:
            return "N/A"
        
        # Rough estimation: processing time is usually 2-3x video duration
        estimated_total_time = self.video_duration * 2.5
        time_per_percent = estimated_total_time / 100
        remaining_time = time_per_percent * (100 - self.progress)
        
        if remaining_time < 60:
            return f"{int(remaining_time)} seconds"
        elif remaining_time < 3600:
            return f"{int(remaining_time / 60)} minutes"
        else:
            return f"{int(remaining_time / 3600)} hours"

    def get_duration_formatted(self) -> Optional[str]:
        """Get formatted video duration string."""
        if not self.video_duration:
            return None
        
        hours = self.video_duration // 3600
        minutes = (self.video_duration % 3600) // 60
        seconds = self.video_duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def is_active(self) -> bool:
        """Check if task is currently active (not completed, failed, or cancelled)."""
        return self.status in ['pending', 'downloading', 'processing', 'uploading']

    def can_be_cancelled(self) -> bool:
        """Check if task can be cancelled."""
        return self.status in ['pending', 'downloading', 'processing']

    @staticmethod
    def get_valid_statuses() -> list:
        """Get list of valid task statuses."""
        return ['pending', 'downloading', 'processing', 'uploading', 'completed', 'failed', 'cancelled']

    @staticmethod
    def get_active_tasks_count(user_id: int) -> int:
        """Get count of active tasks for a user."""
        return VideoTask.query.filter(
            VideoTask.user_id == user_id,
            VideoTask.status.in_(['pending', 'downloading', 'processing', 'uploading'])
        ).count()

    def cleanup_temp_files(self):
        """Clean up temporary files associated with this task."""
        import os
        
        file_paths = [
            self.original_video_path,
            self.original_audio_path,
            self.dubbed_audio_path
        ]
        
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not remove file {file_path}: {e}")
