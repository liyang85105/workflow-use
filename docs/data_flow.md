1. 用户说话 → VoiceProcessor (extension/src/voice/)
   ↓
2. WebSocket → Python 语音服务 (workflows/voice_service/)
   ↓
3. 语音转文字 → 发送回浏览器
   ↓
4. Content Script → Background Script (VOICE_INPUT_EVENT)
   ↓
5. 存储在 voiceEvents[] 数组中
   ↓
6. 录制停止时 → 发送到 Python 服务器 (HttpRecordingStoppedEvent)
   ↓
7. RecordingService 接收 → 提取 voiceEvents
   ↓
8. EventCorrelator 关联 voice_events + browser_events
   ↓
9. EnhancedWorkflowGenerator 生成增强工作流