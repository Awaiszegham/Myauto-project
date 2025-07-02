import os
import boto3
import logging
import tempfile
from pydub import AudioSegment
from pydub.effects import normalize
from typing import Optional, Dict, Any, List
import ffmpeg

logger = logging.getLogger(__name__)

class AudioService:
    """Service for audio processing, text-to-speech, and audio manipulation."""
    
    def __init__(self, aws_access_key: str = None, aws_secret_key: str = None, aws_region: str = 'us-east-1'):
        self.aws_access_key = aws_access_key or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = aws_region
        
        # Initialize AWS Polly client
        if self.aws_access_key and self.aws_secret_key:
            self.polly_client = boto3.client(
                'polly',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
        else:
            self.polly_client = None
            logger.warning("AWS credentials not provided, TTS functionality will be limited")
    
    def extract_audio_from_video(self, video_path: str, output_path: str = None) -> Optional[str]:
        """
        Extract audio from video file using ffmpeg.
        
        Args:
            video_path: Path to the video file
            output_path: Path for the output audio file (optional)
            
        Returns:
            Path to the extracted audio file or None if failed
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None
            
            if not output_path:
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(os.path.dirname(video_path), f"{video_name}_audio.wav")
            
            # Use ffmpeg to extract audio
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            
            if os.path.exists(output_path):
                logger.info(f"Audio extracted successfully: {output_path}")
                return output_path
            else:
                logger.error("Audio extraction failed")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return None
    
    def preprocess_audio(self, audio_path: str, output_path: str = None) -> Optional[str]:
        """
        Preprocess audio for better transcription quality.
        
        Args:
            audio_path: Path to the input audio file
            output_path: Path for the processed audio file (optional)
            
        Returns:
            Path to the processed audio file or None if failed
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            if not output_path:
                audio_name = os.path.splitext(os.path.basename(audio_path))[0]
                output_path = os.path.join(os.path.dirname(audio_path), f"{audio_name}_processed.wav")
            
            # Load audio with pydub
            audio = AudioSegment.from_file(audio_path)
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Set sample rate to 16kHz (good for speech recognition)
            audio = audio.set_frame_rate(16000)
            
            # Normalize audio levels
            audio = normalize(audio)
            
            # Remove silence from beginning and end
            audio = audio.strip_silence(silence_len=1000, silence_thresh=-40)
            
            # Export processed audio
            audio.export(output_path, format="wav")
            
            logger.info(f"Audio preprocessed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error preprocessing audio: {e}")
            return None
    
    def text_to_speech(self, text: str, language_code: str = 'en-US', 
                      voice_id: str = None, output_path: str = None) -> Optional[str]:
        """
        Convert text to speech using AWS Polly.
        
        Args:
            text: Text to convert to speech
            language_code: Language code (e.g., 'en-US', 'es-ES')
            voice_id: Specific voice ID (optional)
            output_path: Path for the output audio file (optional)
            
        Returns:
            Path to the generated audio file or None if failed
        """
        try:
            if not self.polly_client:
                logger.error("AWS Polly client not initialized")
                return None
            
            if not text.strip():
                logger.error("Empty text provided for TTS")
                return None
            
            # Get appropriate voice if not specified
            if not voice_id:
                voice_id = self._get_default_voice(language_code)
            
            if not output_path:
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    output_path = temp_file.name
            
            logger.info(f"Generating speech for text length: {len(text)} characters")
            
            # Generate speech
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=voice_id,
                LanguageCode=language_code,
                Engine='neural' if self._supports_neural_voice(voice_id) else 'standard'
            )
            
            # Save audio data to file
            with open(output_path, 'wb') as file:
                file.write(response['AudioStream'].read())
            
            logger.info(f"Speech generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return None
    
    def merge_audio_with_video(self, video_path: str, audio_path: str, output_path: str = None) -> Optional[str]:
        """
        Merge dubbed audio with original video.
        
        Args:
            video_path: Path to the original video file
            audio_path: Path to the dubbed audio file
            output_path: Path for the output video file (optional)
            
        Returns:
            Path to the merged video file or None if failed
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None
            
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            if not output_path:
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(os.path.dirname(video_path), f"{video_name}_dubbed.mp4")
            
            # Use ffmpeg to merge video and audio
            video_input = ffmpeg.input(video_path)
            audio_input = ffmpeg.input(audio_path)
            
            (
                ffmpeg
                .output(video_input['v'], audio_input['a'], output_path, vcodec='copy', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            if os.path.exists(output_path):
                logger.info(f"Video and audio merged successfully: {output_path}")
                return output_path
            else:
                logger.error("Video merging failed")
                return None
                
        except Exception as e:
            logger.error(f"Error merging video and audio: {e}")
            return None
    
    def adjust_audio_speed(self, audio_path: str, speed_factor: float, output_path: str = None) -> Optional[str]:
        """
        Adjust audio playback speed to match video duration.
        
        Args:
            audio_path: Path to the input audio file
            speed_factor: Speed adjustment factor (1.0 = normal, 1.2 = 20% faster)
            output_path: Path for the output audio file (optional)
            
        Returns:
            Path to the speed-adjusted audio file or None if failed
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            if not output_path:
                audio_name = os.path.splitext(os.path.basename(audio_path))[0]
                output_path = os.path.join(os.path.dirname(audio_path), f"{audio_name}_speed_{speed_factor}.wav")
            
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Adjust speed by changing frame rate
            new_sample_rate = int(audio.frame_rate * speed_factor)
            adjusted_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
            adjusted_audio = adjusted_audio.set_frame_rate(audio.frame_rate)
            
            # Export adjusted audio
            adjusted_audio.export(output_path, format="wav")
            
            logger.info(f"Audio speed adjusted successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adjusting audio speed: {e}")
            return None
    
    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """
        Get audio duration in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds or None if failed
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0  # Convert milliseconds to seconds
            
            return duration
            
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return None
    
    def _get_default_voice(self, language_code: str) -> str:
        """Get default voice for a language code."""
        voice_mapping = {
            'en-US': 'Joanna',
            'en-GB': 'Emma',
            'es-ES': 'Lucia',
            'es-MX': 'Mia',
            'fr-FR': 'Lea',
            'de-DE': 'Marlene',
            'it-IT': 'Bianca',
            'pt-BR': 'Camila',
            'ja-JP': 'Mizuki',
            'ko-KR': 'Seoyeon',
            'zh-CN': 'Zhiyu',
            'hi-IN': 'Aditi',
            'ar-AE': 'Zeina',
            'ru-RU': 'Tatyana'
        }
        return voice_mapping.get(language_code, 'Joanna')
    
    def _supports_neural_voice(self, voice_id: str) -> bool:
        """Check if voice supports neural engine."""
        neural_voices = [
            'Joanna', 'Matthew', 'Amy', 'Emma', 'Brian', 'Olivia',
            'Aria', 'Ayanda', 'Ivy', 'Kendra', 'Kimberly', 'Salli',
            'Joey', 'Justin', 'Kevin', 'Ruth'
        ]
        return voice_id in neural_voices
    
    def get_available_voices(self, language_code: str = None) -> List[Dict[str, Any]]:
        """
        Get list of available voices from AWS Polly.
        
        Args:
            language_code: Filter by language code (optional)
            
        Returns:
            List of voice information dictionaries
        """
        try:
            if not self.polly_client:
                return []
            
            response = self.polly_client.describe_voices(LanguageCode=language_code)
            voices = response.get('Voices', [])
            
            return [
                {
                    'id': voice['Id'],
                    'name': voice['Name'],
                    'language_code': voice['LanguageCode'],
                    'language_name': voice['LanguageName'],
                    'gender': voice['Gender'],
                    'engine': voice.get('SupportedEngines', ['standard'])
                }
                for voice in voices
            ]
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return []

