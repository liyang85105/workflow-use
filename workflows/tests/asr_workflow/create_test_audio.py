import asyncio
import json
import base64
import websockets
from pathlib import Path

async def test_with_sample_audio():
    """Test with a sample audio file"""
    # Create a simple test audio file or use existing one
    audio_file = Path("test_audio.webm")
    
    if not audio_file.exists():
        print("❌ Please create a test_audio.webm file first")
        print("You can record a short audio using browser and save it")
        return
    
    uri = "ws://localhost:8765/voice-stream"
    
    async with websockets.connect(uri) as websocket:
        print("✅ Connected")
        
        # Wait for welcome
        welcome = await websocket.recv()
        print(f"Welcome: {welcome}")
        
        # Send audio
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
            base64_audio = base64.b64encode(audio_bytes).decode()
            
            message = {
                "type": "audio",
                "data": base64_audio
            }
            
            await websocket.send(json.dumps(message))
            print(f"📤 Sent {len(audio_bytes)} bytes of audio")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                result = json.loads(response)
                print(f"🎯 Transcription: {result.get('text', 'No text')}")
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for transcription")

if __name__ == "__main__":
    asyncio.run(test_with_sample_audio())