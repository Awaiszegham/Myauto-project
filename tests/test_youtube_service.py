import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, mock_open
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.youtube_service import YouTubeService

class TestYouTubeService(unittest.TestCase):
    """Comprehensive tests for YouTube service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = YouTubeService()
        self.test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.test_output_dir = "/tmp/test_downloads"
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_output_dir):
            import shutil
            shutil.rmtree(self.test_output_dir)
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('time.sleep')
    @patch('random.uniform')
    @patch('random.choice')
    def test_download_video_success(self, mock_choice, mock_uniform, mock_sleep, 
                                   mock_listdir, mock_makedirs, mock_ytdl_class):
        """Test successful video download."""
        # Setup mocks
        mock_uniform.return_value = 2.0
        mock_choice.return_value = self.service.user_agents[0]
        mock_listdir.return_value = ["test_video.mp4"]
        
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        
        # Mock video info
        mock_info = {
            'title': 'Test Video',
            'duration': 180,
            'id': 'dQw4w9WgXcQ',
            'uploader': 'Test Channel'
        }
        mock_ytdl.extract_info.return_value = mock_info
        
        result = self.service.download_video(self.test_url, self.test_output_dir)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Test Video')
        self.assertEqual(result['duration'], 180)
        self.assertEqual(result['video_id'], 'dQw4w9WgXcQ')
        self.assertTrue(result['video_path'].endswith('test_video.mp4'))
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with(self.test_output_dir, exist_ok=True)
        
        # Verify yt-dlp was called correctly
        mock_ytdl.extract_info.assert_called_once_with(self.test_url, download=False)
        mock_ytdl.download.assert_called_once_with([self.test_url])
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('time.sleep')
    @patch('random.uniform')
    @patch('random.choice')
    def test_download_video_extract_info_failure(self, mock_choice, mock_uniform, 
                                                mock_sleep, mock_makedirs, mock_ytdl_class):
        """Test download failure during info extraction."""
        mock_uniform.return_value = 2.0
        mock_choice.return_value = self.service.user_agents[0]
        
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        mock_ytdl.extract_info.return_value = None
        
        result = self.service.download_video(self.test_url, self.test_output_dir)
        
        self.assertIsNone(result)
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('time.sleep')
    @patch('random.uniform')
    @patch('random.choice')
    def test_download_video_no_files_found(self, mock_choice, mock_uniform, mock_sleep,
                                          mock_listdir, mock_makedirs, mock_ytdl_class):
        """Test download when no video files are found after download."""
        mock_uniform.return_value = 2.0
        mock_choice.return_value = self.service.user_agents[0]
        mock_listdir.return_value = ["info.json", "description.txt"]  # No video files
        
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        
        mock_info = {
            'title': 'Test Video',
            'duration': 180,
            'id': 'dQw4w9WgXcQ'
        }
        mock_ytdl.extract_info.return_value = mock_info
        
        result = self.service.download_video(self.test_url, self.test_output_dir)
        
        self.assertIsNone(result)
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('time.sleep')
    @patch('random.uniform')
    @patch('random.choice')
    def test_download_video_exception(self, mock_choice, mock_uniform, mock_sleep,
                                     mock_makedirs, mock_ytdl_class):
        """Test download with exception."""
        mock_uniform.return_value = 2.0
        mock_choice.return_value = self.service.user_agents[0]
        
        mock_ytdl_class.side_effect = Exception("Download failed")
        
        result = self.service.download_video(self.test_url, self.test_output_dir)
        
        self.assertIsNone(result)
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_extract_audio_success(self, mock_exists, mock_makedirs, mock_ytdl_class):
        """Test successful audio extraction."""
        video_path = "/tmp/test_video.mp4"
        mock_exists.return_value = True
        
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        
        # Mock the extracted audio file exists
        with patch('os.path.exists') as mock_exists_audio:
            mock_exists_audio.side_effect = lambda path: path.endswith('.wav')
            
            result = self.service.extract_audio(video_path, self.test_output_dir)
            
            self.assertIsNotNone(result)
            self.assertTrue(result.endswith('.wav'))
    
    @patch('os.path.exists')
    def test_extract_audio_video_not_found(self, mock_exists):
        """Test audio extraction with non-existent video file."""
        mock_exists.return_value = False
        
        result = self.service.extract_audio("/nonexistent/video.mp4", self.test_output_dir)
        
        self.assertIsNone(result)
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_extract_audio_exception(self, mock_exists, mock_makedirs, mock_ytdl_class):
        """Test audio extraction with exception."""
        mock_exists.return_value = True
        mock_ytdl_class.side_effect = Exception("Audio extraction failed")
        
        result = self.service.extract_audio("/tmp/test_video.mp4", self.test_output_dir)
        
        self.assertIsNone(result)
    
    @patch('yt_dlp.YoutubeDL')
    def test_get_video_info_success(self, mock_ytdl_class):
        """Test successful video info retrieval."""
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        
        mock_info = {
            'title': 'Test Video',
            'duration': 180,
            'id': 'dQw4w9WgXcQ',
            'uploader': 'Test Channel',
            'upload_date': '20210101',
            'view_count': 1000000,
            'description': 'Test description',
            'thumbnail': 'https://example.com/thumb.jpg'
        }
        mock_ytdl.extract_info.return_value = mock_info
        
        result = self.service.get_video_info(self.test_url)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Test Video')
        self.assertEqual(result['duration'], 180)
        self.assertEqual(result['video_id'], 'dQw4w9WgXcQ')
        self.assertEqual(result['uploader'], 'Test Channel')
        self.assertEqual(result['upload_date'], '20210101')
        self.assertEqual(result['view_count'], 1000000)
        
        # Verify yt-dlp was called with download=False
        mock_ytdl.extract_info.assert_called_once_with(self.test_url, download=False)
    
    @patch('yt_dlp.YoutubeDL')
    def test_get_video_info_failure(self, mock_ytdl_class):
        """Test video info retrieval failure."""
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        mock_ytdl.extract_info.return_value = None
        
        result = self.service.get_video_info(self.test_url)
        
        self.assertIsNone(result)
    
    @patch('yt_dlp.YoutubeDL')
    def test_get_video_info_exception(self, mock_ytdl_class):
        """Test video info retrieval with exception."""
        mock_ytdl_class.side_effect = Exception("Info extraction failed")
        
        result = self.service.get_video_info(self.test_url)
        
        self.assertIsNone(result)
    
    @patch('googleapiclient.discovery.build')
    @patch('google.oauth2.credentials.Credentials.from_authorized_user_file')
    @patch('os.path.exists')
    def test_get_youtube_api_with_existing_token(self, mock_exists, mock_creds_from_file, mock_build):
        """Test YouTube API initialization with existing token."""
        # Setup service with credentials
        service = YouTubeService(
            credentials_file="/tmp/credentials.json",
            token_file="/tmp/token.json"
        )
        
        mock_exists.return_value = True
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds_from_file.return_value = mock_creds
        
        mock_youtube_api = MagicMock()
        mock_build.return_value = mock_youtube_api
        
        result = service._get_youtube_api()
        
        self.assertEqual(result, mock_youtube_api)
        mock_build.assert_called_once_with('youtube', 'v3', credentials=mock_creds)
    
    @patch('googleapiclient.discovery.build')
    @patch('googleapiclient.http.MediaFileUpload')
    @patch('os.path.exists')
    def test_upload_video_success(self, mock_exists, mock_media_upload, mock_build):
        """Test successful video upload."""
        # Setup service with mock API
        self.service.youtube_api = MagicMock()
        
        mock_exists.return_value = True
        mock_media = MagicMock()
        mock_media_upload.return_value = mock_media
        
        # Mock the upload process
        mock_insert_request = MagicMock()
        mock_insert_request.next_chunk.side_effect = [
            (MagicMock(progress=lambda: 0.5), None),  # 50% progress
            (None, {'id': 'uploaded_video_id'})       # Complete
        ]
        
        self.service.youtube_api.videos.return_value.insert.return_value = mock_insert_request
        
        result = self.service.upload_video(
            "/tmp/test_video.mp4",
            "Test Video Title",
            "Test description",
            ["test", "video"],
            "private"
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['video_id'], 'uploaded_video_id')
        self.assertEqual(result['video_url'], 'https://www.youtube.com/watch?v=uploaded_video_id')
        self.assertEqual(result['title'], 'Test Video Title')
    
    @patch('os.path.exists')
    def test_upload_video_file_not_found(self, mock_exists):
        """Test video upload with non-existent file."""
        mock_exists.return_value = False
        
        result = self.service.upload_video(
            "/nonexistent/video.mp4",
            "Test Video"
        )
        
        self.assertIsNone(result)
    
    def test_upload_video_no_api(self):
        """Test video upload without YouTube API initialized."""
        # Don't initialize the API
        self.service.credentials_file = None
        
        with self.assertRaises(ValueError):
            self.service.upload_video("/tmp/test_video.mp4", "Test Video")

class TestYouTubeServiceBotDetectionMitigation(unittest.TestCase):
    """Tests for bot detection mitigation features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = YouTubeService()
    
    @patch.dict(os.environ, {'PROXY_URL': 'http://proxy.example.com:8080'})
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('time.sleep')
    @patch('random.uniform')
    @patch('random.choice')
    def test_download_with_proxy(self, mock_choice, mock_uniform, mock_sleep,
                                mock_listdir, mock_makedirs, mock_ytdl_class):
        """Test download with proxy configuration."""
        mock_uniform.return_value = 2.0
        mock_choice.return_value = self.service.user_agents[0]
        mock_listdir.return_value = ["test_video.mp4"]
        
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        
        mock_info = {
            'title': 'Test Video',
            'duration': 180,
            'id': 'test_id'
        }
        mock_ytdl.extract_info.return_value = mock_info
        
        self.service.download_video("https://www.youtube.com/watch?v=test", "/tmp")
        
        # Verify yt-dlp was initialized with proxy
        call_args = mock_ytdl_class.call_args[0][0]  # Get the ydl_opts
        self.assertEqual(call_args['proxy'], 'http://proxy.example.com:8080')
    
    @patch.dict(os.environ, {'YOUTUBE_COOKIES_FILE': '/tmp/cookies.txt'})
    @patch('os.path.exists')
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('time.sleep')
    @patch('random.uniform')
    @patch('random.choice')
    def test_download_with_cookies(self, mock_choice, mock_uniform, mock_sleep,
                                  mock_listdir, mock_makedirs, mock_ytdl_class, mock_exists):
        """Test download with cookies configuration."""
        mock_exists.return_value = True  # Cookies file exists
        mock_uniform.return_value = 2.0
        mock_choice.return_value = self.service.user_agents[0]
        mock_listdir.return_value = ["test_video.mp4"]
        
        mock_ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        
        mock_info = {
            'title': 'Test Video',
            'duration': 180,
            'id': 'test_id'
        }
        mock_ytdl.extract_info.return_value = mock_info
        
        self.service.download_video("https://www.youtube.com/watch?v=test", "/tmp")
        
        # Verify yt-dlp was initialized with cookies
        call_args = mock_ytdl_class.call_args[0][0]  # Get the ydl_opts
        self.assertEqual(call_args['cookiefile'], '/tmp/cookies.txt')
    
    @patch('time.sleep')
    @patch('random.uniform')
    def test_random_delay_called(self, mock_uniform, mock_sleep):
        """Test that random delays are implemented."""
        mock_uniform.return_value = 2.5
        
        with patch('yt_dlp.YoutubeDL') as mock_ytdl_class:
            mock_ytdl = MagicMock()
            mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
            mock_ytdl.extract_info.return_value = None  # Fail early
            
            self.service.download_video("https://www.youtube.com/watch?v=test", "/tmp")
            
            # Verify random delay was called
            mock_uniform.assert_called_with(1, 3)
            mock_sleep.assert_called_with(2.5)
    
    def test_user_agent_rotation(self):
        """Test that user agents are rotated."""
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "Custom User Agent"
            
            with patch('yt_dlp.YoutubeDL') as mock_ytdl_class:
                mock_ytdl = MagicMock()
                mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
                mock_ytdl.extract_info.return_value = None
                
                self.service.download_video("https://www.youtube.com/watch?v=test", "/tmp")
                
                # Verify user agent was selected from the list
                mock_choice.assert_called_with(self.service.user_agents)
                
                # Verify it was used in yt-dlp options
                call_args = mock_ytdl_class.call_args[0][0]
                self.assertEqual(call_args['user_agent'], "Custom User Agent")

if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)

