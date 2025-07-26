import asyncio
import io
import struct
from openai import OpenAI

def create_test_wav(duration_seconds=1.0, sample_rate=16000):
    """Create a proper WAV file with actual audio data"""
    
    # Calculate number of samples
    num_samples = int(duration_seconds * sample_rate)
    
    # Create audio data (simple sine wave tone)
    import math
    frequency = 440  # A4 note
    audio_data = []
    
    for i in range(num_samples):
        # Generate a sine wave
        sample = int(32767 * 0.1 * math.sin(2 * math.pi * frequency * i / sample_rate))
        audio_data.append(struct.pack('<h', sample))  # 16-bit little-endian
    
    audio_bytes = b''.join(audio_data)
    
    # WAV header
    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + len(audio_bytes),  # File size - 8
        b'WAVE',
        b'fmt ',
        16,  # PCM header size
        1,   # PCM format
        1,   # Mono
        sample_rate,
        sample_rate * 2,  # Byte rate
        2,   # Block align
        16,  # Bits per sample
        b'data',
        len(audio_bytes)
    )
    
    return wav_header + audio_bytes

async def test_whisper_api():
    """Test Whisper API directly with a proper audio file"""
    
    client = OpenAI(
        api_key="sk-0uQzUWXvWFgXqNDDLAlj4LU5XhiBRBYv8KE8svr4p9nb7Nuk",
        base_url="https://api.100dog.com/v1"
    )
    
    try:
        # Create 1 second of test audio
        wav_data = create_test_wav(duration_seconds=1.0)
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "test.wav"
        
        print(f"Testing Whisper API with {len(wav_data)} bytes of audio...")
        
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        
        print(f"✅ API test successful: {response}")
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(test_whisper_api())
