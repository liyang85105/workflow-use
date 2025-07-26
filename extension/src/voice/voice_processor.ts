import { VoiceRecorder } from './voice_recorder';

export class VoiceProcessor {
  private recorder: VoiceRecorder;
  private websocket: WebSocket | null;
  private websocketUrl: string;
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  
  // VAD 相关属性
  private isVADEnabled: boolean = true;
  private silenceThreshold: number = 0.01; // 静音阈值
  private silenceDuration: number = 1500; // 1.5秒静音后发送
  private minRecordingDuration: number = 500; // 最小录音时长500ms
  private silenceTimer: NodeJS.Timeout | null = null;
  private currentAudioChunks: Blob[] = [];
  private lastSoundTime: number = 0;
  private isProcessingSegment: boolean = false;

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
      
      // 启动 VAD 监听
      if (this.isVADEnabled) {
        this.startVADMonitoring();
      }
      
      console.log('语音录制已开始');
    } catch (error) {
      console.error('开始录音失败:', error);
      throw error;
    }
  }

  private startVADMonitoring(): void {
    // 获取音频流进行实时分析
    const stream = this.recorder.getMediaStream();
    if (!stream) return;

    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const checkAudioLevel = () => {
      if (!this.recorder.getRecordingState()) return;

      analyser.getByteFrequencyData(dataArray);
      
      // 计算音频能量
      const average = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength;
      const normalizedLevel = average / 255;

      const currentTime = Date.now();
      
      if (normalizedLevel > this.silenceThreshold) {
        // 检测到声音
        this.lastSoundTime = currentTime;
        
        // 清除静音计时器
        if (this.silenceTimer) {
          clearTimeout(this.silenceTimer);
          this.silenceTimer = null;
        }
        
        console.log(`🎵 Voice detected: ${normalizedLevel.toFixed(3)}`);
      } else {
        // 静音状态
        const silenceDuration = currentTime - this.lastSoundTime;
        
        if (silenceDuration > this.silenceDuration && !this.silenceTimer && !this.isProcessingSegment) {
          // 静音超过阈值，准备发送当前段
          console.log(`🔇 Silence detected for ${silenceDuration}ms, preparing to send segment`);
          this.silenceTimer = setTimeout(() => {
            this.sendCurrentSegment();
          }, 100); // 短暂延迟确保音频数据完整
        }
      }

      // 继续监听
      requestAnimationFrame(checkAudioLevel);
    };

    checkAudioLevel();
  }

  private async sendCurrentSegment(): Promise<void> {
    if (this.isProcessingSegment) return;
    
    this.isProcessingSegment = true;
    
    try {
      // 获取当前录音段
      const segmentBlob = await this.recorder.getCurrentSegment();
      
      if (segmentBlob && segmentBlob.size > 8192) {
        const recordingDuration = Date.now() - this.lastSoundTime + this.silenceDuration;
        
        if (recordingDuration >= this.minRecordingDuration) {
          console.log(`📤 Sending voice segment: ${segmentBlob.size} bytes`);
          
          // 使用语音开始时间而不是发送时间作为时间戳
          const voiceStartTime = this.lastSoundTime - recordingDuration + this.silenceDuration;
          
          this.sendAudioToServer(segmentBlob, voiceStartTime);
          
          // 清空当前段的数据
          this.recorder.clearCurrentSegment();
        } else {
          console.log(`⏱️ Segment too short (${recordingDuration}ms), keeping for next segment`);
        }
      }
    } catch (error) {
      console.error('❌ Error sending voice segment:', error);
    } finally {
      this.isProcessingSegment = false;
      this.silenceTimer = null;
    }
  }

  async stopRecording(): Promise<Blob | null> {
    try {
      if (this.recorder.getRecordingState()) {
        // 发送最后一段（如果有的话）
        if (!this.isProcessingSegment) {
          await this.sendCurrentSegment();
        }
        
        const audioBlob = await this.recorder.stopRecording();
        console.log('语音录制已停止');
        return audioBlob;
      }
      return null;
    } catch (error) {
      console.error('停止录音失败:', error);
      throw error;
    }
  }

  private sendAudioToServer(audioBlob: Blob, voiceStartTime?: number): void {
    if (!this.websocket || !this.isConnected) {
      console.error('WebSocket 未连接，无法发送音频数据');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result && this.websocket) {
        const base64Data = (reader.result as string).split(',')[1];
        
        try {
          const message = {
            type: 'audio_segment',
            data: base64Data,
            timestamp: voiceStartTime || Date.now(), // 使用语音开始时间
            voiceStartTime: voiceStartTime, // 语音开始时间
            voiceEndTime: Date.now(), // 语音结束时间
            size: audioBlob.size,
            mimeType: audioBlob.type,
            format: this.detectAudioFormat(audioBlob.type),
            isSegment: true
          };
          
          this.websocket.send(JSON.stringify(message));
          console.log(`✅ Audio segment sent with timestamp: ${voiceStartTime}`);
          
        } catch (error) {
          console.error('❌ Failed to send audio segment:', error);
        }
      }
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
