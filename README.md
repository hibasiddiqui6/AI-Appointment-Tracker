# AI Appointment Tracker - LiveKit Call Listener

This project listens to LiveKit calls and automatically extracts appointment information (name, email, phone, date/time, reason) from the conversation transcript, then sends the data to an n8n webhook. It includes both a backend API service and a frontend web interface for testing.

## Features

- 🎧 **LiveKit Integration**: Connects to LiveKit rooms and processes audio
- 🗣️ **Speech-to-Text**: Real-time transcription with Deepgram or local Whisper
- 🤖 **AI Data Extraction**: Uses Google Gemini to extract structured appointment data
- 📤 **n8n Webhook**: Sends extracted data to n8n workflow
- 📊 **Airtable Integration**: Optional bonus feature to create records in Airtable
- 🌐 **Web Interface**: Frontend for easy testing and token generation
- 🧪 **Demo Testing**: Includes test scripts for validation
- 
## Project Structure

```
AI-Appointment-Tracker/
├── backend/                    # Backend API and services
│   ├── config.py              # Configuration management
│   ├── models.py              # Data models (API + Appointment)
│   ├── fastapi_server.py      # FastAPI token generation API
│   ├── livekit_listener.py    # LiveKit call listener agent
│   ├── data_extractor_multi.py # AI data extraction
│   ├── speech_to_text.py      # Speech-to-text services
│   ├── webhook_sender.py      # n8n webhook integration
│   └── run_system.py          # Start both API server and LiveKit listener
├── frontend/                   # Web interface for testing
│   ├── index.html             # Main web page
│   ├── main.js                # LiveKit client integration
│   └── style.css              # Styling
├── requirements.txt            # Python dependencies
└── README.md                  # This file
```

## Quick Start

### 1. Set Up Virtual Environment

**For Linux/macOS:**

```bash
# Create virtual environment
python3 -m venv venv
# Activate virtual environment
source venv/bin/activate
# Verify activation (should show venv path)
which python
```

**For Windows:**

```cmd
# Create virtual environment
python -m venv venv
# Activate virtual environment
venv\Scripts\activate
# Verify activation (should show venv path)
where python
```

### 2. Install Dependencies

```bash
# Make sure virtual environment is activated
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root with your credentials:
```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
# AI Configuration (Google Gemini - FREE)
GEMINI_API_KEY=your-gemini-api-key
# Speech-to-Text Configuration (Choose ONE)
DEEPGRAM_API_KEY=your-deepgram-api-key
# Leave empty for local Whisper
# n8n Webhook
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/appointment-data
```

### 4. Start the Complete System

**Start Backend Services:**

```bash
# Make sure virtual environment is activated
cd backend
python run_system.py
```

**Start Frontend (in a new terminal):**

```bash
# Serve the frontend (simple HTTP server)
cd frontend
python -m http.server 3000
# Or use any other static file server
```

**Access the Application:**

- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Frontend Interface: http://localhost:3000
This starts both backend services in a single terminal:
- **FastAPI Server** at `http://localhost:8000` with:
  - **POST /generate-token** - Generate LiveKit access tokens
  - **GET /health** - Health check
  - **GET /config** - Configuration status
  - **GET /docs** - Interactive API documentation
- **LiveKit Listener** - Agent that listens to calls and extracts appointment data
The frontend provides a simple web interface to:
- Generate LiveKit tokens
- Join test calls
- Monitor call status
**Note:** Backend services run simultaneously. Press `Ctrl+C` to stop both.
  
## How It Works

1. **Call Connection**: Connects to LiveKit room and listens for participants
2. **Audio Processing**: Captures audio from participants
3. **Transcription**: Converts audio to text (using LiveKit's built-in or external service)
4. **Data Extraction**: Uses AI to extract structured appointment data:
   - Name
   - Email address
   - Phone number
   - Appointment date & time
   - Appointment reason
5. **Webhook Delivery**: Sends JSON payload to n8n webhook when call ends
6. **Airtable Record**: Optionally creates record in Airtable

## Data Format

The extracted data is sent as JSON to your n8n webhook:
```json
{
  "name": "John Smith",
  "email": "john.smith@email.com",
  "phone": "555-123-4567",
  "appointment_date": "Next Tuesday",
  "appointment_time": "2:00 PM",
  "appointment_reason": "back pain",
  "call_duration": 180.5,
  "transcript": "Hello, this is John Smith calling...",
  "extracted_at": "2024-01-15T10:30:00"
}
```

## Demo Preparation

For the live demonstration:
1. **Setup**: Ensure all credentials are configured in `.env` file
2. **Test**: Run `python test_system.py` to verify everything works
3. **Start Services**: 
   - Run `python run_system.py` (starts both API server and LiveKit agent)
4. **Generate Token**: Use the API to get a token
5. **Join Call**: Use LiveKit Meet or any LiveKit client with the token
6. **Show Results**: Demonstrate the webhook receiving data and Airtable record creation
   
### Quick Demo Steps:

1. **Start Backend**: `cd backend && python run_system.py`
2. **Start Frontend**: `cd frontend && python -m http.server 3000`
3. **Open Web Interface**: Visit http://localhost:3000
4. **Generate Token**: Use the web interface to create a token
5. **Join Call**: Click "Start Call" and speak: *"Hi, I'm John Smith, my email is john@email.com, I'd like to schedule an appointment for next Tuesday at 2 PM for a checkup."*
6. **End Call**: Click "Leave" and check the webhook data in n8n
   
## Configuration Options

### Speech-to-Text Services

The system can be configured to use different STT services:
- **Deepgram** (Recommended) - Cloud-based, high accuracy, FREE tier
- **Local Whisper** - OpenAI's Whisper running locally, no API needed

### Data Extraction

Uses Google Gemini for intelligent extraction with regex fallback for reliability.

### Error Handling

- Graceful fallback if AI services are unavailable
- Comprehensive logging for debugging
- Webhook retry logic (can be added)

### Project Dependencies

The project uses the following main dependencies:
- **LiveKit**: Real-time communication platform
- **FastAPI**: Modern web framework for APIs
- **Google Gemini**: AI for data extraction
- **Deepgram/Whisper**: Speech-to-text services
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server

### File Structure Details

- `backend/`: Contains all Python backend code
- `frontend/`: Contains HTML, CSS, and JavaScript for web interface
- `requirements.txt`: Python package dependencies
- `.env`: Environment variables (create this file)
