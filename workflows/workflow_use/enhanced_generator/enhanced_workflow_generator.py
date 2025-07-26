"""
增强型工作流生成器
使用 LLM 将关联后的多模态事件数据转换为智能工作流
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ..correlator.event_correlator import CorrelationResult, BrowserEvent, VoiceEvent
from ..intent_processor.intent_analyzer import IntentAnalyzer, IntentType

logger = logging.getLogger(__name__)


@dataclass
class EnhancedWorkflowStep:
    """增强的工作流步骤"""
    id: str
    type: str  # click, input, navigation, condition, etc.
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    xpath: Optional[str] = None
    css_selector: Optional[str] = None
    
    # 语音增强字段
    voice_context: Optional[Dict[str, Any]] = None
    extracted_variables: Optional[Dict[str, str]] = None
    conditions: Optional[List[str]] = None
    enhanced: bool = False


class EnhancedWorkflowGenerator:
    """增强型工作流生成器"""
    
    def __init__(self, llm: BaseChatModel):
        """
        初始化生成器
        
        Args:
            llm: LangChain BaseChatModel 实例
        """
        if llm is None:
            raise ValueError('A BaseChatModel instance must be provided.')
        
        self.llm = llm
        self.intent_analyzer = IntentAnalyzer()
        
    async def generate_enhanced_workflow(
        self, 
        correlations: List[CorrelationResult],
        user_goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成增强型工作流
        
        Args:
            correlations: 事件关联结果列表
            user_goal: 用户目标描述
            
        Returns:
            增强的工作流定义
        """
        logger.info(f"Generating enhanced workflow from {len(correlations)} correlations")
        
        # 1. 生成基础工作流步骤
        base_steps = self._generate_base_steps(correlations)
        
        # 2. 使用语音增强步骤
        enhanced_steps = []
        for step in base_steps:
            enhanced_step = await self._enhance_step_with_voice(step, correlations)
            enhanced_steps.append(enhanced_step)
        
        # 3. 提取全局变量和条件
        global_variables = self._extract_workflow_variables(enhanced_steps)
        global_conditions = self._extract_global_conditions(enhanced_steps)
        
        # 4. 生成最终工作流
        workflow = {
            "name": "Enhanced Voice Workflow",
            "description": user_goal or "Voice-enhanced browser automation workflow",
            "version": "1.0",
            "variables": global_variables,
            "conditions": global_conditions,
            "steps": [step.__dict__ for step in enhanced_steps],
            "metadata": {
                "enhanced": True,
                "voice_events_count": sum(len(c.voice_events) for c in correlations),
                "browser_events_count": len(correlations)
            }
        }
        
        return workflow
    
    def _generate_base_steps(self, correlations: List[CorrelationResult]) -> List[EnhancedWorkflowStep]:
        """从关联结果生成基础工作流步骤"""
        steps = []
        
        for i, correlation in enumerate(correlations):
            browser_event = correlation.browser_event
            
            # 基于浏览器事件类型生成基础步骤
            step = EnhancedWorkflowStep(
                id=f"step_{i+1}",
                type=browser_event.type,
                action=self._get_action_from_event_type(browser_event.type),
                target=browser_event.element_tag,
                value=browser_event.value,
                xpath=browser_event.xpath,
                css_selector=browser_event.css_selector
            )
            
            steps.append(step)
        
        return steps
    
    def _get_action_from_event_type(self, event_type: str) -> str:
        """根据事件类型获取动作描述"""
        action_map = {
            'click': 'click_element',
            'input': 'input_text',
            'navigation': 'navigate_to',
            'scroll': 'scroll_page',
            'select': 'select_option',
            'hover': 'hover_element'
        }
        return action_map.get(event_type, 'perform_action')
    
    async def _enhance_step_with_voice(
        self, 
        step: EnhancedWorkflowStep, 
        correlations: List[CorrelationResult]
    ) -> EnhancedWorkflowStep:
        """使用语音指令增强工作流步骤"""
        
        # 找到对应的关联结果
        correlation = self._find_correlation_for_step(step, correlations)
        if not correlation or not correlation.voice_events:
            return step
        
        # 分析语音意图
        voice_texts = [ve.text for ve in correlation.voice_events]
        voice_analysis = []
        
        for voice_text in voice_texts:
            analysis = self.intent_analyzer.analyze_intent(voice_text)
            voice_analysis.append(analysis)
        
        # 使用 LLM 进行语义增强
        enhanced_step = await self._llm_enhance_step(step, voice_analysis, voice_texts)
        
        return enhanced_step
    
    def _find_correlation_for_step(
        self, 
        step: EnhancedWorkflowStep, 
        correlations: List[CorrelationResult]
    ) -> Optional[CorrelationResult]:
        """为步骤找到对应的关联结果"""
        step_index = int(step.id.split('_')[1]) - 1
        if 0 <= step_index < len(correlations):
            return correlations[step_index]
        return None
    
    async def _llm_enhance_step(
        self, 
        step: EnhancedWorkflowStep, 
        voice_analysis: List[Any],
        voice_texts: List[str]
    ) -> EnhancedWorkflowStep:
        """使用 LLM 增强步骤"""
        
        system_prompt = """你是一个工作流增强专家。根据浏览器操作和对应的语音指令，生成更智能的工作流步骤。

请分析语音指令中的：
1. 条件逻辑（如果...则...）
2. 变量提取（用户名、密码等参数化内容）
3. 操作意图（点击、输入、导航等）
4. 错误处理提示

返回JSON格式的增强信息：
{
    "enhanced_action": "增强后的动作描述",
    "conditions": ["条件1", "条件2"],
    "variables": {"var_name": "var_value"},
    "error_handling": "错误处理逻辑",
    "smart_selectors": ["智能选择器1", "智能选择器2"]
}"""
        
        user_prompt = f"""
原始浏览器操作：
- 类型: {step.type}
- 动作: {step.action}
- 目标: {step.target}
- XPath: {step.xpath}

对应的语音指令：
{chr(10).join(f"- {text}" for text in voice_texts)}

语音意图分析：
{chr(10).join(f"- 意图: {analysis.intent_type.value}, 置信度: {analysis.confidence}" for analysis in voice_analysis)}

请生成增强的工作流步骤信息。
"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            enhancement_data = json.loads(response.content)
            
            # 应用增强信息
            step.action = enhancement_data.get('enhanced_action', step.action)
            step.conditions = enhancement_data.get('conditions', [])
            step.voice_context = {
                'instructions': voice_texts,
                'intent_types': [analysis.intent_type.value for analysis in voice_analysis],
                'error_handling': enhancement_data.get('error_handling'),
                'smart_selectors': enhancement_data.get('smart_selectors', [])
            }
            step.extracted_variables = enhancement_data.get('variables', {})
            step.enhanced = True
            
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}, using basic enhancement")
            # 降级到基础增强
            step = self._basic_enhance_step(step, voice_analysis, voice_texts)
        
        return step
    
    def _basic_enhance_step(
        self, 
        step: EnhancedWorkflowStep, 
        voice_analysis: List[Any],
        voice_texts: List[str]
    ) -> EnhancedWorkflowStep:
        """基础增强（不依赖LLM）"""
        
        # 提取变量
        variables = {}
        conditions = []
        
        for analysis in voice_analysis:
            variables.update(analysis.extracted_variables)
            conditions.extend(analysis.conditions)
        
        step.voice_context = {
            'instructions': voice_texts,
            'intent_types': [analysis.intent_type.value for analysis in voice_analysis]
        }
        step.extracted_variables = variables
        step.conditions = conditions
        step.enhanced = True
        
        return step
    
    def _extract_workflow_variables(self, steps: List[EnhancedWorkflowStep]) -> Dict[str, Any]:
        """提取工作流全局变量"""
        global_variables = {}
        
        for step in steps:
            if step.extracted_variables:
                for var_name, var_value in step.extracted_variables.items():
                    if var_name not in global_variables:
                        global_variables[var_name] = {
                            'type': 'string',
                            'default': var_value,
                            'description': f'Extracted from voice: {var_value}'
                        }
        
        return global_variables
    
    def _extract_global_conditions(self, steps: List[EnhancedWorkflowStep]) -> List[Dict[str, Any]]:
        """提取全局条件逻辑"""
        global_conditions = []
        
        for step in steps:
            if step.conditions:
                for condition in step.conditions:
                    global_conditions.append({
                        'condition': condition,
                        'step_id': step.id,
                        'type': 'voice_extracted'
                    })
        
        return global_conditions