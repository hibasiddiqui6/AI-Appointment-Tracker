import asyncio
import logging
import time
import tempfile, wave, os, io
import numpy as np
from livekit import rtc, api
from config import Config
from models import AppointmentData
from data_extractor import DataExtractor
from speech_to_text import SpeechToText
from webhook_sender import WebhookSender
from token_utils import build_livekit_token

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CallListener:
    def __init__(self):
        self.config = Config()
        self.data_extractor = DataExtractor()
        self.webhook_sender = WebhookSender()
        self.speech_to_text = SpeechToText()
        self.transcript = ""
        self.call_start_time = None
        self.appointment_data = AppointmentData()
        self.audio_buffer = []
        # Reference to rtc.Room when running via run_rtc_listener
        self.room = None
        
        # Speech detection parameters (tuned)
        self.silence_threshold = 3.0  # seconds of silence before processing
        self.min_speech_threshold = 0.01  # minimum audio level to consider as speech
        self.last_processed_time = 0
        self.processed_once = False  # avoid double-processing on disconnect
        self.webhook_sent = False

        self.end_phrases = [
            "bye", "goodbye", "see you", "talk to you later", "thanks, bye",
            "have a nice day", "thank you bye", "that will be all"
        ]
    
    def reset_state(self):
        """Reset listener state for a brand-new participant/call.
        This avoids carrying transcript and timers between calls.
        """
        logger.info("Resetting call state for new participant")
        self.transcript = ""
        self.call_start_time = None
        self.appointment_data = AppointmentData()
        self.audio_buffer = []
        self.last_processed_time = 0
        self.processed_once = False
        
    async def on_participant_connected(self, participant: rtc.RemoteParticipant):
        """Called when a participant joins the room"""
        logger.info(f"Participant {participant.identity} connected")
        # New participant implies a new call session; clear prior state
        self.reset_state()
        
    async def on_participant_disconnected(self, participant: rtc.RemoteParticipant):
        """Called when a participant leaves the room"""
        logger.info(f"Participant {participant.identity} disconnected")
        # Reset immediately so any reconnection starts clean
        self.reset_state()
        
    async def on_track_subscribed(self, track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        """Called when a track is subscribed"""
        logger.info(f"Track {track.kind} subscribed from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            # Start processing audio for transcription
            await self.process_audio_track(track)
            
    async def process_audio_track(self, track: rtc.AudioTrack):
        """Process audio track using simple RMS-based VAD (no sleep timer)"""
        logger.info("Starting audio processing (RMS VAD)")
        
        # Local VAD state
        is_speaking = False
        last_activity_time = None
        finalized = False
        
        try:
            stream = rtc.AudioStream(track)
            async for audio_event in stream:
                if finalized:
                    break
                frame = getattr(audio_event, "frame", audio_event)

                audio_level = self.calculate_audio_level(frame)
                
                # Get raw bytes
                raw_bytes = None
                try:
                    if hasattr(frame, "data"):
                        data_obj = frame.data
                        if isinstance(data_obj, (bytes, bytearray)):
                            raw_bytes = bytes(data_obj)
                        elif isinstance(data_obj, memoryview):
                            raw_bytes = data_obj.tobytes()
                        else:
                            raw_bytes = bytes(data_obj)
                    elif hasattr(frame, "to_wav_bytes"):
                        wav_bytes = frame.to_wav_bytes()
                        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                            raw_bytes = wf.readframes(wf.getnframes())
                except Exception as e:
                    logger.warning(f"Audio frame extract failed: {e}")
                    raw_bytes = None
                
                now = time.time()
                
                # VAD transitions
                if audio_level > self.min_speech_threshold and not is_speaking:
                    # Speech start
                    logger.info(f"Speech start (level={audio_level:.3f})")
                    is_speaking = True
                    self.audio_buffer = []
                    last_activity_time = now
                    # ensure call start captured when user first speaks
                    if self.call_start_time is None:
                        self.call_start_time = now
                elif audio_level > self.min_speech_threshold and is_speaking:
                    # Speech continues
                    last_activity_time = now
                elif audio_level <= self.min_speech_threshold and is_speaking:
                    # Possible speech end if silence exceeds threshold
                    if last_activity_time and (now - last_activity_time) > self.silence_threshold:
                        logger.info(f"Speech end after {now - last_activity_time:.2f}s silence; processing")
                        await self.process_audio_buffer()
                        # set call duration at first finalization as well
                        if self.call_start_time:
                            duration_seconds = now - self.call_start_time
                            self.appointment_data.call_duration = self.format_duration(duration_seconds)
                        # Notify UI that call should end
                        await self.notify_ui_call_finished()
                        self.processed_once = True
                        is_speaking = False
                        self.last_processed_time = now
                        finalized = True
                        break
                
                # Buffer audio only when speaking
                if is_speaking and raw_bytes:
                    self.audio_buffer.append(raw_bytes)
        except Exception as e:
            logger.error(f"VAD loop error: {e}")

    def calculate_audio_level(self, audio_frame) -> float:
        """Compute simple RMS level from an audio frame."""
        try:
            data = None
            if hasattr(audio_frame, 'data'):
                d = audio_frame.data
                if isinstance(d, memoryview):
                    data = np.frombuffer(d.tobytes(), dtype=np.int16)
                elif isinstance(d, (bytes, bytearray)):
                    data = np.frombuffer(d, dtype=np.int16)
                else:
                    data = np.frombuffer(bytes(d), dtype=np.int16)
            elif hasattr(audio_frame, 'to_wav_bytes'):
                wav_b = audio_frame.to_wav_bytes()
                with wave.open(io.BytesIO(wav_b), 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    data = np.frombuffer(frames, dtype=np.int16)
            if data is None or data.size == 0:
                return 0.0
            rms = np.sqrt(np.mean(data.astype(np.float32) ** 2))
            return float(rms / 32768.0)
        except Exception:
            return 0.0
    
    def format_duration(self, duration_seconds: float) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS format."""
        if duration_seconds < 60:
            return f"{int(duration_seconds)}s"
        
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        
        if minutes < 60:
            return f"{minutes}:{seconds:02d}"
        else:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        
    async def process_audio_buffer(self):
        """Process buffered audio data for transcription"""
        if not self.audio_buffer:
            logger.warning("No audio data to process")
            return
            
        logger.info(f"Processing {len(self.audio_buffer)} audio chunks")
        try:
            # Write buffered PCM to a temporary WAV (48kHz mono s16le) then transcribe
            pcm_bytes = b"".join(self.audio_buffer)
            self.audio_buffer = []

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            try:
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(48000)
                    wf.writeframes(pcm_bytes)

                part = await self.speech_to_text.transcribe_audio_file(wav_path)
                if part:
                    if self.transcript:
                        self.transcript += " " + part
                    else:
                        self.transcript = part
            finally:
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass
            
            self.last_processed_time = time.time()
            logger.info(f"Transcript received (length={len(self.transcript)}): {self.transcript}")
            
            # Set call duration first
            if self.call_start_time and not self.appointment_data.call_duration:
                duration_seconds = time.time() - self.call_start_time
                formatted_duration = self.format_duration(duration_seconds)
                self.appointment_data.call_duration = formatted_duration
                logger.info(f"Call duration set: {self.appointment_data.call_duration}")
            
            # Extract appointment data from transcript
            await self.extract_appointment_data()
            
            # Send to webhook immediately after processing
            await self.send_to_webhook()
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
        
    async def extract_appointment_data(self):
        """Extract appointment data from transcript using AI"""
        logger.info("Extracting appointment data from transcript")
        
        try:
            # Early end-of-call phrase check
            lower = (self.transcript or "").lower()
            if any(p in lower for p in self.end_phrases):
                self.processed_once = True
                logger.info("End phrase detected; marking call as finalized")
            
            extracted_data = await self.data_extractor.extract_from_transcript(self.transcript)

            # Merge extracted fields into our existing appointment_data
            # without overwriting already set values like call_duration.
            if extracted_data:
                if getattr(extracted_data, "name", None):
                    self.appointment_data.name = extracted_data.name
                if getattr(extracted_data, "email", None):
                    self.appointment_data.email = extracted_data.email
                if getattr(extracted_data, "phone", None):
                    self.appointment_data.phone = extracted_data.phone
                if getattr(extracted_data, "appointment_date", None):
                    self.appointment_data.appointment_date = extracted_data.appointment_date
                if getattr(extracted_data, "appointment_time", None):
                    self.appointment_data.appointment_time = extracted_data.appointment_time
                if getattr(extracted_data, "appointment_reason", None):
                    self.appointment_data.appointment_reason = extracted_data.appointment_reason

            logger.info(f"Extracted data merged: {self.appointment_data.to_json()}")
            
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
            
    async def send_to_webhook(self):
        """Send appointment data to n8n webhook"""
        try:
            if self.webhook_sent:
                return
            logger.info("Sending data to webhook...")
            # Ensure transcript and duration are up-to-date before sending
            if self.transcript:
                self.appointment_data.transcript = self.transcript
            # Do not overwrite duration if it was already finalized
            if self.call_start_time and not self.appointment_data.call_duration:
                duration_seconds = time.time() - self.call_start_time
                self.appointment_data.call_duration = self.format_duration(duration_seconds)
            success = await self.webhook_sender.send_appointment_data(self.appointment_data)
            if success:
                logger.info("✅ Data sent to webhook successfully")
                self.webhook_sent = True
            else:
                logger.error("❌ Failed to send data to webhook")
        except Exception as e:
            logger.error(f"Error sending to webhook: {e}")
            
    async def on_room_disconnected(self):
        """Called when the room is disconnected"""
        logger.info("Room disconnected - processing final data")
        
        # If we haven't processed yet (no long silence), process remaining buffer once
        if not self.processed_once and self.audio_buffer:
            logger.info("Disconnect-triggered finalization; processing remaining buffer")
            await self.process_audio_buffer()
            self.processed_once = True
        
        # Calculate call duration
        if self.call_start_time:
            duration_seconds = time.time() - self.call_start_time
            self.appointment_data.call_duration = self.format_duration(duration_seconds)
            logger.info(f"Call duration: {self.appointment_data.call_duration}")
            
        # Send data to webhook
        await self.send_to_webhook()
        
        # Prepare for a new session if the room reconnects later
        self.reset_state()

    async def notify_ui_call_finished(self):
        """Send a small data message so the UI auto-leaves."""
        try:
            if getattr(self, "room", None) and getattr(self.room, "local_participant", None):
                message = b"END_CALL"
                try:
                    # default is reliable; no enum needed
                    await self.room.local_participant.publish_data(message, topic="control")
                except TypeError:
                    # older SDKs without topic kwarg
                    await self.room.local_participant.publish_data(message)
                logger.info("Sent END_CALL signal to UI")
        except Exception as e:
            logger.warning(f"Failed to send END_CALL signal: {e}")
            
# --- Direct RTC listener (joins a room with JWT) ---
async def run_rtc_listener(room_name: str = "demo", identity: str = "listener-agent"):
    """Join a LiveKit room directly using rtc.Room and listen for audio tracks.
    This is suitable for running inside our combined runner instead of the agents worker.
    """
    logger.info("Starting LiveKit RTC listener")
    cfg = Config()

    if not (cfg.LIVEKIT_URL and cfg.LIVEKIT_API_KEY and cfg.LIVEKIT_API_SECRET):
        logger.error("LiveKit configuration missing. Check LIVEKIT_URL/API_KEY/API_SECRET")
        return

    # Create room and listener instance
    room = rtc.Room()
    listener = CallListener()
    listener.room = room

    # Set call start time at connection; will be overwritten on first speech
    listener.call_start_time = time.time()

    # Wire events to our listener callbacks (wrap async handlers)
    room.on("participant_connected", lambda p: asyncio.create_task(listener.on_participant_connected(p)))
    room.on("participant_disconnected", lambda p: asyncio.create_task(listener.on_participant_disconnected(p)))
    room.on(
        "track_subscribed",
        lambda track, pub, p: asyncio.create_task(listener.on_track_subscribed(track, pub, p)),
    )
    room.on("disconnected", lambda: asyncio.create_task(listener.on_room_disconnected()))

    # Build JWT token for the listener to join and subscribe only (shared helper)
    token, _ = build_livekit_token(
        room_name=room_name,
        identity=identity,
        name="RTC Listener",
        can_publish=False,
        can_subscribe=True,
        can_publish_data=True,
        ttl_hours=24,
    )

    logger.info(f"Connecting RTC listener to room '{room_name}'")
    await room.connect(cfg.LIVEKIT_URL, token)
    logger.info("RTC listener connected")

    # Keep alive
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        await room.disconnect()
