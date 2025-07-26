"""
增强型工作流生成器测试
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock

from workflow_use.enhanced_generator.enhanced_workflow_generator import (
    EnhancedWorkflowGenerator,
    EnhancedWorkflowStep
)
from workflow_use.correlator.event_correlator import (
    CorrelationResult,
    BrowserEvent,
    VoiceEvent,
    CorrelationMethod
)
from workflow_use.intent_processor.intent_analyzer import IntentType, IntentAnalysisResult


class TestEnhancedWorkflowGenerator:
    """增强型工作流生成器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        # Mock LLM
        self.mock_llm = Mock()
        self.mock_llm.ainvoke = AsyncMock()
        
        self.generator = EnhancedWorkflowGenerator(self.mock_llm)
    
    def create_browser_event(self, event_type: str, timestamp: float) -> BrowserEvent:
        """创建测试用浏览器事件"""
        return BrowserEvent(
            id=f"browser_{event_type}_{timestamp}",
            type=event_type,
            timestamp=1000.0 + timestamp,
            url="https://example.com",
            session_id="test_session",
            xpath=f"//button[@id='{event_type}']",
            css_selector=f"#{event_type}",
            element_tag="button",
            value="test_value" if event_type == "input" else None
        )
    
    def create_voice_event(self, text: str, timestamp: float) -> VoiceEvent:
        """创建测试用语音事件"""
        return VoiceEvent(
            id=f"voice_{timestamp}",
            text=text,
            timestamp=1000.0 + timestamp,
            confidence=0.9,
            session_id="test_session",
            url="https://example.com"
        )
    
    def create_correlation(self, browser_event: BrowserEvent, voice_events: list) -> CorrelationResult:
        """创建测试用关联结果"""
        return CorrelationResult(
            browser_event=browser_event,
            voice_events=voice_events,
            correlation_score=0.8,
            time_window=5.0,
            correlation_method=CorrelationMethod.TIME_WINDOW,
            metadata={}
        )
    
    def test_init_with_valid_llm(self):
        """测试使用有效LLM初始化"""
        generator = EnhancedWorkflowGenerator(self.mock_llm)
        assert generator.llm == self.mock_llm
        assert generator.intent_analyzer is not None
    
    def test_init_with_none_llm(self):
        """测试使用None LLM初始化应该抛出异常"""
        with pytest.raises(ValueError, match="A BaseChatModel instance must be provided"):
            EnhancedWorkflowGenerator(None)
    
    def test_generate_base_steps(self):
        """测试生成基础工作流步骤"""
        browser_events = [
            self.create_browser_event("click", 0.0),
            self.create_browser_event("input", 5.0)
        ]
        
        correlations = [
            self.create_correlation(browser_events[0], []),
            self.create_correlation(browser_events[1], [])
        ]
        
        steps = self.generator._generate_base_steps(correlations)
        
        assert len(steps) == 2
        assert steps[0].id == "step_1"
        assert steps[0].type == "click"
        assert steps[0].action == "click_element"
        assert steps[1].id == "step_2"
        assert steps[1].type == "input"
        assert steps[1].action == "input_text"
    
    def test_get_action_from_event_type(self):
        """测试从事件类型获取动作"""
        assert self.generator._get_action_from_event_type("click") == "click_element"
        assert self.generator._get_action_from_event_type("input") == "input_text"
        assert self.generator._get_action_from_event_type("navigation") == "navigate_to"
        assert self.generator._get_action_from_event_type("unknown") == "perform_action"
    
    def test_find_correlation_for_step(self):
        """测试为步骤找到对应的关联结果"""
        correlations = [
            self.create_correlation(self.create_browser_event("click", 0.0), []),
            self.create_correlation(self.create_browser_event("input", 5.0), [])
        ]
        
        step1 = EnhancedWorkflowStep(id="step_1", type="click", action="click_element")
        step2 = EnhancedWorkflowStep(id="step_2", type="input", action="input_text")
        
        correlation1 = self.generator._find_correlation_for_step(step1, correlations)
        correlation2 = self.generator._find_correlation_for_step(step2, correlations)
        
        assert correlation1 == correlations[0]
        assert correlation2 == correlations[1]
    
    def test_basic_enhance_step(self):
        """测试基础步骤增强"""
        step = EnhancedWorkflowStep(id="step_1", type="click", action="click_element")
        
        # Mock 语音分析结果
        voice_analysis = [
            IntentAnalysisResult(
                intent_type=IntentType.CLICK,
                confidence=0.9,
                extracted_variables={"button_name": "提交"},
                conditions=["如果表单有效"],
                parameters={},
                raw_text="如果表单有效就点击提交按钮",
                processed_text="如果表单有效就点击提交按钮"
            )
        ]
        
        voice_texts = ["如果表单有效就点击提交按钮"]
        
        enhanced_step = self.generator._basic_enhance_step(step, voice_analysis, voice_texts)
        
        assert enhanced_step.enhanced is True
        assert enhanced_step.extracted_variables == {"button_name": "提交"}
        assert enhanced_step.conditions == ["如果表单有效"]
        assert enhanced_step.voice_context['instructions'] == voice_texts
        assert enhanced_step.voice_context['intent_types'] == [IntentType.CLICK.value]
    
    @pytest.mark.asyncio
    async def test_llm_enhance_step_success(self):
        """测试LLM增强步骤成功"""
        step = EnhancedWorkflowStep(id="step_1", type="click", action="click_element")
        
        # Mock LLM 响应
        mock_response = Mock()
        mock_response.content = json.dumps({
            "enhanced_action": "智能点击提交按钮",
            "conditions": ["表单验证通过"],
            "variables": {"form_data": "用户输入"},
            "error_handling": "如果按钮不可用则等待",
            "smart_selectors": ["[data-testid='submit']", "button[type='submit']"]
        })
        self.mock_llm.ainvoke.return_value = mock_response
        
        voice_analysis = [
            IntentAnalysisResult(
                intent_type=IntentType.CLICK,
                confidence=0.9,
                extracted_variables={},
                conditions=[],
                parameters={},
                raw_text="点击提交按钮",
                processed_text="点击提交按钮"
            )
        ]
        
        enhanced_step = await self.generator._llm_enhance_step(
            step, voice_analysis, ["点击提交按钮"]
        )
        
        assert enhanced_step.enhanced is True
        assert enhanced_step.action == "智能点击提交按钮"
        assert enhanced_step.conditions == ["表单验证通过"]
        assert enhanced_step.extracted_variables == {"form_data": "用户输入"}
        assert enhanced_step.voice_context['error_handling'] == "如果按钮不可用则等待"
    
    @pytest.mark.asyncio
    async def test_llm_enhance_step_fallback(self):
        """测试LLM增强失败时的降级处理"""
        step = EnhancedWorkflowStep(id="step_1", type="click", action="click_element")
        
        # Mock LLM 抛出异常
        self.mock_llm.ainvoke.side_effect = Exception("LLM error")
        
        voice_analysis = [
            IntentAnalysisResult(
                intent_type=IntentType.CLICK,
                confidence=0.9,
                extracted_variables={"button": "提交"},
                conditions=["表单有效"],
                parameters={},
                raw_text="点击提交按钮",
                processed_text="点击提交按钮"
            )
        ]
        
        enhanced_step = await self.generator._llm_enhance_step(
            step, voice_analysis, ["点击提交按钮"]
        )
        
        # 应该降级到基础增强
        assert enhanced_step.enhanced is True
        assert enhanced_step.extracted_variables == {"button": "提交"}
        assert enhanced_step.conditions == ["表单有效"]
    
    def test_extract_workflow_variables(self):
        """测试提取工作流变量"""
        steps = [
            EnhancedWorkflowStep(
                id="step_1",
                type="input",
                action="input_text",
                extracted_variables={"username": "admin", "password": "123456"}
            ),
            EnhancedWorkflowStep(
                id="step_2",
                type="click",
                action="click_element",
                extracted_variables={"button": "提交"}
            )
        ]
        
        variables = self.generator._extract_workflow_variables(steps)
        
        assert len(variables) == 3
        assert "username" in variables
        assert "password" in variables
        assert "button" in variables
        assert variables["username"]["default"] == "admin"
        assert variables["password"]["type"] == "string"
    
    def test_extract_global_conditions(self):
        """测试提取全局条件"""
        steps = [
            EnhancedWorkflowStep(
                id="step_1",
                type="click",
                action="click_element",
                conditions=["如果按钮可用", "表单验证通过"]
            ),
            EnhancedWorkflowStep(
                id="step_2",
                type="input",
                action="input_text",
                conditions=["如果字段为空"]
            )
        ]
        
        conditions = self.generator._extract_global_conditions(steps)
        
        assert len(conditions) == 3
        assert conditions[0]["condition"] == "如果按钮可用"
        assert conditions[0]["step_id"] == "step_1"
        assert conditions[1]["condition"] == "表单验证通过"
        assert conditions[2]["step_id"] == "step_2"
    
    @pytest.mark.asyncio
    async def test_generate_enhanced_workflow_complete(self):
        """测试完整的增强工作流生成"""
        # 准备测试数据
        browser_event = self.create_browser_event("click", 0.0)
        voice_event = self.create_voice_event("点击提交按钮", 0.5)
        correlation = self.create_correlation(browser_event, [voice_event])
        
        # Mock LLM 响应
        mock_response = Mock()
        mock_response.content = json.dumps({
            "enhanced_action": "智能提交表单",
            "conditions": ["表单验证通过"],
            "variables": {"form_type": "登录表单"},
            "error_handling": "等待按钮可用",
            "smart_selectors": ["[type='submit']"]
        })
        self.mock_llm.ainvoke.return_value = mock_response
        
        # 生成工作流
        workflow = await self.generator.generate_enhanced_workflow(
            [correlation], 
            "用户登录流程"
        )
        
        # 验证结果
        assert workflow["name"] == "Enhanced Voice Workflow"
        assert workflow["description"] == "用户登录流程"
        assert workflow["metadata"]["enhanced"] is True
        assert workflow["metadata"]["voice_events_count"] == 1
        assert workflow["metadata"]["browser_events_count"] == 1
        
        assert len(workflow["steps"]) == 1
        step = workflow["steps"][0]
        assert step["enhanced"] is True
        assert step["action"] == "智能提交表单"
        
        assert "form_type" in workflow["variables"]
        assert len(workflow["conditions"]) == 1