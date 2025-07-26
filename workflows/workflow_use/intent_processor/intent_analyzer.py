import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel


class IntentType(Enum):
    """语音指令意图类型"""
    FILTER = "filter"  # 筛选操作
    SELECT = "select"  # 选择操作
    INPUT = "input"    # 输入操作
    CLICK = "click"    # 点击操作
    NAVIGATE = "navigate"  # 导航操作
    CONDITION = "condition"  # 条件判断
    VARIABLE = "variable"   # 变量定义
    DESCRIPTION = "description"  # 描述说明
    UNKNOWN = "unknown"  # 未知意图


@dataclass
class IntentAnalysisResult:
    """意图分析结果"""
    intent_type: IntentType
    confidence: float
    extracted_variables: Dict[str, str]
    conditions: List[str]
    parameters: Dict[str, any]
    raw_text: str
    processed_text: str


class IntentAnalyzer:
    """多模态意图理解器"""
    
    def __init__(self, llm: Optional[BaseChatModel] = None):
        self.llm = llm
        self._init_patterns()
    
    def _init_patterns(self):
        """初始化正则表达式模式"""
        self.patterns = {
            IntentType.CONDITION: [
                r'如果.*就|假如.*则|当.*时.*就|要是.*就',
                r'当.*时|当.*的时候',
                r'没有.*就|为空.*就|不存在.*就',
                r'否则|不然|要不然'
            ],
            IntentType.DESCRIPTION: [
                r'^这是(?!.*输入)',
                r'^这里是',
                r'^现在是',
                r'^这里用来(?!.*输入)',
                r'^用来|^用于|^为了',
                r'^目的是|^作用是'
            ],
            IntentType.NAVIGATE: [
                r'跳转到|转到|打开.*页面|访问.*页面',
                r'回到|返回到|切换到',
                r'进入.*页面|前往.*页面'
            ],
            IntentType.FILTER: [
                r'筛选|过滤|查找|搜索|找到.*的',
                r'显示.*条|最新的.*条|前.*个',
                r'只要|只显示|仅显示'
            ],
            IntentType.SELECT: [
                r'选择|选中|勾选|点选',
                r'全选|选择所有|选择全部',
                r'取消选择|不选'
            ],
            IntentType.INPUT: [
                r'输入(?!.*页面)',
                r'填写|填入|写入',
                r'设置.*为|改为|修改.*为',
                r'修改|更改|变更'
            ],
            IntentType.CLICK: [
                r'点击(?!.*页面)',
                r'按(?!.*页面)|按下',
                r'提交|确认|保存|取消',
                r'下一步|上一步(?!.*页面)'
            ],
            IntentType.VARIABLE: [
                r'\{.*\}|变量.*|参数.*',
                r'这里用.*代替|用.*替换',
                r'动态.*|可变.*'
            ]
        }
    
    def analyze_intent(self, voice_text: str) -> IntentAnalysisResult:
        """分析语音文本的意图"""
        # 预处理文本
        processed_text = self._preprocess_text(voice_text)
        
        # 基于规则的意图识别
        intent_type, rule_confidence = self._rule_based_classification(processed_text)
        
        # 提取变量
        variables = self._extract_variables(processed_text)
        
        # 提取条件
        conditions = self._extract_conditions(processed_text)
        
        # 提取参数
        parameters = self._extract_parameters(processed_text, intent_type)
        
        # 如果有LLM，进行语义增强
        if self.llm:
            llm_result = self._llm_enhanced_analysis(processed_text, intent_type)
            confidence = max(rule_confidence, llm_result.get('confidence', 0))
            intent_type = llm_result.get('intent_type', intent_type)
            variables.update(llm_result.get('variables', {}))
            conditions.extend(llm_result.get('conditions', []))
            parameters.update(llm_result.get('parameters', {}))
        else:
            confidence = rule_confidence
        
        return IntentAnalysisResult(
            intent_type=intent_type,
            confidence=confidence,
            extracted_variables=variables,
            conditions=conditions,
            parameters=parameters,
            raw_text=voice_text,
            processed_text=processed_text
        )
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 去除多余空格和标点
        text = re.sub(r'\s+', ' ', text.strip())
        # 统一标点符号
        text = re.sub(r'[，。！？；：]', ',', text)
        return text.lower()
    
    def _rule_based_classification(self, text: str) -> Tuple[IntentType, float]:
        """基于规则的意图分类"""
        scores = {}
        
        # 按优先级顺序检查意图类型
        priority_order = [
            IntentType.CONDITION,
            IntentType.DESCRIPTION, 
            IntentType.NAVIGATE,
            IntentType.FILTER,
            IntentType.SELECT,
            IntentType.INPUT,
            IntentType.CLICK,
            IntentType.VARIABLE
        ]
        
        for intent_type in priority_order:
            patterns = self.patterns.get(intent_type, [])
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
        
            if score > 0:
                # 根据匹配数量和文本长度计算置信度
                confidence = min(score / len(text.split()) * 2, 1.0)
                scores[intent_type] = confidence
    
        if not scores:
            return IntentType.UNKNOWN, 0.0
    
        # 返回得分最高的意图类型
        best_intent = max(scores.items(), key=lambda x: x[1])
        return best_intent[0], best_intent[1]
    
    def _extract_variables(self, text: str) -> Dict[str, str]:
        """提取变量"""
        variables = {}
        
        # 提取花括号变量 {variable_name}
        brace_vars = re.findall(r'\{([^}]+)\}', text)
        for var in brace_vars:
            variables[var] = f"${{{var}}}"
        
        # 提取常见变量模式
        var_patterns = {
            'username': r'用户名|账号|账户名',
            'password': r'密码|口令',
            'email': r'邮箱|邮件|email',
            'phone': r'电话|手机|联系方式',
            'name': r'姓名|名字|名称',
            'count': r'(\d+)条|(\d+)个|(\d+)项'
        }
        
        for var_name, pattern in var_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                variables[var_name] = f"${{{var_name}}}"
        
        return variables
    
    def _extract_conditions(self, text: str) -> List[str]:
        """提取条件语句"""
        conditions = []
        
        condition_patterns = [
            r'如果(.+?)就(.+?)(?:,|$)',
            r'当(.+?)时(.+?)(?:,|$)',
            r'假如(.+?)则(.+?)(?:,|$)',
            r'没有.*就(.+?)(?:,|$)',
            r'为空就(.+?)(?:,|$)'
        ]
        
        for pattern in condition_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    condition = f"if {match[0].strip()} then {match[1].strip()}"
                else:
                    condition = match.strip()
                conditions.append(condition)
        
        return conditions
    
    def _extract_parameters(self, text: str, intent_type: IntentType) -> Dict[str, any]:
        """根据意图类型提取参数"""
        parameters = {}
        
        if intent_type == IntentType.FILTER:
            # 提取数量参数
            count_match = re.search(r'(\d+)条|(\d+)个|(\d+)项', text)
            if count_match:
                count = next(g for g in count_match.groups() if g)
                parameters['count'] = int(count)
            
            # 提取时间参数
            time_match = re.search(r'最新|最近|今天|昨天|本周|本月', text)
            if time_match:
                parameters['time_filter'] = time_match.group()
        
        elif intent_type == IntentType.INPUT:
            # 提取输入值
            value_patterns = [
                r'输入(.+?)(?:,|$)',
                r'填写(.+?)(?:,|$)',
                r'设置为(.+?)(?:,|$)'
            ]
            for pattern in value_patterns:
                match = re.search(pattern, text)
                if match:
                    parameters['value'] = match.group(1).strip()
                    break
        
        elif intent_type == IntentType.SELECT:
            # 提取选择范围
            if '全选' in text or '所有' in text:
                parameters['select_all'] = True
            elif '取消' in text:
                parameters['deselect'] = True
        
        return parameters
    
    def _llm_enhanced_analysis(self, text: str, initial_intent: IntentType) -> Dict:
        """使用LLM进行语义增强分析"""
        if not self.llm:
            return {}
        
        prompt = PromptTemplate.from_template("""
        分析以下语音指令的意图和参数：

        语音文本: {text}
        初步意图: {initial_intent}

        请提供：
        1. 最终意图类型 (filter/select/input/click/navigate/condition/variable/description/unknown)
        2. 置信度 (0-1)
        3. 提取的变量 (JSON格式)
        4. 条件语句 (数组格式)
        5. 参数 (JSON格式)

        以JSON格式返回结果。
        """)
        
        try:
            response = self.llm.invoke(prompt.format(
                text=text,
                initial_intent=initial_intent.value
            ))
            
            # 这里需要解析LLM的响应，简化实现
            return {
                'intent_type': initial_intent,
                'confidence': 0.8,
                'variables': {},
                'conditions': [],
                'parameters': {}
            }
        except Exception as e:
            print(f"LLM分析失败: {e}")
            return {}
    
    def batch_analyze(self, voice_texts: List[str]) -> List[IntentAnalysisResult]:
        """批量分析语音文本"""
        return [self.analyze_intent(text) for text in voice_texts]
