import os
import yt_dlp
import logging
import random
import time
import tempfile
import json
from typing import Optional, Dict, Any, List
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

class YouTubeService:
    """Service for downloading videos from YouTube and uploading dubbed versions."""
    
    def __init__(self, credentials_file: str = None, token_file: str = None):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.youtube_api = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
    def _get_youtube_api(self):
        """Initialize YouTube API client with authentication."""
        if self.youtube_api:
            return self.youtube_api
            
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        creds = None
        
        # Load credentials from environment variable if available
        youtube_credentials_json = os.getenv('YOUTUBE_CREDENTIALS_JSON')
        if youtube_credentials_json:
            import json
            from google.oauth2.credentials import Credentials as OAuth2Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            # Load token from environment variable if available
            youtube_token_json = os.getenv('YOUTUBE_TOKEN_JSON')
            if youtube_token_json:
                creds = OAuth2Credentials.from_authorized_user_info(json.loads(youtube_token_json), SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Create a temporary file for credentials
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_creds_file:
                        temp_creds_file.write(youtube_credentials_json)
                        temp_creds_path = temp_creds_file.name
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(temp_creds_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                    finally:
                        os.unlink(temp_creds_path) # Clean up the temporary file
                
                # Save the credentials back to environment variable for the next run
                if creds and os.getenv('RAILWAY_ENVIRONMENT_NAME'): # Only save if on Railway
                    os.environ['YOUTUBE_TOKEN_JSON'] = creds.to_json()
        else:
            # Fallback to file-based credentials for local development
            if self.token_file and os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_file:
                        raise ValueError("YouTube credentials file not provided")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                if self.token_file:
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
        
        self.youtube_api = build('youtube', 'v3', credentials=creds)
        return self.youtube_api
    
    def download_video(self, url: str, output_dir: str, quality: str = 'best') -> Optional[Dict[str, Any]]:
        """
        Download video from YouTube with bot detection mitigation.
        
        Args:
            url: YouTube video URL
            output_dir: Directory to save the downloaded video
            quality: Video quality preference
            
        Returns:
            Dictionary containing download information or None if failed
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Random delay to avoid detection
            time.sleep(random.uniform(1, 3))
            
            # Configure yt-dlp with bot detection mitigation
            ydl_opts = {
                'format': quality,
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'writeinfojson': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': True,
                'no_warnings': False,
                'extractaudio': False,
                'audioformat': 'mp3',
                'audioquality': '192K',
                
                # Bot detection mitigation
                'user_agent': random.choice(self.user_agents),
                'referer': 'https://www.youtube.com/',
                'sleep_interval': random.uniform(1, 3),
                'max_sleep_interval': 5,
                'sleep_interval_subtitles': random.uniform(1, 2),
                
                # Retry configuration
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                
                # Additional headers to appear more browser-like
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
            if proxy_url:
                ydl_opts['proxy'] = proxy_url
            
            # Add cookies if available
            cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
            if cookies_file and os.path.exists(cookies_file):
                ydl_opts['cookiefile'] = cookies_file
            
            logger.info(f"Starting download for URL: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info first
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    logger.error("Failed to extract video information")
                    return None
                
                video_title = info.get('title', 'Unknown')
                video_duration = info.get('duration', 0)
                video_id = info.get('id', '')
                
                logger.info(f"Video info extracted: {video_title} ({video_duration}s)")
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_files = []
                for file in os.listdir(output_dir):
                    if file.endswith(('.mp4', '.mkv', '.webm', '.avi')):
                        downloaded_files.append(os.path.join(output_dir, file))
                
                if not downloaded_files:
                    logger.error("No video file found after download")
                    return None
                
                video_path = downloaded_files[0]  # Take the first video file
                
                logger.info(f"Video downloaded successfully: {video_path}")
                
                return {
                    'video_path': video_path,
                    'title': video_title,
                    'duration': video_duration,
                    'video_id': video_id,
                    'info': info
                }
                
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
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

