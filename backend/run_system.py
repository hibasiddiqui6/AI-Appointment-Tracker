#!/usr/bin/env python3
"""
Script to run both the backend FastAPI server and LiveKit listener from project root
"""

import sys
import os
import asyncio
import threading
import time

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Change to backend directory
os.chdir(backend_path)

def run_fastapi_server():
    """Run the FastAPI server in a separate thread"""
    print("🚀 Starting FastAPI Server...")
    from fastapi_server import app
    import uvicorn
    
    # Run uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

def run_livekit_listener():
    """Run the LiveKit RTC listener in this thread"""
    print("🎧 Starting LiveKit Call Listener (rtc)...")
    try:
        # Start direct RTC listener coroutine
        import asyncio as _asyncio
        from livekit_listener import run_rtc_listener
        _asyncio.run(run_rtc_listener())
    except Exception as e:
        print(f"❌ Error starting LiveKit listener: {e}")

if __name__ == "__main__":
    print("🎯 Starting LiveKit Appointment Extraction System")
    print("=" * 60)
    print("📍 Backend directory:", backend_path)
    print("🌐 FastAPI server: http://localhost:8000")
    print("📋 API docs: http://localhost:8000/docs")
    print("🎧 LiveKit listener: Active")
    print()
    
    # Start FastAPI server in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    fastapi_thread.start()
    
    # Give the server a moment to start
    time.sleep(2)
    
    # Start LiveKit listener in a separate thread
    listener_thread = threading.Thread(target=run_livekit_listener, daemon=True)
    listener_thread.start()
    
    print("✅ Both services started successfully!")
    print()
    print("🎤 Ready for LiveKit calls and token generation!")
    print("💡 Press Ctrl+C to stop both services")
    print()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        print("✅ Services stopped successfully!")
