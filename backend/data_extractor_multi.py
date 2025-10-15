import re
import logging
from models import AppointmentData
from config import Config
import google.generativeai as genai

logger = logging.getLogger(__name__)

class DataExtractor:
    def __init__(self):
        self.config = Config()
        self.ai_provider = self._detect_ai_provider()
        
    def _detect_ai_provider(self):
        """Detect which AI provider to use based on available API keys"""
        if self.config.GEMINI_API_KEY and not self.config.GEMINI_API_KEY.startswith("your-"):
            return "gemini"
        else:
            return "regex_only"
    
    async def extract_from_transcript(self, transcript: str) -> AppointmentData:
        """Extract appointment data from transcript using available AI provider"""
        logger.info(f"Using AI provider: {self.ai_provider}")
        
        if self.ai_provider == "gemini":
            return await self._extract_with_gemini(transcript)
        else:
            logger.info("No AI provider available - using regex extraction only")
            return self._extract_with_regex(transcript)
    
    async def _extract_with_gemini(self, transcript: str) -> AppointmentData:
        """Extract using Google Gemini with graceful model fallback"""
        try:
            genai.configure(api_key=self.config.GEMINI_API_KEY)

            # Allow override via env var GEMINI_MODEL; else try common models then fallback to first supporting generateContent
            preferred_models = []
            if getattr(self.config, "GEMINI_MODEL", None):
                preferred_models.append(self.config.GEMINI_MODEL)
            preferred_models += [
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro",
            ]

            model = None
            last_err = None
            prompt = f"""Extract appointment information from this call transcript.

                Extract the following information if mentioned:
                - Name (person's full name)
                - Email address
                - Phone number
                - Appointment date and time
                - Reason for appointment

                Return the data in this exact format:
                Name: [extracted name or null]
                Email: [extracted email or null]
                Phone: [extracted phone or null]
                Date: [extracted date or null]
                Time: [extracted time or null]
                Reason: [extracted reason or null]

                Transcript:
                {transcript}"""

            # Try preferred models first
            for name in preferred_models:
                try:
                    model = genai.GenerativeModel(name)
                    response = model.generate_content(prompt)
                    content = getattr(response, "text", "") or ""
                    logger.info(f"Gemini response (model={name}): {content}")
                    appointment_data = self._extract_with_regex(transcript)
                    appointment_data = self._parse_ai_response(content, appointment_data)
                    return appointment_data
                except Exception as e:
                    last_err = e
                    logger.debug(f"Gemini model '{name}' failed: {e}")
                    continue

            # Fallback: pick any model that supports generateContent
            try:
                models = genai.list_models()
                for m in models:
                    caps = getattr(m, "supported_generation_methods", []) or []
                    if "generateContent" in caps:
                        try:
                            model = genai.GenerativeModel(m.name)
                            response = model.generate_content(prompt)
                            content = getattr(response, "text", "") or ""
                            logger.info(f"Gemini response (model={m.name}): {content}")
                            appointment_data = self._extract_with_regex(transcript)
                            appointment_data = self._parse_ai_response(content, appointment_data)
                            return appointment_data
                        except Exception as e:
                            last_err = e
                            continue
            except Exception as e:
                last_err = e

            # If all models failed, fall back to regex
            if last_err:
                logger.error(f"Error with Gemini extraction: {last_err}")
            return self._extract_with_regex(transcript)
            
        except Exception as e:
            logger.error(f"Error with Gemini extraction: {e}")
            return self._extract_with_regex(transcript)
    
    
    def _extract_with_regex(self, transcript: str) -> AppointmentData:
        """Fallback regex-based extraction (works without any API)"""
        data = AppointmentData()
        
        # Extract name (look for patterns like "I'm John Smith" or "This is John Smith")
        name_patterns = [
            r"(?:I'm|I am|This is|My name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+calling|\s+here)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                data.name = match.group(1).strip()
                break
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, transcript)
        if email_match:
            data.email = email_match.group(0)
        
        # Extract phone number
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
            r'\b\d{10}\b'
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, transcript)
            if phone_match:
                data.phone = phone_match.group(0)
                break
        
        # Extract appointment date/time
        date_patterns = [
            r'(?:next\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?:tomorrow|today)',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?'
        ]
        
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)\b',
            r'\b\d{1,2}\s*(?:am|pm|AM|PM)\b'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, transcript, re.IGNORECASE)
            if date_match:
                data.appointment_date = date_match.group(0)
                break
                
        for pattern in time_patterns:
            time_match = re.search(pattern, transcript, re.IGNORECASE)
            if time_match:
                data.appointment_time = time_match.group(0)
                break
        
        # Extract appointment reason (look for keywords)
        reason_keywords = [
            'back pain', 'headache', 'checkup', 'follow up', 'consultation',
            'symptoms', 'pain', 'injury', 'illness', 'medical', 'health',
            'chest pain', 'fever', 'cough', 'cold', 'flu'
        ]
        
        transcript_lower = transcript.lower()
        for keyword in reason_keywords:
            if keyword in transcript_lower:
                start = transcript_lower.find(keyword)
                context_start = max(0, start - 50)
                context_end = min(len(transcript), start + len(keyword) + 50)
                data.appointment_reason = transcript[context_start:context_end].strip()
                break
        
        return data
    
    def _parse_ai_response(self, content: str, fallback_data: AppointmentData) -> AppointmentData:
        """Parse AI response and merge with fallback data"""
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip().lower()
            if 'name:' in line:
                name = line.split('name:')[1].strip()
                if name and name != 'null':
                    fallback_data.name = name
            elif 'email:' in line:
                email = line.split('email:')[1].strip()
                if email and email != 'null':
                    fallback_data.email = email
            elif 'phone:' in line:
                phone = line.split('phone:')[1].strip()
                if phone and phone != 'null':
                    fallback_data.phone = phone
            elif 'date:' in line:
                date = line.split('date:')[1].strip()
                if date and date != 'null':
                    fallback_data.appointment_date = date
            elif 'time:' in line:
                time = line.split('time:')[1].strip()
                if time and time != 'null':
                    fallback_data.appointment_time = time
            elif 'reason:' in line:
                reason = line.split('reason:')[1].strip()
                if reason and reason != 'null':
                    fallback_data.appointment_reason = reason
        
        return fallback_data
