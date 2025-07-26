import { VoiceRecorder } from './voice_recorder';

export class VoiceProcessor {
  private recorder: VoiceRecorder;
  private websocket: WebSocket | null;
  private websocketUrl: string;
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

  private constructor(websocket: WebSocket, url: string) {
    this.recorder = new VoiceRecorder();
    this.websocket = websocket;
    this.websocketUrl = url;
    this.setupWebSocketHandlers();
  }

  public static async create(
    url = 'ws://127.0.0.1:8765/voice-stream'
  ): Promise<VoiceProcessor> {
    return new Promise((resolve, reject) => {
      const websocket = new WebSocket(url);

      websocket.onopen = () => {
        console.log('WebSocket 连接已建立');
        const processor = new VoiceProcessor(websocket, url);
        processor.isConnected = true;
        resolve(processor);
      };

      websocket.onerror = (error) => {
        console.error('WebSocket 创建失败:', error);
        reject(new Error('无法连接到 WebSocket 服务器'));
      };
    });
  }

  private setupWebSocketHandlers(): void {
    if (!this.websocket) {
      console.error('WebSocket is null, cannot setup handlers');
      return;
    }

    try {
      this.websocket.onopen = () => {
        console.log('WebSocket 连接已建立');
        this.isConnected = true;
        this.reconnectAttempts = 0;
      };

      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'transcription') {
            this.handleTranscription(data.text, data.timestamp);
          }
        } catch (error) {
          console.error('解析 WebSocket 消息失败:', error);
        }
      };

      this.websocket.onclose = () => {
        console.log('WebSocket 连接已断开');
        this.isConnected = false;
        this.attemptReconnect();
      };

      this.websocket.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        this.isConnected = false;
      };
    } catch (error) {
      console.error('创建 WebSocket 连接失败:', error);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连 WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.reconnectWebSocket();
      }, 2000 * this.reconnectAttempts);
    } else {
      console.error('WebSocket 重连失败，已达到最大尝试次数');
    }
  }

  private reconnectWebSocket(): void {
    try {
      this.websocket = new WebSocket(this.websocketUrl);
      this.setupWebSocketHandlers();
    } catch (error) {
      console.error('重连 WebSocket 失败:', error);
      this.attemptReconnect();
    }
  }

  private handleTranscription(text: string, timestamp: number): void {
    // 将转录文本与浏览器事件时间戳关联
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      chrome.runtime.sendMessage({
        type: 'VOICE_INPUT',
        text: text,
        timestamp: timestamp
      }).catch(error => {
        console.error('发送语音输入消息失败:', error);
      });
    } else {
      // 如果不在 Chrome 扩展环境中，使用其他方式处理
      this.handleVoiceInputFallback(text, timestamp);
    }
  }

  private handleVoiceInputFallback(text: string, timestamp: number): void {
    // 备用处理方案，例如使用 postMessage 或自定义事件
    window.postMessage({
      type: 'VOICE_INPUT',
      text: text,
      timestamp: timestamp
    }, '*');
  }

  async startRecording(): Promise<void> {
    if (!this.isConnected) {
      throw new Error('WebSocket 未连接，无法开始录音');
    }
    
    try {
      await this.recorder.startRecording();
      console.log('语音录制已开始');
    } catch (error) {
      console.error('开始录音失败:', error);
      throw error;
    }
  }

  async stopRecording(): Promise<Blob | null> {
    try {
      if (this.recorder.getRecordingState()) {
        const audioBlob = await this.recorder.stopRecording();
        
        if (audioBlob) {
          console.log(`🎵 Audio blob created: ${audioBlob.size} bytes`);
          
          // Check minimum size before sending
          if (audioBlob.size < 8192) { // 8KB minimum
            console.warn('⚠️ Audio too small, not sending to server');
            return audioBlob;
          }
          
          // 将音频数据发送到服务器
          if (this.websocket && this.isConnected) {
            this.sendAudioToServer(audioBlob);
          }
        }
        
        console.log('语音录制已停止');
        return audioBlob;
      }
      return null;
    } catch (error) {
      console.error('停止录音失败:', error);
      throw error;
    }
  }

  private sendAudioToServer(audioBlob: Blob): void {
    if (!this.websocket || !this.isConnected) {
      console.error('WebSocket 未连接，无法发送音频数据');
      return;
    }

    console.log(`🎵 Preparing to send audio blob, size: ${audioBlob.size} bytes, type: ${audioBlob.type}`);

    // Check if blob is large enough
    if (audioBlob.size < 8192) {
      console.warn(`⚠️ Audio blob too small (${audioBlob.size} bytes), skipping transmission`);
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result && this.websocket) {
        const base64Data = (reader.result as string).split(',')[1];
        console.log(`📦 Base64 audio data length: ${base64Data.length}`);
        
        try {
          const message = {
            type: 'audio', 
            data: base64Data,
            timestamp: Date.now(),
            size: audioBlob.size,
            mimeType: audioBlob.type,
            format: this.detectAudioFormat(audioBlob.type)
          };
          
          const messageStr = JSON.stringify(message);
          console.log(`📤 Sending ${audioBlob.type} audio, message size: ${messageStr.length} characters`);
          
          this.websocket.send(messageStr);
          console.log('✅ Audio data sent successfully');
          
          this.waitForTranscription();
          
        } catch (error) {
          console.error('❌ Failed to send audio data:', error);
        }
      }
    };
    
    reader.onerror = (error) => {
      console.error('❌ Failed to read audio blob:', error);
    };
    
    reader.readAsDataURL(audioBlob);
  }

  private detectAudioFormat(mimeType: string): string {
    if (mimeType.includes('wav')) return 'wav';
    if (mimeType.includes('mp4')) return 'mp4';
    if (mimeType.includes('ogg')) return 'ogg';
    if (mimeType.includes('webm')) return 'webm';
    return 'unknown';
  }

  private waitForTranscription(): void {
    const timeout = setTimeout(() => {
      console.warn('⏰ No transcription received within 30 seconds');
    }, 30000);
    
    // Clear timeout when transcription is received
    const originalOnMessage = this.websocket?.onmessage;
    if (this.websocket) {
      this.websocket.onmessage = (event) => {
        clearTimeout(timeout);
        console.log('🎯 Transcription response received:', event.data);
        if (originalOnMessage && this.websocket) {
          originalOnMessage.call(this.websocket, event);
        }
      };
    }
  }

  dispose(): void {
    this.recorder.dispose();
    
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
    
    this.isConnected = false;
  }
}
