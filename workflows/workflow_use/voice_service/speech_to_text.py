import asyncio
import json
import websockets
from openai import OpenAI
from datetime import datetime
import queue
import io
import os
from typing import Optional, Set
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeechToTextService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        try:
            # 初始化OpenAI客户端
            self.client = OpenAI(
                api_key=api_key or os.getenv('OPENAI_API_KEY'),
                base_url=base_url or os.getenv('OPENAI_BASE_URL')
            )
            
            if not (api_key or os.getenv('OPENAI_API_KEY')):
                logger.warning("OpenAI API key not provided. Audio transcription will be disabled.")
                self.transcription_enabled = False
            else:
                self.transcription_enabled = True
            
            logger.info(f"Using API base URL: {base_url or os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1'}")
            logger.info(f"Transcription enabled: {self.transcription_enabled}")
            
            self.audio_queue = queue.Queue()
            self.clients: Set[websockets.WebSocketServerProtocol] = set()
            
            # Whisper API 配置
            self.whisper_model = "whisper-1"
            self.language = "zh"  # 中文
            
            # 添加配置选项
            self.enable_streaming = os.getenv('VOICE_STREAMING_ENABLED', 'true').lower() == 'true'
            self.chunk_size = int(os.getenv('VOICE_CHUNK_SIZE', '8192'))
            
        except Exception as e:
            logger.error(f"Failed to initialize SpeechToTextService: {e}")
            raise
        
    async def handle_client(self, websocket):
        path = websocket.request.path
        logger.info(f"Incoming connection attempt to path: {path}")
        
        try:
            # 检查路径是否正确
            if path != "/voice-stream":
                logger.warning(f"Client tried to connect to invalid path: {path}")
                await websocket.close(code=4004, reason="Invalid path")
                return
                
            self.clients.add(websocket)
            logger.info(f"✅ New client connected to {path}. Total clients: {len(self.clients)}")
            
            # 发送欢迎消息确认连接
            try:
                welcome_msg = {
                    'type': 'connection',
                    'status': 'connected',
                    'message': 'Speech-to-text service ready'
                }
                await websocket.send(json.dumps(welcome_msg, ensure_ascii=False))
                logger.info("✅ Welcome message sent successfully")
            except Exception as e:
                logger.error(f"❌ Failed to send welcome message: {e}")
                raise
            
            async for message in websocket:
                logger.info(f"📨 Received message type: {type(message)}")
                logger.info(f"📏 Message length: {len(message) if hasattr(message, '__len__') else 'N/A'}")
                
                # Log first 100 characters of message for debugging
                if isinstance(message, str):
                    logger.info(f"📝 Message preview: {message[:100]}...")
                
                # 处理来自浏览器的音频数据
                await self.process_audio_chunk(message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # 尝试关闭连接
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass
        finally:
            self.clients.discard(websocket)  # 使用discard避免KeyError
            logger.info(f"Client removed. Total clients: {len(self.clients)}")

    async def process_audio_chunk(self, audio_data):
        """优化的音频处理 - 支持流式识别"""
        try:
            # 快速响应确认收到
            await self.send_ack_to_client("音频接收中...")
            
            # 异步处理识别
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self.transcribe_audio, audio_data)
            
            if text:
                await self.broadcast_transcription(text, datetime.now().timestamp())
                
        except Exception as e:
            await self.send_error_to_client(f"识别失败: {str(e)}")

    def transcribe_audio(self, audio_data) -> Optional[str]:
        """
        使用OpenAI Whisper API转录音频
        
        Args:
            audio_data: 音频数据 (bytes)
            
        Returns:
            转录的文本或None
        """
        if not self.transcription_enabled:
            logger.warning("Transcription is disabled - no API key provided")
            return "Transcription disabled - no API key"
        
        try:
            # 确保音频数据是bytes类型
            if isinstance(audio_data, str):
                import base64
                try:
                    audio_data = base64.b64decode(audio_data)
                    logger.info(f"Decoded base64 audio data, size: {len(audio_data)} bytes")
                except Exception as decode_error:
                    logger.error(f"Failed to decode base64 audio data: {decode_error}")
                    return None
            
            if not isinstance(audio_data, bytes):
                logger.error(f"Invalid audio data type: {type(audio_data)}")
                return None
            
            # 检查音频数据大小
            min_size = 8192  # 8KB minimum
            if len(audio_data) < min_size:
                logger.warning(f"Audio data too small ({len(audio_data)} bytes < {min_size})")
                return "[录音时间太短，请录制至少0.1秒]"
            
            if len(audio_data) > 25 * 1024 * 1024:
                logger.warning("Audio data too large (>25MB), skipping transcription")
                return None
            
            # 尝试不同的文件扩展名，从最兼容的开始
            extensions_to_try = [
                ("audio.wav", "WAV format"),
                ("audio.mp3", "MP3 format"), 
                ("audio.m4a", "M4A format"),
                ("audio.ogg", "OGG format"),
                ("audio.webm", "WebM format")
            ]
            
            for filename, format_name in extensions_to_try:
                try:
                    audio_file = io.BytesIO(audio_data)
                    audio_file.name = filename
                    
                    logger.info(f"Trying {format_name}: {len(audio_data)} bytes")
                    
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    
                    # 正确获取转录文本 - response.text 而不是 response.strip()
                    text = response.text if hasattr(response, 'text') else str(response)
                    text = text.strip() if text else ""
                    
                    if text:
                        logger.info(f"✅ Transcription successful with {format_name}: {text[:50]}...")
                        return text
                    else:
                        logger.warning(f"Empty transcription result with {format_name}")
                        continue
                        
                except Exception as format_error:
                    error_msg = str(format_error)
                    logger.warning(f"Failed with {format_name}: {error_msg}")
                    
                    # If it's the token counting error, try next format
                    if "count_audio_tokens_failed" in error_msg:
                        continue
                    # If it's other errors, also try next format
                    elif "500" in error_msg or "invalid_request_error" in error_msg.lower():
                        continue
                    else:
                        # For other errors, might be worth trying other formats
                        continue
            
            # If all formats failed
            logger.error("All audio formats failed transcription")
            return "[音频格式不兼容，请重新录制]"
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"Transcription error: {error_message}")
            
            # 特定错误处理
            if "too short" in error_message.lower():
                logger.error("Audio too short - minimum 0.1 seconds required")
                return "[录音时间太短，请录制至少0.1秒]"
            elif "count_audio_tokens_failed" in error_message:
                logger.error("API provider failed to count audio tokens")
                return "[音频格式不兼容，请重新录制]"
            elif "500" in error_message:
                logger.error("API provider server error")
                return "[服务器错误，请稍后重试]"
            
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return "[转录失败，请重试]"

    async def broadcast_transcription(self, text: str, timestamp: float):
        """广播转录结果到所有连接的客户端"""
        message = {
            'type': 'transcription',
            'text': text,
            'timestamp': timestamp,
            'source': 'openai-whisper'
        }
        
        logger.info(f"Broadcasting transcription: {text}")
        
        # 发送给所有连接的客户端
        if self.clients:
            # 创建发送任务列表
            tasks = []
            for client in self.clients.copy():  # 使用copy避免在迭代时修改集合
                tasks.append(self.send_to_client(client, message))
            
            # 并发发送消息
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_client(self, client, message):
        """发送消息给单个客户端"""
        try:
            await client.send(json.dumps(message, ensure_ascii=False))
        except websockets.exceptions.ConnectionClosed:
            # 客户端连接已关闭，从集合中移除
            self.clients.discard(client)
            logger.info("Removed disconnected client")
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            self.clients.discard(client)

    async def start_server(self, host='localhost', port=8765):
        """启动WebSocket服务器"""
        logger.info(f"Starting speech-to-text server on {host}:{port}")
        logger.info(f"WebSocket endpoint: ws://{host}:{port}/voice-stream")
        
        async with websockets.serve(self.handle_client, host, port):
            logger.info(f"Server is running. Connect to: ws://{host}:{port}/voice-stream")
            await asyncio.Future()  # 永远运行

    def set_language(self, language: str):
        """设置识别语言"""
        self.language = language
        logger.info(f"Language set to: {language}")

    def set_model(self, model: str):
        """设置Whisper模型"""
        self.whisper_model = model
        logger.info(f"Model set to: {model}")


async def main():
    try:
        # Use environment variables instead of hardcoded values
        api_key = os.getenv('OPENAI_API_KEY')
        base_url = os.getenv('OPENAI_BASE_URL')
        
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            logger.info("Please set OPENAI_API_KEY in your .env file")
            return
            
        service = SpeechToTextService(api_key=api_key, base_url=base_url)
        
        # 可选：设置不同的语言或模型
        # service.set_language("en")  # 英文
        # service.set_model("whisper-1")
        
        # 启动服务器
        await service.start_server(host='0.0.0.0', port=8765)
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
