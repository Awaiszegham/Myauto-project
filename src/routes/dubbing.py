from flask import Blueprint, request, jsonify, send_file
from flask_cors import cross_origin
import logging
import os
from src.models.video_task import VideoTask, db
from src.services.gemini_cli_service import GeminiCLIService
from src.services.youtube_service import YouTubeService
from src.services.audio_service import AudioService
from celery import Celery

logger = logging.getLogger(__name__)

dubbing_bp = Blueprint('dubbing', __name__)

# Initialize services
gemini_service = GeminiCLIService()
youtube_service = YouTubeService()
audio_service = AudioService()

# Initialize Celery (this would typically be in a separate file)
celery = Celery('youtube_dubbing')
celery.conf.update(
    broker_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@dubbing_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint."""
    try:
        gemini_status = gemini_service.check_cli_availability()
        
        return jsonify({
            'status': 'healthy' if gemini_status['available'] else 'unhealthy',
            'services': {
                'gemini_cli': gemini_status,
                'database': True,  # If we reach here, DB is working
                'audio_service': audio_service.polly_client is not None
            }
        }), 200 if gemini_status['available'] else 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@dubbing_bp.route('/start-dubbing', methods=['POST'])
@cross_origin()
def start_dubbing():
    """Start the video dubbing process."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        youtube_url = data.get('youtube_url')
        target_language = data.get('target_language')
        source_language = data.get('source_language', 'auto')
        user_id = data.get('user_id') # Assuming user_id is provided in the request
        
        if not youtube_url or not target_language or not user_id:
            return jsonify({'error': 'youtube_url, target_language, and user_id are required'}), 400
        
        # Validate YouTube URL
        if 'youtube.com/watch' not in youtube_url and 'youtu.be/' not in youtube_url:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Create new video task
        task = VideoTask(
            youtube_url=youtube_url,
            target_language=target_language,
            source_language=source_language,
            user_id=user_id,
            status='pending'
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Queue the dubbing task
        dubbing_task.delay(task.id)
        
        logger.info(f"Dubbing task started for video: {youtube_url}")
        
        return jsonify({
            'task_id': task.id,
            'status': 'started',
            'message': 'Dubbing process initiated'
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting dubbing process: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dubbing_bp.route('/task-status/<task_id>', methods=['GET'])
@cross_origin()
def get_task_status(task_id):
    """Get the status of a dubbing task."""
    try:
        task = VideoTask.query.get(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dubbing_bp.route('/tasks', methods=['GET'])
@cross_origin()
def list_tasks():
    """List all dubbing tasks."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status_filter = request.args.get('status')
        
        query = VideoTask.query
        
        if status_filter:
            query = query.filter(VideoTask.status == status_filter)
        
        tasks = query.order_by(VideoTask.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'tasks': [task.to_dict() for task in tasks.items],
            'total': tasks.total,
            'pages': tasks.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dubbing_bp.route('/supported-languages', methods=['GET'])
@cross_origin()
def get_supported_languages():
    """Get list of supported languages."""
    try:
        # Get languages from Gemini CLI
        gemini_languages = gemini_service.get_supported_languages()
        
        # Get available voices from AWS Polly
        polly_voices = audio_service.get_available_voices()
        
        # Common language mappings
        common_languages = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'hi': 'Hindi',
            'ar': 'Arabic',
            'ru': 'Russian'
        }
        
        return jsonify({
            'gemini_languages': gemini_languages or common_languages,
            'polly_voices': polly_voices,
            'common_languages': common_languages
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@celery.task(bind=True)
def dubbing_task(self, task_id):
    """Celery task for processing video dubbing."""
    try:
        # Get task from database
        task = VideoTask.query.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # Update task status
        task.update_status('downloading', 10)
        
        # Step 1: Download video
        logger.info(f"Downloading video: {task.youtube_url}")
        download_dir = f"/tmp/dubbing/{task_id}"
        os.makedirs(download_dir, exist_ok=True)
        
        download_result = youtube_service.download_video(task.youtube_url, download_dir)
        if not download_result:
            task.update_status('failed', error_message='Failed to download video')
            return
        
        task.original_video_path = download_result['video_path']
        task.update_status('processing', 30)
        
        # Step 2: Extract and preprocess audio
        logger.info("Extracting audio from video")
        audio_path = audio_service.extract_audio_from_video(task.original_video_path)
        if not audio_path:
            task.update_status('failed', error_message='Failed to extract audio')
            return
        
        processed_audio_path = audio_service.preprocess_audio(audio_path)
        if not processed_audio_path:
            processed_audio_path = audio_path
        
        task.original_audio_path = processed_audio_path
        task.update_status('processing', 50)
        
        # Step 3: Transcribe audio using Gemini CLI
        logger.info("Transcribing audio")
        transcription_result = gemini_service.transcribe_audio(
            processed_audio_path, 
            task.source_language
        )
        if not transcription_result:
            task.update_status('failed', error_message='Failed to transcribe audio')
            return
        
        task.transcription_text = transcription_result['text']
        task.update_status('processing', 70)
        
        # Step 4: Translate text using Gemini CLI
        logger.info("Translating text")
        translation_result = gemini_service.translate_text(
            task.transcription_text,
            task.target_language,
            task.source_language
        )
        if not translation_result:
            task.update_status('failed', error_message='Failed to translate text')
            return
        
        task.translated_text = translation_result['translated_text']
        task.update_status('processing', 80)
        
        # Step 5: Generate speech from translated text
        logger.info("Generating dubbed audio")
        language_code = f"{task.target_language}-US"  # Simplified mapping
        dubbed_audio_path = audio_service.text_to_speech(
            task.translated_text,
            language_code
        )
        if not dubbed_audio_path:
            task.update_status('failed', error_message='Failed to generate dubbed audio')
            return
        
        task.dubbed_audio_path = dubbed_audio_path
        task.update_status('processing', 90)
        
        # Step 6: Merge dubbed audio with original video
        logger.info("Merging audio with video")
        final_video_path = audio_service.merge_audio_with_video(
            task.original_video_path,
            dubbed_audio_path
        )
        if not final_video_path:
            task.update_status('failed', error_message='Failed to merge audio with video')
            return
        
        task.final_video_path = final_video_path
        task.update_status('uploading', 95)
        
        # Step 7: Upload to YouTube (optional)
        # This step would require YouTube API credentials
        # For now, we'll mark as completed
        
        task.update_status('completed', 100)
        logger.info(f"Dubbing task completed successfully: {task_id}")
        
        # Clean up temporary files
        cleanup_temp_files(download_dir)
        
    except Exception as e:
        logger.error(f"Error in dubbing task {task_id}: {e}")
        task = VideoTask.query.get(task_id)
        if task:
            task.update_status('failed', error_message=str(e))

def cleanup_temp_files(directory):
    """Clean up temporary files."""
    try:
        import shutil
        if os.path.exists(directory):
            shutil.rmtree(directory)
            logger.info(f"Cleaned up temporary directory: {directory}")
    except Exception as e:
        logger.warning(f"Failed to clean up directory {directory}: {e}")

@dubbing_bp.route('/cancel-task/<task_id>', methods=['POST'])
@cross_origin()
def cancel_task(task_id):
    """Cancel a running dubbing task."""
    try:
        task = VideoTask.query.get(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        if task.status in ['completed', 'failed']:
            return jsonify({'error': 'Task already finished'}), 400
        
        # Revoke the Celery task
        celery.control.revoke(task_id, terminate=True)
        
        # Update task status
        task.update_status('cancelled', error_message='Task cancelled by user')
        
        return jsonify({'message': 'Task cancelled successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dubbing_bp.route('/download-dubbed-video/<task_id>', methods=['GET'])
@cross_origin()
def download_dubbed_video(task_id):
    """Download the final dubbed video for a completed task."""
    try:
        task = VideoTask.query.get(task_id)

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task.status != 'completed' or not task.final_video_path:
            return jsonify({'error': 'Video not yet dubbed or task not completed'}), 400
        
        if not os.path.exists(task.final_video_path):
            return jsonify({'error': 'Dubbed video file not found on server'}), 404

        return send_file(task.final_video_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Error downloading dubbed video for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

