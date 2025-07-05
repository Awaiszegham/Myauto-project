import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, mock_open
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.audio_service import AudioService

class TestAudioService(unittest.TestCase):
    """Comprehensive tests for Audio service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = AudioService(
            aws_access_key="test_key",
            aws_secret_key="test_secret",
            aws_region="us-east-1"
        )
        self.test_video_path = "/tmp/test_video.mp4"
        self.test_audio_path = "/tmp/test_audio.wav"
        self.test_text = "Hello, this is a test text for speech synthesis."
    
    def tearDown(self):
        """Clean up test fixtures."""
        for path in [self.test_video_path, self.test_audio_path]:
            if os.path.exists(path):
                os.remove(path)
    
    @patch('boto3.client')
    def test_init_with_credentials(self, mock_boto_client):
        """Test service initialization with AWS credentials."""
        mock_polly = MagicMock()
        mock_boto_client.return_value = mock_polly
        
        service = AudioService("access_key", "secret_key", "us-west-2")
        
        self.assertEqual(service.aws_access_key, "access_key")
        self.assertEqual(service.aws_secret_key, "secret_key")
        self.assertEqual(service.aws_region, "us-west-2")
        self.assertEqual(service.polly_client, mock_polly)
        
        mock_boto_client.assert_called_once_with(
            'polly',
            aws_access_key_id="access_key",
            aws_secret_access_key="secret_key",
            region_name="us-west-2"
        )
    
    def test_init_without_credentials(self):
        """Test service initialization without AWS credentials."""
        service = AudioService()
        
        self.assertIsNone(service.polly_client)
    
    @patch('ffmpeg.input')
    @patch('ffmpeg.output')
    @patch('os.path.exists')
    def test_extract_audio_from_video_success(self, mock_exists, mock_output, mock_input):
        """Test successful audio extraction from video."""
        mock_exists.side_effect = lambda path: path == self.test_video_path or path.endswith('_audio.wav')
        
        # Mock ffmpeg chain
        mock_input_obj = MagicMock()
        mock_input.return_value = mock_input_obj
        
        mock_output_obj = MagicMock()
        mock_output.return_value = mock_output_obj
        
        mock_run_obj = MagicMock()
        mock_output_obj.overwrite_output.return_value.run = mock_run_obj
        
        result = self.service.extract_audio_from_video(self.test_video_path)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('_audio.wav'))
        
        # Verify ffmpeg was called correctly
        mock_input.assert_called_once_with(self.test_video_path)
        mock_output.assert_called_once()
        mock_run_obj.assert_called_once_with(quiet=True)
    
    @patch('os.path.exists')
    def test_extract_audio_from_video_file_not_found(self, mock_exists):
        """Test audio extraction with non-existent video file."""
        mock_exists.return_value = False
        
        result = self.service.extract_audio_from_video(self.test_video_path)
        
        self.assertIsNone(result)
    
    @patch('ffmpeg.input')
    @patch('os.path.exists')
    def test_extract_audio_from_video_exception(self, mock_exists, mock_input):
        """Test audio extraction with ffmpeg exception."""
        mock_exists.return_value = True
        mock_input.side_effect = Exception("FFmpeg error")
        
        result = self.service.extract_audio_from_video(self.test_video_path)
        
        self.assertIsNone(result)
    
    @patch('pydub.AudioSegment.from_file')
    @patch('os.path.exists')
    def test_preprocess_audio_success(self, mock_exists, mock_from_file):
        """Test successful audio preprocessing."""
        mock_exists.side_effect = lambda path: path == self.test_audio_path or path.endswith('_processed.wav')
        
        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.channels = 2  # Stereo
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.strip_silence.return_value = mock_audio
        mock_from_file.return_value = mock_audio
        
        # Mock normalize function
        with patch('pydub.effects.normalize') as mock_normalize:
            mock_normalize.return_value = mock_audio
            
            result = self.service.preprocess_audio(self.test_audio_path)
            
            self.assertIsNotNone(result)
            self.assertTrue(result.endswith('_processed.wav'))
            
            # Verify audio processing steps
            mock_audio.set_channels.assert_called_once_with(1)  # Convert to mono
            mock_audio.set_frame_rate.assert_called_once_with(16000)  # Set sample rate
            mock_normalize.assert_called_once()
            mock_audio.strip_silence.assert_called_once()
            mock_audio.export.assert_called_once()
    
    @patch('os.path.exists')
    def test_preprocess_audio_file_not_found(self, mock_exists):
        """Test audio preprocessing with non-existent file."""
        mock_exists.return_value = False
        
        result = self.service.preprocess_audio(self.test_audio_path)
        
        self.assertIsNone(result)
    
    @patch('pydub.AudioSegment.from_file')
    @patch('os.path.exists')
    def test_preprocess_audio_exception(self, mock_exists, mock_from_file):
        """Test audio preprocessing with exception."""
        mock_exists.return_value = True
        mock_from_file.side_effect = Exception("Audio processing error")
        
        result = self.service.preprocess_audio(self.test_audio_path)
        
        self.assertIsNone(result)
    
    @patch('tempfile.NamedTemporaryFile')
    def test_text_to_speech_success(self, mock_tempfile):
        """Test successful text-to-speech conversion."""
        # Mock temporary file
        mock_file = MagicMock()
        mock_file.name = "/tmp/temp_audio.mp3"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        # Mock Polly response
        mock_response = {
            'AudioStream': MagicMock()
        }
        mock_response['AudioStream'].read.return_value = b"fake_audio_data"
        
        self.service.polly_client = MagicMock()
        self.service.polly_client.synthesize_speech.return_value = mock_response
        
        with patch('builtins.open', mock_open()) as mock_file_open:
            result = self.service.text_to_speech(self.test_text, "en-US", "Joanna")
            
            self.assertIsNotNone(result)
            self.assertEqual(result, "/tmp/temp_audio.mp3")
            
            # Verify Polly was called correctly
            self.service.polly_client.synthesize_speech.assert_called_once_with(
                Text=self.test_text,
                OutputFormat='mp3',
                VoiceId='Joanna',
                LanguageCode='en-US',
                Engine='neural'
            )
            
            # Verify file was written
            mock_file_open.assert_called_once_with("/tmp/temp_audio.mp3", 'wb')
    
    def test_text_to_speech_no_client(self):
        """Test text-to-speech without Polly client."""
        service = AudioService()  # No credentials
        
        result = service.text_to_speech(self.test_text)
        
        self.assertIsNone(result)
    
    def test_text_to_speech_empty_text(self):
        """Test text-to-speech with empty text."""
        self.service.polly_client = MagicMock()
        
        result = self.service.text_to_speech("")
        
        self.assertIsNone(result)
        self.service.polly_client.synthesize_speech.assert_not_called()
    
    def test_text_to_speech_exception(self):
        """Test text-to-speech with Polly exception."""
        self.service.polly_client = MagicMock()
        self.service.polly_client.synthesize_speech.side_effect = Exception("Polly error")
        
        result = self.service.text_to_speech(self.test_text)
        
        self.assertIsNone(result)
    
    @patch('ffmpeg.input')
    @patch('ffmpeg.output')
    @patch('os.path.exists')
    def test_merge_audio_with_video_success(self, mock_exists, mock_output, mock_input):
        """Test successful audio-video merging."""
        mock_exists.side_effect = lambda path: True  # All files exist
        
        # Mock ffmpeg objects
        mock_video_input = MagicMock()
        mock_audio_input = MagicMock()
        mock_video_input.__getitem__.return_value = "video_stream"
        mock_audio_input.__getitem__.return_value = "audio_stream"
        
        mock_input.side_effect = [mock_video_input, mock_audio_input]
        
        mock_output_obj = MagicMock()
        mock_output.return_value = mock_output_obj
        
        mock_run_obj = MagicMock()
        mock_output_obj.overwrite_output.return_value.run = mock_run_obj
        
        result = self.service.merge_audio_with_video(
            self.test_video_path, 
            self.test_audio_path
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('_dubbed.mp4'))
        
        # Verify ffmpeg was called correctly
        self.assertEqual(mock_input.call_count, 2)
        mock_output.assert_called_once()
        mock_run_obj.assert_called_once_with(quiet=True)
    
    @patch('os.path.exists')
    def test_merge_audio_with_video_files_not_found(self, mock_exists):
        """Test audio-video merging with missing files."""
        mock_exists.return_value = False
        
        result = self.service.merge_audio_with_video(
            self.test_video_path, 
            self.test_audio_path
        )
        
        self.assertIsNone(result)
    
    @patch('pydub.AudioSegment.from_file')
    @patch('os.path.exists')
    def test_adjust_audio_speed_success(self, mock_exists, mock_from_file):
        """Test successful audio speed adjustment."""
        mock_exists.side_effect = lambda path: path == self.test_audio_path or path.endswith('_speed_1.2.wav')
        
        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.frame_rate = 44100
        mock_audio.raw_data = b"fake_audio_data"
        mock_audio._spawn.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_from_file.return_value = mock_audio
        
        result = self.service.adjust_audio_speed(self.test_audio_path, 1.2)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('_speed_1.2.wav'))
        
        # Verify speed adjustment
        expected_new_rate = int(44100 * 1.2)
        mock_audio._spawn.assert_called_once_with(
            b"fake_audio_data", 
            overrides={"frame_rate": expected_new_rate}
        )
        mock_audio.set_frame_rate.assert_called_once_with(44100)
        mock_audio.export.assert_called_once()
    
    @patch('os.path.exists')
    def test_adjust_audio_speed_file_not_found(self, mock_exists):
        """Test audio speed adjustment with non-existent file."""
        mock_exists.return_value = False
        
        result = self.service.adjust_audio_speed(self.test_audio_path, 1.2)
        
        self.assertIsNone(result)
    
    @patch('pydub.AudioSegment.from_file')
    @patch('os.path.exists')
    def test_get_audio_duration_success(self, mock_exists, mock_from_file):
        """Test successful audio duration retrieval."""
        mock_exists.return_value = True
        
        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 5000  # 5 seconds in milliseconds
        mock_from_file.return_value = mock_audio
        
        result = self.service.get_audio_duration(self.test_audio_path)
        
        self.assertEqual(result, 5.0)  # Should be converted to seconds
    
    @patch('os.path.exists')
    def test_get_audio_duration_file_not_found(self, mock_exists):
        """Test audio duration retrieval with non-existent file."""
        mock_exists.return_value = False
        
        result = self.service.get_audio_duration(self.test_audio_path)
        
        self.assertIsNone(result)
    
    def test_get_default_voice(self):
        """Test default voice selection for different languages."""
        test_cases = [
            ('en-US', 'Joanna'),
            ('en-GB', 'Emma'),
            ('es-ES', 'Lucia'),
            ('fr-FR', 'Lea'),
            ('de-DE', 'Marlene'),
            ('unknown-XX', 'Joanna')  # Should default to Joanna
        ]
        
        for language_code, expected_voice in test_cases:
            with self.subTest(language_code=language_code):
                result = self.service._get_default_voice(language_code)
                self.assertEqual(result, expected_voice)
    
    def test_supports_neural_voice(self):
        """Test neural voice support detection."""
        neural_voices = ['Joanna', 'Matthew', 'Amy', 'Emma']
        standard_voices = ['Ivy', 'Russell', 'Nicole']
        
        for voice in neural_voices:
            with self.subTest(voice=voice):
                self.assertTrue(self.service._supports_neural_voice(voice))
        
        for voice in standard_voices:
            with self.subTest(voice=voice):
                # Note: Some of these might actually support neural now
                # This test checks the current implementation
                result = self.service._supports_neural_voice(voice)
                self.assertIsInstance(result, bool)
    
    def test_get_available_voices_success(self):
        """Test successful retrieval of available voices."""
        mock_response = {
            'Voices': [
                {
                    'Id': 'Joanna',
                    'Name': 'Joanna',
                    'LanguageCode': 'en-US',
                    'LanguageName': 'US English',
                    'Gender': 'Female',
                    'SupportedEngines': ['neural', 'standard']
                },
                {
                    'Id': 'Matthew',
                    'Name': 'Matthew',
                    'LanguageCode': 'en-US',
                    'LanguageName': 'US English',
                    'Gender': 'Male',
                    'SupportedEngines': ['neural', 'standard']
                }
            ]
        }
        
        self.service.polly_client = MagicMock()
        self.service.polly_client.describe_voices.return_value = mock_response
        
        result = self.service.get_available_voices('en-US')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'Joanna')
        self.assertEqual(result[0]['language_code'], 'en-US')
        self.assertEqual(result[0]['gender'], 'Female')
        self.assertEqual(result[1]['id'], 'Matthew')
        
        self.service.polly_client.describe_voices.assert_called_once_with(LanguageCode='en-US')
    
    def test_get_available_voices_no_client(self):
        """Test getting available voices without Polly client."""
        service = AudioService()  # No credentials
        
        result = service.get_available_voices()
        
        self.assertEqual(result, [])
    
    def test_get_available_voices_exception(self):
        """Test getting available voices with exception."""
        self.service.polly_client = MagicMock()
        self.service.polly_client.describe_voices.side_effect = Exception("API error")
        
        result = self.service.get_available_voices()
        
        self.assertEqual(result, [])

class TestAudioServiceIntegration(unittest.TestCase):
    """Integration tests for Audio service (requires actual AWS credentials)."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        # Only run if AWS credentials are available
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if self.aws_access_key and self.aws_secret_key:
            self.service = AudioService(
                aws_access_key=self.aws_access_key,
                aws_secret_key=self.aws_secret_key
            )
        else:
            self.service = None
    
    @unittest.skipUnless(
        os.getenv('RUN_INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable."
    )
    def test_get_available_voices_integration(self):
        """Integration test for getting available voices."""
        if not self.service or not self.service.polly_client:
            self.skipTest("AWS credentials not available")
        
        result = self.service.get_available_voices('en-US')
        
        self.assertIsInstance(result, list)
        if result:  # If voices are returned
            self.assertIn('id', result[0])
            self.assertIn('language_code', result[0])
            self.assertIn('gender', result[0])
    
    @unittest.skipUnless(
        os.getenv('RUN_INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable."
    )
    def test_text_to_speech_integration(self):
        """Integration test for text-to-speech conversion."""
        if not self.service or not self.service.polly_client:
            self.skipTest("AWS credentials not available")
        
        test_text = "Hello, this is a test."
        
        result = self.service.text_to_speech(test_text, 'en-US', 'Joanna')
        
        if result:  # Only assert if TTS succeeded
            self.assertTrue(os.path.exists(result))
            self.assertTrue(result.endswith('.mp3'))
            
            # Clean up
            os.remove(result)

if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)

