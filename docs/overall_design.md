# 语音增强工作流扩展设计方案

## 概述

在原有 Workflow-Use 架构基础上，集成语音输入功能，实现多模态工作流创建。用户可以通过语音描述意图，同时进行浏览器操作，系统会智能理解并生成更精确的工作流。

## 架构扩展设计

### 1. 整体架构变化

```
原有架构:
浏览器交互 → 扩展录制 → JSON 工作流

新架构:
浏览器交互 ┐
           ├→ 多模态处理器 → 增强型工作流生成器 → JSON 工作流
语音输入    ┘
```

### 2. 新增组件

#### A. 语音捕获模块 (extension/src/voice/)
```typescript
// voice-recorder.ts
export class VoiceRecorder {
  async startRecording(): Promise<void> {}
  stopRecording(): Promise<Blob> {}
}

// voice-processor.ts
export class VoiceProcessor {
  private setupWebSocket() {}

  private handleTranscription(text: string, timestamp: number) {}
}
```

#### B. 实时语音转文字服务 (workflows/voice_service/)
```python
# speech_to_text.py
class SpeechToTextService:
    def __init__(self):
        pass

    async def handle_client(self, websocket, path):
        pass

    def transcribe_audio(self, audio_data):
        pass

    async def broadcast_transcription(self, text, timestamp):
        pass
```

#### C. 多模态意图理解器 (workflows/intent_processor/)
```python
# intent_analyzer.py
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

@dataclass
class VoiceIntent:
    text: str
    timestamp: float
    intent_type: str  # 'filter', 'select', 'action', 'condition'
    parameters: Dict
    confidence: float

@dataclass
class BrowserEvent:
    event_type: str
    element: Dict
    timestamp: float
    coordinates: Optional[Tuple[int, int]]

class MultiModalIntentAnalyzer:
    def __init__(self):
        pass

    def analyze_voice_intent(self, voice_text: str, timestamp: float) -> VoiceIntent:
        pass

    def correlate_events(self, voice_intents: List[VoiceIntent], 
                        browser_events: List[BrowserEvent]) -> List[Dict]:
        """关联语音意图和浏览器事件"""
        pass
```

#### D. 增强型工作流生成器 (workflows/enhanced_generator/)
```python
# enhanced_workflow_generator.py
class EnhancedWorkflowGenerator:
    def __init__(self):
        pass

    def generate_workflow(self, browser_events: List[BrowserEvent], 
                         voice_intents: List[VoiceIntent]) -> Dict[str, Any]:
        """生成增强型工作流"""
        workflow = None       
        # 1. 关联语音和浏览器事件
        # 2. 生成基础工作流步骤
        # 3. 使用语音意图增强步骤
        # 4. 生成变量和条件
        return workflow
```

## 实现步骤

### 阶段一：基础语音集成
1. 实现浏览器扩展的语音录制功能
2. 创建 WebSocket 语音流服务
3. 集成语音转文字 API
4. 实现基础的时间戳关联

### 阶段二：意图理解
1. 开发语音意图分析器
2. 实现多模态事件关联算法
3. 创建参数提取和映射逻辑
4. 测试不同场景下的意图识别准确性

### 阶段三：工作流增强
1. 扩展现有工作流格式支持语音上下文
2. 实现增强型工作流生成器
3. 添加变量和条件提取功能
4. 集成到现有的执行引擎

### 阶段四：优化和集成
1. 性能优化和错误处理
2. 用户界面改进
3. 文档和示例更新
4. 端到端测试

## 技术栈扩展

### 新增依赖
```python
# Python 后端
openai-sdk
websockets==11.0.3
torch>=1.9.0  # 如果使用本地语音模型
transformers>=4.20.0  # 用于意图理解

# JavaScript 前端
@types/webrtc  # WebRTC 类型定义
```

### 配置文件更新
```yaml
# .env 新增配置
VOICE_LANGUAGE=zh-CN
VOICE_CONFIDENCE_THRESHOLD=0.7
CORRELATION_TIME_WINDOW=10
```

## 预期效果

使用这个扩展后，用户可以：

1. **边说边做**: "现在我要筛选最新的10条记录" + 点击筛选按钮
2. **语音变量**: "输入用户名{username}" + 在输入框中输入
3. **条件逻辑**: "如果没有数据就跳过这步" + 继续操作
4. **批量操作**: "选择所有这样的项目" + 点击复选框

生成的工作流将包含丰富的语义信息，执行时更加智能和灵活。