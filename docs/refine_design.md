# 语音增强工作流技术方案

## 方案概述

基于现有的 Workflow-Use 架构，通过**时间戳关联**的方式将语音指令与浏览器事件进行匹配，然后在工作流生成阶段使用 LLM 进行语义增强，生成更智能、更灵活的工作流。

## 核心思路

在现有的 Workflow-Use 架构基础上，通过**时间戳关联**的方式将语音指令与浏览器事件进行匹配，然后在工作流生成阶段使用 LLM 进行语义增强，生成更智能、更灵活的工作流。

## 数据流设计

```
浏览器事件 (带时间戳) ┐
                    ├→ 事件关联器 → 增强型工作流生成器 → JSON工作流
语音转录 (带时间戳)   ┘
```

## 关键技术点

1. **时间窗口关联**: 使用可配置的时间窗口（如±5秒）将语音指令与最近的浏览器事件关联
2. **语义增强**: 利用 LLM 理解语音指令的意图，为对应的浏览器事件添加语义信息
3. **渐进式集成**: 不破坏现有架构，通过扩展现有组件实现功能

## 需要实现的组件

### 1. 多模态意图理解器
**文件**: `workflows/workflow_use/intent_processor/intent_analyzer.py`
**功能**:
- 分析语音文本，提取意图类型（筛选、选择、操作、条件等）
- 从语音中提取参数和变量
- 计算语音指令的置信度
- 提供意图分类和参数映射

### 2. 事件关联器
**文件**: `workflows/workflow_use/correlator/event_correlator.py`
**功能**:
- 基于时间戳将语音事件与浏览器事件进行关联
- 支持可配置的时间窗口
- 处理一对多、多对一的关联关系
- 生成关联度评分

### 3. 增强型工作流生成器
**文件**: `workflows/workflow_use/enhanced_generator/enhanced_workflow_generator.py`
**功能**:
- 接收关联后的多模态事件数据
- 使用 LLM 理解语音指令对浏览器事件的语义增强
- 生成包含语音上下文的工作流步骤
- 自动提取变量和生成条件逻辑

### 4. 语音数据存储管理器
**文件**: `workflows/workflow_use/storage/voice_storage.py`
**功能**:
- 管理语音事件的持久化存储
- 提供语音数据的查询和检索接口
- 支持语音数据与录制会话的关联
- 数据清理和归档功能

### 5. 多模态录制服务
**文件**: `workflows/workflow_use/recorder/multimodal_recorder.py`
**功能**:
- 扩展现有的 `RecordingService`
- 同时管理浏览器事件和语音事件的录制
- 提供统一的录制控制接口
- 支持语音开关的动态控制

### 6. 配置管理器
**文件**: `workflows/workflow_use/config/voice_config.py`
**功能**:
- 管理语音相关的配置参数
- 时间窗口、置信度阈值等参数配置
- 支持运行时配置更新
- 提供配置验证功能

### 7. CLI 命令扩展
**需要修改**: `workflows/cli.py`
**新增功能**:
- `create-enhanced-workflow`: 创建语音增强工作流
- `analyze-voice-events`: 分析语音事件数据
- `correlate-events`: 手动触发事件关联
- `export-voice-data`: 导出语音数据

### 8. 浏览器扩展增强
**需要修改**: `extension/src/entrypoints/background.ts`
**新增功能**:
- 语音事件与浏览器事件的统一管理
- 支持语音数据的批量导出
- 提供多模态录制状态管理

## 数据结构设计

### 语音事件结构
```typescript
interface VoiceEvent {
  id: string;
  text: string;
  timestamp: number;
  confidence: float;
  session_id: string;
  url: string;
}
```

### 关联事件结构
```typescript
interface CorrelatedEvent {
  browser_event: BrowserEvent;
  voice_events: VoiceEvent[];
  correlation_score: float;
  time_window: number;
}
```

### 增强工作流步骤
```typescript
interface EnhancedWorkflowStep extends WorkflowStep {
  voice_context?: {
    instructions: string[];
    intent_type: string;
    extracted_variables: Record<string, any>;
    conditions: string[];
  };
}
```

## 实现优先级

### 阶段一：基础关联（MVP）
1. `intent_analyzer.py` - 基础意图分析
2. `event_correlator.py` - 时间戳关联
3. `voice_storage.py` - 数据存储
4. CLI 命令扩展

### 阶段二：智能增强
1. `enhanced_workflow_generator.py` - LLM 增强生成
2. `voice_config.py` - 配置管理
3. `multimodal_recorder.py` - 录制服务增强

### 阶段三：优化集成
1. 浏览器扩展增强
2. 错误处理和容错机制
3. 性能优化和测试

## 方案优势

- **渐进式**: 不破坏现有架构
- **可扩展**: 每个组件职责单一，易于扩展
- **实用性**: 基于时间戳关联，技术实现相对简单
- **智能化**: 利用 LLM 进行语义理解和增强

## 技术栈扩展

### 新增依赖
```python
# Python 后端
websockets>=11.0.3
openai>=1.0.0
pydantic>=2.0.0
sqlalchemy>=2.0.0  # 用于语音数据存储
```

### 配置文件更新
```yaml
# .env 新增配置
VOICE_LANGUAGE=zh-CN
VOICE_CONFIDENCE_THRESHOLD=0.7
CORRELATION_TIME_WINDOW=5
VOICE_STORAGE_PATH=./tmp/voice_data
```

## 预期效果

使用这个扩展后，用户可以：

1. **边说边做**: "现在我要筛选最新的10条记录" + 点击筛选按钮
2. **语音变量**: "输入用户名{username}" + 在输入框中输入
3. **条件逻辑**: "如果没有数据就跳过这步" + 继续操作
4. **批量操作**: "选择所有这样的项目" + 点击复选框

生成的工作流将包含丰富的语义信息，执行时更加智能和灵活。