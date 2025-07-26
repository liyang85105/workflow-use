export class VoiceRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private isRecording: boolean = false;
  private stream: MediaStream | null = null;

  async startRecording(): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,      // Standard rate for speech recognition
          channelCount: 1,        // Mono
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      // Try different formats in order of compatibility
      const formats = [
        'audio/wav',
        'audio/mp4',
        'audio/ogg;codecs=opus',
        'audio/webm;codecs=opus'
      ];
      
      let selectedFormat = '';
      for (const format of formats) {
        if (MediaRecorder.isTypeSupported(format)) {
          selectedFormat = format;
          console.log(`✅ Using audio format: ${format}`);
          break;
        }
      }
      
      const options: MediaRecorderOptions = {
        audioBitsPerSecond: 32000  // Moderate bitrate
      };
      
      if (selectedFormat) {
        options.mimeType = selectedFormat;
      }
      
      this.mediaRecorder = new MediaRecorder(this.stream, options);
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
          console.log(`🎤 Audio chunk: ${event.data.size} bytes, type: ${event.data.type}`);
        }
      };
      
      this.mediaRecorder.onerror = (event) => {
        console.error('❌ MediaRecorder error:', event);
      };
      
      // Start recording with longer intervals to ensure adequate size
      this.mediaRecorder.start(2000); // 2 second chunks
      this.isRecording = true;
      console.log(`🎤 Recording started with format: ${selectedFormat || 'default'}`);
      
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      throw error;
    }
  }

  async stopRecording(): Promise<Blob | null> {
    if (!this.mediaRecorder || !this.isRecording) {
      console.log('⚠️ No active recording to stop');
      return null;
    }

    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve(null);
        return;
      }

      this.mediaRecorder.onstop = () => {
        console.log('🛑 Recording stopped, processing chunks...');
        
        if (this.audioChunks.length === 0) {
          console.warn('⚠️ No audio chunks recorded');
          resolve(null);
          return;
        }

        const audioBlob = new Blob(this.audioChunks, { 
          type: this.audioChunks[0]?.type || 'audio/webm' 
        });
        
        console.log(`✅ Created audio blob: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
        
        // Check if blob is large enough (minimum ~8KB for 0.1+ seconds)
        if (audioBlob.size < 8192) {
          console.warn(`⚠️ Audio blob too small (${audioBlob.size} bytes), may be rejected by API`);
        }
        
        this.audioChunks = [];
        this.isRecording = false;
        
        // Stop all tracks
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
        }
        
        resolve(audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }

  getRecordingState(): boolean {
    return this.isRecording;
  }

  // 清理资源
  dispose(): void {
    if (this.isRecording && this.mediaRecorder) {
      this.mediaRecorder.stop();
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
  }
}
