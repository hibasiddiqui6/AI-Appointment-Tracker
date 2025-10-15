import asyncio
import logging
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
    
    async def transcribe_audio_file(self, audio_file_path: str) -> str:
        """Transcribe audio file to text"""
        logger.info(f"Transcribing audio file with {self.stt_provider}")
        
        if self.stt_provider == "deepgram":
            return await self._transcribe_file_with_deepgram(audio_file_path)
        else:
            return await self._transcribe_file_with_whisper(audio_file_path)
    
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

