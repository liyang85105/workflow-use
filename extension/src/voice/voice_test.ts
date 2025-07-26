export class SimpleVoiceTest {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private isRecording: boolean = false;

  async testMicrophoneAccess(): Promise<boolean> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('✅ 麦克风访问成功');
      
      // 立即停止流以释放麦克风
      stream.getTracks().forEach(track => track.stop());
      return true;
    } catch (error) {
      console.error('❌ 麦克风访问失败:', error);
      return false;
    }
  }

  async startTestRecording(): Promise<void> {
    if (this.isRecording) {
      console.log('⚠️ 已在录音中');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
          console.log('📝 录音数据块:', event.data.size, 'bytes');
        }
      };

      this.mediaRecorder.onstart = () => {
        console.log('🎤 录音开始');
        this.isRecording = true;
      };

      this.mediaRecorder.onstop = () => {
        console.log('⏹️ 录音停止');
        this.isRecording = false;
        this.processRecording();
      };

      this.mediaRecorder.onerror = (event) => {
        console.error('❌ 录音错误:', event);
      };

      this.mediaRecorder.start(1000); // 每1秒收集一次数据
      console.log('🚀 开始录音测试...');
      
    } catch (error) {
      console.error('❌ 启动录音失败:', error);
      throw error;
    }
  }

  stopTestRecording(): void {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      
      // 停止所有音频轨道
      if (this.mediaRecorder.stream) {
        this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
      }
    } else {
      console.log('⚠️ 没有正在进行的录音');
    }
  }

  private processRecording(): void {
    if (this.audioChunks.length === 0) {
      console.log('⚠️ 没有录音数据');
      return;
    }

    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    console.log('✅ 录音完成，大小:', audioBlob.size, 'bytes');
    
    // 创建播放链接进行测试
    const audioUrl = URL.createObjectURL(audioBlob);
    console.log('🔗 录音播放链接:', audioUrl);
    
    // 可选：自动播放测试
    this.playTestAudio(audioUrl);
    
    // 清空数据为下次录音做准备
    this.audioChunks = [];
  }

  private playTestAudio(audioUrl: string): void {
    const audio = new Audio(audioUrl);
    audio.onloadeddata = () => {
      console.log('✅ 音频数据加载完成，时长:', audio.duration, '秒');
    };
    
    audio.onended = () => {
      console.log('✅ 音频播放完成');
      URL.revokeObjectURL(audioUrl); // 清理内存
    };

    audio.onerror = (error) => {
      console.error('❌ 音频播放错误:', error);
    };

    // 开始播放
    audio.play().catch(error => {
      console.error('❌ 无法播放音频:', error);
    });
  }

  getRecordingStatus(): string {
    return this.isRecording ? '录音中' : '未录音';
  }
}