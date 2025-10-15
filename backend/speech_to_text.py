import asyncio
import logging
import tempfile
import os
from typing import AsyncGenerator
from config import Config
import whisper
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

logger = logging.getLogger(__name__)

class SpeechToText:
    def __init__(self):
        self.config = Config()
        self.stt_provider = self._detect_stt_provider()
        self.whisper_model = None
        
    def _detect_stt_provider(self):
        """Detect which STT provider to use based on available API keys"""
        if self.config.DEEPGRAM_API_KEY and not self.config.DEEPGRAM_API_KEY.startswith("your-"):
            return "deepgram"
        else:
            return "whisper_local"
    
    async def transcribe_audio_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> str:
        """Transcribe audio stream to text"""
        logger.info(f"Using STT provider: {self.stt_provider}")
        
        if self.stt_provider == "deepgram":
            return await self._transcribe_with_deepgram(audio_stream)
        else:
            return await self._transcribe_with_whisper(audio_stream)
    
    async def transcribe_audio_file(self, audio_file_path: str) -> str:
        """Transcribe audio file to text"""
        logger.info(f"Transcribing audio file with {self.stt_provider}")
        
        if self.stt_provider == "deepgram":
            return await self._transcribe_file_with_deepgram(audio_file_path)
        else:
            return await self._transcribe_file_with_whisper(audio_file_path)
    
    async def _transcribe_with_deepgram(self, audio_stream: AsyncGenerator[bytes, None]) -> str:
        """Transcribe using Deepgram streaming API"""
        try:
            
            deepgram = DeepgramClient(self.config.DEEPGRAM_API_KEY)
            
            # Collect audio data from stream
            audio_data = b""
            async for chunk in audio_stream:
                audio_data += chunk
            
            # Create file source
            payload: FileSource = {
                "buffer": audio_data,
            }
            
            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
                punctuate=True,
                diarize=True,  # Speaker identification
                language="en"
            )
            
            response = await deepgram.listen.prerecorded.v("1").transcribe_file(
                payload, options
            )
            
            # Extract transcript
            transcript = response.results.channels[0].alternatives[0].transcript
            logger.info(f"Deepgram transcript: {transcript}")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error with Deepgram transcription: {e}")
            # Fallback to Whisper
            return await self._transcribe_with_whisper(audio_stream)
    
    async def _transcribe_file_with_deepgram(self, audio_file_path: str) -> str:
        """Transcribe audio file using Deepgram"""
        try:
            
            deepgram = DeepgramClient(self.config.DEEPGRAM_API_KEY)
            
            with open(audio_file_path, "rb") as audio:
                buffer_data = audio.read()
            
            payload: FileSource = {
                "buffer": buffer_data,
            }
            
            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
                punctuate=True,
                diarize=True,
                language="en"
            )
            
            response = await asyncio.to_thread(
                lambda: deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
            )
            
            transcript = response.results.channels[0].alternatives[0].transcript
            logger.info(f"Deepgram transcript: {transcript}")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error with Deepgram file transcription: {e}")
            return await self._transcribe_file_with_whisper(audio_file_path)
    
    async def _transcribe_with_whisper(self, audio_stream: AsyncGenerator[bytes, None]) -> str:
        """Transcribe using local Whisper"""
        try:
            # Save audio stream to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Collect audio data from stream
                async for chunk in audio_stream:
                    temp_file.write(chunk)
                temp_file.flush()
                
                # Transcribe the file
                transcript = await self._transcribe_file_with_whisper(temp_path)
                
                # Clean up
                os.unlink(temp_path)
                
                return transcript
                
        except Exception as e:
            logger.error(f"Error with Whisper stream transcription: {e}")
            return ""
    
    async def _transcribe_file_with_whisper(self, audio_file_path: str) -> str:
        """Transcribe audio file using local Whisper"""
        try:
            
            # Load Whisper model (cached after first load)
            if self.whisper_model is None:
                logger.info(f"Loading Whisper model: {self.config.WHISPER_MODEL}")
                self.whisper_model = whisper.load_model(self.config.WHISPER_MODEL)
            
            # Transcribe
            result = self.whisper_model.transcribe(audio_file_path)
            transcript = result["text"].strip()
            
            logger.info(f"Whisper transcript: {transcript}")
            return transcript
            
        except Exception as e:
            logger.error(f"Error with Whisper transcription: {e}")
            return ""

