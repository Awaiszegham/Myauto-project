import os
import yt_dlp
import logging
import random
import time
import tempfile
import json
import re
import subprocess
from typing import Optional, Dict, Any, List
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from src.services.adaptive_mitigation_service import AdaptiveMitigationService

logger = logging.getLogger(__name__)

class YouTubeService:
    """Service for downloading videos from YouTube and uploading dubbed versions."""
    
    def __init__(self, credentials_file: str = None, token_file: str = None):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.youtube_api = None
        self.adaptive_mitigation_service = AdaptiveMitigationService()
    
    def _get_youtube_api(self):
        """Initialize YouTube API client with authentication."""
        if self.youtube_api:
            return self.youtube_api
        
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        creds = None
        
        try:
            # Load credentials from environment variable if available
            youtube_credentials_json = os.getenv('YOUTUBE_CREDENTIALS_JSON')
            if youtube_credentials_json:
                # Load token from environment variable if available
                youtube_token_json = os.getenv('YOUTUBE_TOKEN_JSON')
                if youtube_token_json:
                    creds = Credentials.from_authorized_user_info(
                        json.loads(youtube_token_json), SCOPES
                    )
                
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        # For Railway deployment, use service account or pre-configured tokens
                        logger.warning("YouTube API credentials need refresh but running in production")
                        return None
            
            # Fallback to file-based credentials for local development
            elif self.token_file and os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        if not self.credentials_file:
                            logger.error("YouTube credentials file not provided")
                            return None
                        
                        # Only run interactive flow in development
                        if not os.getenv('RAILWAY_ENVIRONMENT_NAME'):
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.credentials_file, SCOPES
                            )
                            creds = flow.run_local_server(port=0)
                            
                            if self.token_file:
                                with open(self.token_file, 'w') as token:
                                    token.write(creds.to_json())
                        else:
                            logger.error("Cannot run interactive auth flow in production")
                            return None
            
            if creds:
                self.youtube_api = build('youtube', 'v3', credentials=creds)
                return self.youtube_api
            else:
                logger.error("No valid YouTube API credentials available")
                return None
                
        except Exception as e:
            logger.error(f"Error initializing YouTube API: {e}")
            return None
    
    def validate_video_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube video URL."""
        try:
            youtube_regex = re.compile(
                r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
                r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
            )
            return bool(youtube_regex.match(url))
        except:
            return False
    
    def download_video(self, url: str, output_dir: str, quality: str = 'best') -> Optional[Dict[str, Any]]:
        """
        Download video from YouTube with enhanced error handling.
        
        Args:
            url: YouTube video URL
            output_dir: Directory to save the downloaded video
            quality: Video quality preference
            
        Returns:
            Dictionary containing download information or None if failed
        """
        try:
            # Validate URL first
            if not self.validate_video_url(url):
                logger.error(f"Invalid YouTube URL: {url}")
                return None
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Get adaptive mitigation parameters
            adaptive_params = self.adaptive_mitigation_service.get_adaptive_params()
            
            # Apply adaptive delay
            time.sleep(adaptive_params.get('sleep_interval', random.uniform(1, 3)))
            
            # Configure yt-dlp with enhanced options
            ydl_opts = {
                'format': quality,
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'writeinfojson': True,
                'ignoreerrors': True,
                'no_warnings': False,
                'extractaudio': False,
                'user_agent': adaptive_params.get('user_agent'),
                'referer': 'https://www.youtube.com/',
                'sleep_interval': adaptive_params.get('sleep_interval', random.uniform(1, 3)),
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                'http_headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            }
            
            # Add proxy support if configured
            proxy_url = os.getenv('PROXY_URL')
            if adaptive_params.get('proxy_enabled', False) and proxy_url:
                ydl_opts['proxy'] = proxy_url
            
            # Add cookies if available
            cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
            if adaptive_params.get('cookies_enabled', False) and cookies_file and os.path.exists(cookies_file):
                ydl_opts['cookiefile'] = cookies_file
            
            logger.info(f"Starting download for URL: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info first
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    logger.error("Failed to extract video information")
                    self._log_download_outcome(url, False, "Failed to extract video information", ydl_opts)
                    return None
                
                # Check video availability
                if info.get('is_live'):
                    logger.error("Cannot download live streams")
                    return None
                
                video_title = info.get('title', 'Unknown')
                video_duration = info.get('duration', 0)
                video_id = info.get('id', '')
                
                # Check duration limits (optional)
                max_duration = int(os.getenv('MAX_VIDEO_DURATION', 3600))  # 1 hour default
                if video_duration > max_duration:
                    logger.error(f"Video too long: {video_duration}s (max: {max_duration}s)")
                    return None
                
                logger.info(f"Video info extracted: {video_title} ({video_duration}s)")
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_files = []
                for file in os.listdir(output_dir):
                    if file.endswith(('.mp4', '.mkv', '.webm', '.avi')) and video_title.replace(' ', '_') in file:
                        downloaded_files.append(os.path.join(output_dir, file))
                
                if not downloaded_files:
                    logger.error("No video file found after download")
                    return None
                
                video_path = downloaded_files[0]
                logger.info(f"Video downloaded successfully: {video_path}")
                
                self._log_download_outcome(url, True, None, ydl_opts)
                
                return {
                    'video_path': video_path,
                    'title': video_title,
                    'duration': video_duration,
                    'video_id': video_id,
                    'info': info
                }
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error downloading video: {error_message}")
            self._log_download_outcome(url, False, error_message, ydl_opts if 'ydl_opts' in locals() else {})
            return None
    
    def _log_download_outcome(self, url: str, success: bool, error_message: str, ydl_opts: dict):
        """Log download outcome for adaptive mitigation."""
        log_data = {
            'timestamp': time.time(),
            'url': url,
            'success': success,
            'error_message': error_message,
            'mitigation_params': {
                'user_agent': ydl_opts.get('user_agent'),
                'sleep_interval': ydl_opts.get('sleep_interval'),
                'proxy_used': 'proxy' in ydl_opts,
                'cookies_used': 'cookiefile' in ydl_opts
            }
        }
        
        self.adaptive_mitigation_service.record_outcome(log_data)
    
    def extract_audio(self, video_path: str, output_dir: str) -> Optional[str]:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to the video file
            output_dir: Directory to save the extracted audio
            
        Returns:
            Path to the extracted audio file or None if failed
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            audio_path = os.path.join(output_dir, f"{video_name}.wav")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.process_info({'filepath': video_path})
            
            if os.path.exists(audio_path):
                logger.info(f"Audio extracted successfully: {audio_path}")
                return audio_path
            else:
                logger.error("Audio extraction failed - file not found")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return None
    
    def upload_video(self, video_path: str, title: str, description: str = "",
                    tags: List[str] = None, privacy_status: str = "private") -> Optional[Dict[str, Any]]:
        """
        Upload video to YouTube.
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            privacy_status: Privacy status (private, public, unlisted)
            
        Returns:
            Dictionary containing upload information or None if failed
        """
        try:
            youtube = self._get_youtube_api()
            if not youtube:
                raise ValueError("YouTube API not initialized. Ensure credentials are set up.")
            
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None
            
            tags = tags or []
            
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '22'  # People & Blogs category
                },
                'status': {
                    'privacyStatus': privacy_status
                }
            }
            
            # Create media upload object
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            
            logger.info(f"Starting upload for video: {title}")
            
            # Execute the upload
            insert_request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            error = None
            retry = 0
            
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    if status:
                        logger.info(f"Upload progress: {int(status.progress() * 100)}%")
                except Exception as e:
                    error = e
                    if retry < 3:
                        retry += 1
                        logger.warning(f"Upload error, retrying ({retry}/3): {e}")
                        time.sleep(2 ** retry)
                    else:
                        logger.error(f"Upload failed after retries: {e}")
                        return None
            
            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"Video uploaded successfully: {video_url}")
                
                return {
                    'video_id': video_id,
                    'video_url': video_url,
                    'title': title,
                    'response': response
                }
            else:
                logger.error("Upload completed but no response received")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return None
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information without downloading.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary containing video information or None if failed
        """
        try:
            if not self.validate_video_url(url):
                logger.error(f"Invalid YouTube URL: {url}")
                return None
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    return {
                        'title': info.get('title', ''),
                        'duration': info.get('duration', 0),
                        'video_id': info.get('id', ''),
                        'uploader': info.get('uploader', ''),
                        'upload_date': info.get('upload_date', ''),
                        'view_count': info.get('view_count', 0),
                        'description': info.get('description', ''),
                        'thumbnail': info.get('thumbnail', '')
                    }
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
