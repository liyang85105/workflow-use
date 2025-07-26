import asyncio
import json
import base64
import websockets

async def test_websocket_connection(host='localhost', port=8765):
    """测试WebSocket连接"""
    uri = f"ws://{host}:{port}/voice-stream"
    print(f"Testing connection to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connection successful!")
            
            # 等待欢迎消息
            try:
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Received: {welcome}")
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for welcome message")
                return
            
            # 发送测试消息
            test_msg = json.dumps({"type": "test", "message": "hello"})
            await websocket.send(test_msg)
            print("📤 Sent test message")
            
            print("✅ All tests passed!")
            
    except ConnectionRefusedError:
        print("❌ Connection refused - server may not be running")
    except websockets.exceptions.InvalidURI:
        print("❌ Invalid URI")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed unexpectedly: {e}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

# 测试WebSocket连接的工具函数
async def test_websocket_connection(host='localhost', port=8765):
    """测试WebSocket连接"""
    uri = f"ws://{host}:{port}/voice-stream"
    print(f"Testing connection to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connection successful!")
            
            # 等待欢迎消息
            try:
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Received: {welcome}")
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for welcome message")
                return
            
            # 发送测试消息
            test_msg = json.dumps({"type": "test", "message": "hello"})
            await websocket.send(test_msg)
            print("📤 Sent test message")
            
            print("✅ All tests passed!")
            
    except ConnectionRefusedError:
        print("❌ Connection refused - server may not be running")
    except websockets.exceptions.InvalidURI:
        print("❌ Invalid URI")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed unexpectedly: {e}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

async def run_connection_test():
    await test_websocket_connection()

if __name__ == "__main__":
    asyncio.run(run_connection_test())

async def test_websocket_with_audio():
    """Test WebSocket with actual audio data"""
    uri = "ws://localhost:8765/voice-stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"📨 Welcome: {welcome}")
            
            # Send test audio file (you need a small audio file)
            with open("test_audio.webm", "rb") as f:
                audio_data = f.read()
                base64_audio = base64.b64encode(audio_data).decode()
                
                message = {
                    "type": "audio",
                    "data": base64_audio,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                await websocket.send(json.dumps(message))
                print("📤 Sent audio data")
                
                # Wait for transcription response
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                print(f"🎯 Transcription: {response}")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_with_audio())
