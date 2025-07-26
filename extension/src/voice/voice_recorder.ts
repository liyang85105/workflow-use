export class VoiceRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private currentSegmentChunks: Blob[] = []; // 当前段的音频块
  private stream: MediaStream | null = null;
  private isRecording: boolean = false;

  async startRecording(): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000 // 优化语音识别
        } 
      });

      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000 // 降低比特率，适合语音
      });

      this.audioChunks = [];
      this.currentSegmentChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
          this.currentSegmentChunks.push(event.data); // 同时添加到当前段
        }
      };

      this.mediaRecorder.start(100); // 每100ms产生一个数据块，便于实时处理
      this.isRecording = true;
      
      console.log('✅ MediaRecorder started with segment support');
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      throw error;
    }
  }

  async getCurrentSegment(): Promise<Blob | null> {
    if (this.currentSegmentChunks.length === 0) {
      return null;
    }

    // 创建当前段的 Blob
    const segmentBlob = new Blob(this.currentSegmentChunks, { 
      type: 'audio/webm;codecs=opus' 
    });
    
    return segmentBlob;
  }

  clearCurrentSegment(): void {
    // 清空当前段，但保留总的录音数据
    this.currentSegmentChunks = [];
    console.log('🧹 Current segment cleared');
  }

  getMediaStream(): MediaStream | null {
    return this.stream;
  }

  getRecordingState(): boolean {
    return this.isRecording;
  }

  async stopRecording(): Promise<Blob | null> {
    if (!this.mediaRecorder || !this.isRecording) {
      return null;
    }

    return new Promise((resolve) => {
      if (this.mediaRecorder) {
        this.mediaRecorder.onstop = () => {
          const audioBlob = new Blob(this.audioChunks, { 
            type: 'audio/webm;codecs=opus' 
          });
          this.isRecording = false;
          resolve(audioBlob);
        };

        this.mediaRecorder.stop();
      }
    });
  }

  dispose(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.currentSegmentChunks = [];
    this.isRecording = false;
  }
}
