from flask import Blueprint, request, jsonify, send_file
from flask_cors import cross_origin
import logging
import os
import tempfile
import shutil
from src.models.video_task import VideoTask, db
from src.services import (
    GeminiCLIService, 
    YouTubeService, 
    AudioService,
    AdaptiveMitigationService
)
from src.celery_app import celery  # Import from separate celery app file

logger = logging.getLogger(__name__)

dubbing_bp = Blueprint('dubbing', __name__)

# Initialize services
gemini_service = GeminiCLIService()
youtube_service = YouTubeService()
audio_service = AudioService()

@dubbing_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint for Railway monitoring."""
    try:
        # Check all service availability
        gemini_status = gemini_service.check_cli_availability()
        aws_credentials_valid = audio_service.validate_aws_credentials()
        
        # Database connection test
        try:
            db.session.execute('SELECT 1')
            db_status = True
        except Exception:
            db_status = False
        
        services_healthy = (
            gemini_status.get('available', False) and 
            aws_credentials_valid and 
            db_status
        )
        
        response_data = {
            'status': 'healthy' if services_healthy else 'degraded',
            'timestamp': db.func.now(),
            'services': {
                'gemini_cli': gemini_status,
                'database': db_status,
                'audio_service': {
                    'aws_polly': aws_credentials_valid,
                    'client_initialized': audio_service.polly_client is not None
                },
                'youtube_service': True,
                'adaptive_mitigation': True
            },
            'environment': os.getenv('RAILWAY_ENVIRONMENT_NAME', 'development')
        }
        
        status_code = 200 if services_healthy else 503
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy', 
            'error': str(e),
            'timestamp': db.func.now()
        }), 500

@dubbing_bp.route('/start-dubbing', methods=['POST'])
@cross_origin()
def start_dubbing():
    """Start the video dubbing process."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Extract and validate required parameters
        youtube_url = data.get('youtube_url')
        target_language = data.get('target_language')
        source_language = data.get('source_language', 'auto')
        user_id = data.get('user_id')
        
        # Additional parameters
        voice_style = data.get('voice_style', 'natural')
        quality_level = data.get('quality_level', 'high')

        # Validation
        if not all([youtube_url, target_language, user_id]):
            return jsonify({
                'error': 'youtube_url, target_language, and user_id are required'
            }), 400

        # Enhanced URL validation
        if not youtube_service.validate_video_url(youtube_url):
            return jsonify({'error': 'Invalid YouTube URL format'}), 400

        # Check if video is accessible
        video_info = youtube_service.get_video_info(youtube_url)
        if not video_info:
            return jsonify({'error': 'Unable to access video or video not found'}), 400

        # Check video duration limits
        max_duration = int(os.getenv('MAX_VIDEO_DURATION', 3600))
        if video_info.get('duration', 0) > max_duration:
            return jsonify({
                'error': f'Video too long. Maximum duration: {max_duration} seconds'
            }), 400

        # Create new video task with enhanced data
        task = VideoTask(
            youtube_url=youtube_url,
            target_language=target_language,
            source_language=source_language,
            user_id=user_id,
            status='pending',
            video_title=video_info.get('title', 'Unknown'),
            video_duration=video_info.get('duration', 0),
            voice_style=voice_style,
            quality_level=quality_level
        )

        db.session.add(task)
        db.session.commit()

        # Queue the dubbing task
        celery_task = dubbing_task.delay(task.id)
        
        # Update task with Celery task ID
        task.celery_task_id = celery_task.id
        db.session.commit()

        logger.info(f"Dubbing task started for video: {youtube_url} (Task ID: {task.id})")

        return jsonify({
            'task_id': task.id,
            'celery_task_id': celery_task.id,
            'status': 'started',
            'message': 'Dubbing process initiated',
            'video_info': {
                'title': video_info.get('title'),
                'duration': video_info.get('duration'),
                'estimated_completion': f"{video_info.get('duration', 0) * 2} seconds"
            }
        }), 202

    except Exception as e:
        logger.error(f"Error starting dubbing process: {e}")
        db.session.rollback()
        return jsonify({
            'error': 'Internal server error',
            'details': str(e) if os.getenv('FLASK_ENV') == 'development' else None
        }), 500

