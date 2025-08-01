import subprocess
import json
import os
import tempfile
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class GeminiCLIService:
    """Service for interacting with Google Gemini CLI for transcription and translation."""
    
    def __init__(self):
        self.cli_command = "gemini"  # Assuming gemini CLI is in PATH
    
    def check_cli_availability(self) -> dict:
        """Check if Gemini CLI is available and properly configured."""
        try:
            # First try to check if command exists
            result = subprocess.run(
                [self.cli_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            
            if result.returncode == 0:
                return {
                    "available": True, 
                    "version": result.stdout.strip(),
                    "status": "ready"
                }
            else:
                # Try alternative commands
                for cmd in ["--help", "help", "languages"]:
                    try:
                        result = subprocess.run(
                            [self.cli_command, cmd],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            check=False
                        )
                        if result.returncode == 0:
                            return {
                                "available": True,
                                "output": result.stdout.strip(),
                                "status": "available"
                            }
                    except:
                        continue
                
                return {
                    "available": False,
                    "error": result.stderr.strip() or "Command failed",
                    "stdout": result.stdout.strip(),
                    "returncode": result.returncode
                }
                
        except FileNotFoundError:
            return {
                "available": False, 
                "error": f"Command '{self.cli_command}' not found. Please install Gemini CLI.",
                "suggestion": "Install via: pip install google-generativeai"
            }
        except subprocess.TimeoutExpired:
            return {"available": False, "error": "Command timed out."}
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def transcribe_audio(self, audio_file_path: str, language: str = "auto") -> Optional[Dict[str, Any]]:
        """
        Transcribe audio file using Gemini CLI.
        
        Args:
            audio_file_path: Path to the audio file
            language: Source language code (default: auto-detect)
            
        Returns:
            Dictionary containing transcription results or None if failed
        """
        try:
            if not os.path.exists(audio_file_path):
                logger.error(f"Audio file not found: {audio_file_path}")
                return None
            
            # Check CLI availability first
            cli_status = self.check_cli_availability()
            if not cli_status.get("available", False):
                logger.error(f"Gemini CLI not available: {cli_status.get('error', 'Unknown error')}")
                return self.get_fallback_transcription(audio_file_path, language)
            
            # Construct the Gemini CLI command for transcription
            command = [
                self.cli_command,
                "transcribe",
                "--file", audio_file_path,
                "--language", language,
                "--format", "json"
            ]
            
            logger.info(f"Executing transcription command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                check=True
            )
            
            # Parse the JSON output
            transcription_data = json.loads(result.stdout)
            logger.info("Transcription completed successfully")
            
            return {
                "text": transcription_data.get("text", ""),
                "language": transcription_data.get("language", language),
                "confidence": transcription_data.get("confidence", 0.0),
                "segments": transcription_data.get("segments", [])
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Gemini CLI transcription failed: {e.stderr}")
            return self.get_fallback_transcription(audio_file_path, language)
        except subprocess.TimeoutExpired:
            logger.error("Transcription timeout expired")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse transcription output: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            return None
    
    def translate_text(self, text: str, target_language: str, source_language: str = "auto") -> Optional[Dict[str, Any]]:
        """
        Translate text using Gemini CLI.
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (default: auto-detect)
            
        Returns:
            Dictionary containing translation results or None if failed
        """
        try:
            if not text.strip():
                logger.error("Empty text provided for translation")
                return None
            
            # Check CLI availability first
            cli_status = self.check_cli_availability()
            if not cli_status.get("available", False):
                logger.error(f"Gemini CLI not available: {cli_status.get('error', 'Unknown error')}")
                return self.get_fallback_translation(text, target_language)
            
            # For longer texts, use a temporary file
            if len(text) > 1000:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    temp_file.write(text)
                    temp_file_path = temp_file.name
                
                try:
                    command = [
                        self.cli_command,
                        "translate",
                        "--file", temp_file_path,
                        "--source-language", source_language,
                        "--target-language", target_language,
                        "--format", "json"
                    ]
                    
                    logger.info(f"Executing translation command with file: {' '.join(command)}")
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=120,  # 2 minutes timeout
                        check=True
                    )
                    
                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)
            else:
                # For shorter texts, pass directly as argument
                command = [
                    self.cli_command,
                    "translate",
                    "--text", text,
                    "--source-language", source_language,
                    "--target-language", target_language,
                    "--format", "json"
                ]
                
                logger.info(f"Executing translation command: {' '.join(command)}")
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minutes timeout
                    check=True
                )
            
            # Parse the JSON output
            translation_data = json.loads(result.stdout)
            logger.info("Translation completed successfully")
            
            return {
                "translated_text": translation_data.get("translated_text", ""),
                "source_language": translation_data.get("source_language", source_language),
                "target_language": translation_data.get("target_language", target_language),
                "confidence": translation_data.get("confidence", 0.0),
                "original_text": text
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Gemini CLI translation failed: {e.stderr}")
            return self.get_fallback_translation(text, target_language)
        except subprocess.TimeoutExpired:
            logger.error("Translation timeout expired")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse translation output: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during translation: {e}")
            return None
    
    def get_fallback_transcription(self, audio_file_path: str, language: str) -> Optional[Dict[str, Any]]:
        """Fallback transcription method when CLI is unavailable."""
        try:
            logger.warning("Using fallback transcription method")
            
            return {
                "text": f"[FALLBACK] Audio transcription unavailable",
                "language": language,
                "confidence": 0.0,
                "segments": [],
                "method": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Fallback transcription failed: {e}")
            return None
    
    def get_fallback_translation(self, text: str, target_language: str) -> Optional[Dict[str, Any]]:
        """Fallback translation method when CLI is unavailable."""
        try:
            logger.warning("Using fallback translation method")
            
            return {
                "translated_text": f"[FALLBACK] {text}",
                "source_language": "auto",
                "target_language": target_language,
                "confidence": 0.5,
                "original_text": text,
                "method": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Fallback translation failed: {e}")
            return None
    
    def batch_translate(self, texts: list, target_language: str, source_language: str = "auto") -> list:
        """
        Translate multiple texts in batch.
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code
            
        Returns:
            List of translation results
        """
        results = []
        for text in texts:
            result = self.translate_text(text, target_language, source_language)
            results.append(result)
        return results
    
    def get_supported_languages(self) -> Optional[Dict[str, str]]:
        """
        Get list of supported languages from Gemini CLI.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        try:
            command = [self.cli_command, "languages", "--format", "json"]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            languages_data = json.loads(result.stdout)
            return languages_data.get("languages", {})
            
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return None
