# 语音增强工作流测试

这个目录包含了语音增强工作流系统的所有测试文件。

## 目录结构

```
tests/
├── conftest.py                    # pytest 配置和全局 fixtures
├── README.md                      # 测试说明文档
├── intent_processor/              # 意图分析器测试
│   ├── __init__.py
│   └── test_intent_analyzer.py
├── correlator/                    # 事件关联器测试
│   ├── __init__.py
│   └── test_event_correlator.py
└── ... (其他组件测试目录)
```

## 运行测试

### 运行所有测试
```bash
cd workflows
python run_tests.py
```

### 运行特定组件的测试
```bash
# 运行意图分析器测试
python -m pytest tests/intent_processor/ -v

# 运行事件关联器测试  
python -m pytest tests/correlator/ -v
```

### 运行单个测试文件
```bash
python run_tests.py tests/intent_processor/test_intent_analyzer.py
```

### 运行特定测试方法
```bash
python -m pytest tests/intent_processor/test_intent_analyzer.py::TestIntentAnalyzer::test_filter_intent_recognition -v
```

## 测试覆盖的功能

### 意图分析器 (IntentAnalyzer)
- ✅ 基于规则的意图分类
- ✅ 变量提取
- ✅ 条件语句提取
- ✅ 参数提取
- ✅ 文本预处理
- ✅ 批量分析
- ✅ LLM 增强分析（Mock 测试）

### 事件关联器 (EventCorrelator)
- ✅ 时间窗口关联
- ✅ 语义关联
- ✅ 混合关联
- ✅ 会话隔离
- ✅ URL 匹配
- ✅ 置信度阈值
- ✅ 关联统计
- ✅ 边界情况处理

## 测试数据

测试使用的示例数据在 `conftest.py` 中定义，包括：
- 示例语音事件
- 示例浏览器事件
- 测试会话和URL

## 添加新测试

1. 在相应的组件目录下创建测试文件
2. 使用 `test_` 前缀命名测试文件和测试方法
3. 在 `run_tests.py` 中添加新的测试命令
4. 更新这个 README 文档

## 测试最佳实践

1. **独立性**: 每个测试应该独立运行，不依赖其他测试
2. **清晰性**: 测试名称应该清楚描述测试的功能
3. **覆盖性**: 测试应该覆盖正常情况、边界情况和异常情况
4. **可维护性**: 使用 fixtures 和辅助方法减少重复代码