@dubbing_bp.route('/task-status/<int:task_id>', methods=['GET'])
@cross_origin()
def get_task_status(task_id):
    """Get the status of a dubbing task."""
    try:
        task = VideoTask.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # Get Celery task status if available
        celery_status = None
        if task.celery_task_id:
            try:
                celery_result = celery.AsyncResult(task.celery_task_id)
                celery_status = {
                    'state': celery_result.state,
                    'info': celery_result.info
                }
            except Exception as e:
                logger.warning(f"Could not get Celery status: {e}")

        response_data = task.to_dict()
        if celery_status:
            response_data['celery_status'] = celery_status

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dubbing_bp.route('/tasks', methods=['GET'])
@cross_origin()
def list_tasks():
    """List all dubbing tasks with pagination and filtering."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        status_filter = request.args.get('status')
        user_id_filter = request.args.get('user_id', type=int)

        query = VideoTask.query

        # Apply filters
        if status_filter:
            query = query.filter(VideoTask.status == status_filter)
        if user_id_filter:
            query = query.filter(VideoTask.user_id == user_id_filter)

        # Order by creation date (newest first)
        query = query.order_by(VideoTask.created_at.desc())

        # Paginate
        tasks = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )

        return jsonify({
            'tasks': [task.to_dict() for task in tasks.items],
            'pagination': {
                'total': tasks.total,
                'pages': tasks.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': tasks.has_next,
                'has_prev': tasks.has_prev
            },
            'filters': {
                'status': status_filter,
                'user_id': user_id_filter
            }
        }), 200

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dubbing_bp.route('/supported-languages', methods=['GET'])
@cross_origin()
def get_supported_languages():
    """Get list of supported languages for dubbing."""
    try:
        # Get languages from Gemini CLI
        gemini_languages = gemini_service.get_supported_languages()
        
        # Get available voices from AWS Polly
        polly_voices = audio_service.get_available_voices()

        # Enhanced language mappings with voice support
        common_languages = {
            'en-US': {'name': 'English (US)', 'voices': ['Joanna', 'Matthew', 'Amy']},
            'en-GB': {'name': 'English (UK)', 'voices': ['Emma', 'Brian']},
            'es-ES': {'name': 'Spanish (Spain)', 'voices': ['Lucia', 'Enrique']},
            'es-MX': {'name': 'Spanish (Mexico)', 'voices': ['Mia']},
            'fr-FR': {'name': 'French', 'voices': ['Lea', 'Mathieu']},
            'de-DE': {'name': 'German', 'voices': ['Marlene', 'Hans']},
            'it-IT': {'name': 'Italian', 'voices': ['Bianca', 'Giorgio']},
            'pt-BR': {'name': 'Portuguese (Brazil)', 'voices': ['Camila', 'Ricardo']},
            'ja-JP': {'name': 'Japanese', 'voices': ['Mizuki', 'Takumi']},
            'ko-KR': {'name': 'Korean', 'voices': ['Seoyeon']},
            'zh-CN': {'name': 'Chinese (Mandarin)', 'voices': ['Zhiyu']},
            'hi-IN': {'name': 'Hindi', 'voices': ['Aditi', 'Raveena']},
            'ar-AE': {'name': 'Arabic', 'voices': ['Zeina']},
            'ru-RU': {'name': 'Russian', 'voices': ['Tatyana', 'Maxim']}
        }

        return jsonify({
            'supported_languages': common_languages,
            'gemini_languages': gemini_languages or {},
            'polly_voices': polly_voices,
            'total_languages': len(common_languages)
        }), 200

    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        return jsonify({
            'error': 'Internal server error',
            'supported_languages': {},
            'fallback': True
        }), 500

@dubbing_bp.route('/cancel-task/<int:task_id>', methods=['POST'])
@cross_origin()
def cancel_task(task_id):
    """Cancel a running dubbing task."""
    try:
        task = VideoTask.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task.status in ['completed', 'failed', 'cancelled']:
            return jsonify({
                'error': f'Task already {task.status}',
                'current_status': task.status
            }), 400

        # Revoke the Celery task if it exists
        if task.celery_task_id:
            try:
                celery.control.revoke(task.celery_task_id, terminate=True)
                logger.info(f"Celery task {task.celery_task_id} revoked")
            except Exception as e:
                logger.warning(f"Failed to revoke Celery task: {e}")

        # Update task status
        task.update_status('cancelled', error_message='Task cancelled by user')

        # Clean up any temporary files
        if hasattr(task, 'temp_directory') and task.temp_directory:
            cleanup_temp_files(task.temp_directory)

        return jsonify({
            'message': 'Task cancelled successfully',
            'task_id': task_id,
            'status': 'cancelled'
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dubbing_bp.route('/download-dubbed-video/<int:task_id>', methods=['GET'])
@cross_origin()
def download_dubbed_video(task_id):
    """Download the final dubbed video for a completed task."""
    try:
        task = VideoTask.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task.status != 'completed':
            return jsonify({
                'error': 'Video not yet completed',
                'current_status': task.status,
                'progress': task.progress
            }), 400

        if not task.final_video_path or not os.path.exists(task.final_video_path):
            return jsonify({'error': 'Dubbed video file not found on server'}), 404

        # Generate download filename
        safe_title = "".join(c for c in task.video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}_dubbed_{task.target_language}.mp4"

        return send_file(
            task.final_video_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )

    except Exception as e:
        logger.error(f"Error downloading dubbed video for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def cleanup_temp_files(directory):
    """Clean up temporary files."""
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            logger.info(f"Cleaned up temporary directory: {directory}")
    except Exception as e:
        logger.warning(f"Failed to clean up directory {directory}: {e}")

# Celery task definition (should be moved to separate file)
@celery.task(bind=True)
def dubbing_task(self, task_id):
    """Celery task for processing video dubbing."""
    from src.models.video_task import VideoTask, db
    
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
        language_code = task.target_language
        if '-' not in language_code:
            language_code = f"{task.target_language}-US"

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
        task.update_status('completed', 100)

        logger.info(f"Dubbing task completed successfully: {task_id}")

        # Clean up temporary files
        cleanup_temp_files(download_dir)

    except Exception as e:
        logger.error(f"Error in dubbing task {task_id}: {e}")
        task = VideoTask.query.get(task_id)
        if task:
            task.update_status('failed', error_message=str(e))
