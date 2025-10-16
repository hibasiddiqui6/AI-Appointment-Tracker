#!/usr/bin/env python3
"""
Runner to start the FastAPI API and LiveKit RTC listener from the backend directory.
"""

import os
import sys
import threading
import time

# Ensure we execute relative to this file's directory for reliable imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.getcwd() != SCRIPT_DIR:
    os.chdir(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

def run_fastapi_server():
    """Run the FastAPI server."""
    print("🚀 Starting FastAPI Server...")
    from fastapi_server import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

def run_livekit_listener():
    """Run the LiveKit RTC listener."""
    print("🎧 Starting LiveKit Call Listener (rtc)...")
    try:
        import asyncio as _asyncio
        from livekit_listener import run_rtc_listener
        _asyncio.run(run_rtc_listener())
    except Exception as e:
        print(f"❌ Error starting LiveKit listener: {e}")

if __name__ == "__main__":
    print("🎯 Starting LiveKit Appointment Extraction System")
    print("=" * 60)
    print(f"📍 Backend directory: {SCRIPT_DIR}")
    print("🌐 FastAPI server: http://localhost:8000")
    print("📋 API docs: http://localhost:8000/docs")
    print("🎧 LiveKit listener: Active")
    print()

    # Start FastAPI server
    fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    fastapi_thread.start()

    # Give the server a moment to start
    time.sleep(2)

    # Start LiveKit listener
    listener_thread = threading.Thread(target=run_livekit_listener, daemon=True)
    listener_thread.start()

    print("✅ Both services started successfully!")
    print()
    print("🎤 Ready for LiveKit calls and token generation!")
    print("💡 Press Ctrl+C to stop both services")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        print("✅ Services stopped successfully!")
