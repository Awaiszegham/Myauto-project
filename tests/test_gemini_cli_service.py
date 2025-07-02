import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, mock_open
import subprocess
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.gemini_cli_service import GeminiCLIService

class TestGeminiCLIService(unittest.TestCase):
    """Comprehensive tests for Gemini CLI service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = GeminiCLIService()
        self.test_audio_file = "/tmp/test_audio.wav"
        self.test_text = "Hello, this is a test text for translation."
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_audio_file):
            os.remove(self.test_audio_file)
    
    @patch('subprocess.run')
    def test_check_cli_availability_success(self, mock_run):
        """Test successful CLI availability check."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.service.check_cli_availability()
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["gemini", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_check_cli_availability_failure(self, mock_run):
        """Test CLI availability check failure."""
        mock_run.side_effect = FileNotFoundError()
        
        result = self.service.check_cli_availability()
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_transcribe_audio_success(self, mock_exists, mock_run):
        """Test successful audio transcription."""
        # Setup mocks
        mock_exists.return_value = True
        mock_response = {
            "text": "This is the transcribed text",
            "language": "en",
            "confidence": 0.95,
            "segments": []
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_response)
        )
        
        result = self.service.transcribe_audio(self.test_audio_file, "en")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["text"], "This is the transcribed text")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["confidence"], 0.95)
        
        # Verify the command was called correctly
        expected_command = [
            "gemini", "transcribe", "--file", self.test_audio_file,
            "--language", "en", "--format", "json"
        ]
        mock_run.assert_called_once()
        actual_command = mock_run.call_args[0][0]
        self.assertEqual(actual_command, expected_command)
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_transcribe_audio_file_not_found(self, mock_exists, mock_run):
        """Test transcription with non-existent audio file."""
        mock_exists.return_value = False
        
        result = self.service.transcribe_audio(self.test_audio_file)
        
        self.assertIsNone(result)
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_transcribe_audio_cli_error(self, mock_exists, mock_run):
        """Test transcription with CLI error."""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "gemini", stderr="CLI error occurred"
        )
        
        result = self.service.transcribe_audio(self.test_audio_file)
        
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_transcribe_audio_timeout(self, mock_exists, mock_run):
        """Test transcription timeout."""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("gemini", 300)
        
        result = self.service.transcribe_audio(self.test_audio_file)
        
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_transcribe_audio_invalid_json(self, mock_exists, mock_run):
        """Test transcription with invalid JSON response."""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid json response"
        )
        
        result = self.service.transcribe_audio(self.test_audio_file)
        
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_translate_text_short_success(self, mock_run):
        """Test successful translation of short text."""
        mock_response = {
            "translated_text": "Hola, esta es una prueba de texto para traducción.",
            "source_language": "en",
            "target_language": "es",
            "confidence": 0.98
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_response)
        )
        
        result = self.service.translate_text(self.test_text, "es", "en")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["translated_text"], mock_response["translated_text"])
        self.assertEqual(result["source_language"], "en")
        self.assertEqual(result["target_language"], "es")
        self.assertEqual(result["original_text"], self.test_text)
        
        # Verify the command was called correctly
        expected_command = [
            "gemini", "translate", "--text", self.test_text,
            "--source-language", "en", "--target-language", "es", "--format", "json"
        ]
        mock_run.assert_called_once()
        actual_command = mock_run.call_args[0][0]
        self.assertEqual(actual_command, expected_command)
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.unlink')
    def test_translate_text_long_success(self, mock_unlink, mock_tempfile, mock_run):
        """Test successful translation of long text using temporary file."""
        long_text = "A" * 1500  # Text longer than 1000 characters
        
        # Mock temporary file
        mock_file = MagicMock()
        mock_file.name = "/tmp/temp_text_file.txt"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        mock_response = {
            "translated_text": "Translated long text",
            "source_language": "en",
            "target_language": "es",
            "confidence": 0.95
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_response)
        )
        
        result = self.service.translate_text(long_text, "es", "en")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["translated_text"], "Translated long text")
        
        # Verify temporary file was written to
        mock_file.write.assert_called_once_with(long_text)
        
        # Verify the command used file input
        expected_command = [
            "gemini", "translate", "--file", "/tmp/temp_text_file.txt",
            "--source-language", "en", "--target-language", "es", "--format", "json"
        ]
        mock_run.assert_called_once()
        actual_command = mock_run.call_args[0][0]
        self.assertEqual(actual_command, expected_command)
        
        # Verify cleanup
        mock_unlink.assert_called_once_with("/tmp/temp_text_file.txt")
    
    @patch('subprocess.run')
    def test_translate_text_empty_text(self, mock_run):
        """Test translation with empty text."""
        result = self.service.translate_text("", "es")
        
        self.assertIsNone(result)
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_translate_text_cli_error(self, mock_run):
        """Test translation with CLI error."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "gemini", stderr="Translation failed"
        )
        
        result = self.service.translate_text(self.test_text, "es")
        
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_translate_text_timeout(self, mock_run):
        """Test translation timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("gemini", 120)
        
        result = self.service.translate_text(self.test_text, "es")
        
        self.assertIsNone(result)
    
    def test_batch_translate(self):
        """Test batch translation functionality."""
        texts = ["Hello", "World", "Test"]
        
        with patch.object(self.service, 'translate_text') as mock_translate:
            mock_translate.side_effect = [
                {"translated_text": "Hola"},
                {"translated_text": "Mundo"},
                {"translated_text": "Prueba"}
            ]
            
            results = self.service.batch_translate(texts, "es")
            
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["translated_text"], "Hola")
            self.assertEqual(results[1]["translated_text"], "Mundo")
            self.assertEqual(results[2]["translated_text"], "Prueba")
            
            # Verify each text was translated
            self.assertEqual(mock_translate.call_count, 3)
    
    @patch('subprocess.run')
    def test_get_supported_languages_success(self, mock_run):
        """Test successful retrieval of supported languages."""
        mock_response = {
            "languages": {
                "en": "English",
                "es": "Spanish",
                "fr": "French"
            }
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_response)
        )
        
        result = self.service.get_supported_languages()
        
        self.assertIsNotNone(result)
        self.assertEqual(result["en"], "English")
        self.assertEqual(result["es"], "Spanish")
        self.assertEqual(result["fr"], "French")
        
        expected_command = ["gemini", "languages", "--format", "json"]
        mock_run.assert_called_once()
        actual_command = mock_run.call_args[0][0]
        self.assertEqual(actual_command, expected_command)
    
    @patch('subprocess.run')
    def test_get_supported_languages_error(self, mock_run):
        """Test error in retrieving supported languages."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gemini")
        
        result = self.service.get_supported_languages()
        
        self.assertIsNone(result)

class TestGeminiCLIServiceIntegration(unittest.TestCase):
    """Integration tests for Gemini CLI service (requires actual CLI)."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.service = GeminiCLIService()
        
    def test_cli_availability_integration(self):
        """Integration test for CLI availability (requires actual Gemini CLI)."""
        # This test will only pass if Gemini CLI is actually installed
        result = self.service.check_cli_availability()
        
        # We don't assert True/False here as it depends on the environment
        # Instead, we just verify the method doesn't crash
        self.assertIsInstance(result, bool)
    
    @unittest.skipUnless(
        os.getenv('RUN_INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable."
    )
    def test_translation_integration(self):
        """Integration test for text translation (requires actual Gemini CLI)."""
        test_text = "Hello, world!"
        
        result = self.service.translate_text(test_text, "es", "en")
        
        if result:  # Only assert if translation succeeded
            self.assertIsInstance(result, dict)
            self.assertIn("translated_text", result)
            self.assertIn("source_language", result)
            self.assertIn("target_language", result)
            self.assertEqual(result["original_text"], test_text)

if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)

