import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class CorrelationMethod(Enum):
    """关联方法"""
    TIME_WINDOW = "time_window"  # 时间窗口关联
    SEMANTIC = "semantic"        # 语义关联
    HYBRID = "hybrid"           # 混合关联


@dataclass
class VoiceEvent:
    """语音事件"""
    id: str
    text: str
    timestamp: float
    confidence: float
    session_id: str
    url: str
    intent_type: Optional[str] = None
    variables: Optional[Dict[str, str]] = None


@dataclass
class BrowserEvent:
    """浏览器事件"""
    id: str
    type: str  # click, input, navigation, scroll, etc.
    timestamp: float
    url: str
    session_id: str
    xpath: Optional[str] = None
    css_selector: Optional[str] = None
    element_tag: Optional[str] = None
    value: Optional[str] = None
    tab_id: Optional[str] = None


@dataclass
class CorrelationResult:
    """关联结果"""
    browser_event: BrowserEvent
    voice_events: List[VoiceEvent]
    correlation_score: float
    time_window: float
    correlation_method: CorrelationMethod
    metadata: Dict[str, any]


class EventCorrelator:
    """事件关联器"""
    
    def __init__(self, 
                 time_window: float = 5.0,
                 min_confidence: float = 0.3,
                 correlation_method: CorrelationMethod = CorrelationMethod.TIME_WINDOW):
        """
        初始化事件关联器
        
        Args:
            time_window: 时间窗口大小（秒）
            min_confidence: 最小置信度阈值
            correlation_method: 关联方法
        """
        self.time_window = time_window
        self.min_confidence = min_confidence
        self.correlation_method = correlation_method
    
    def correlate_events(self, 
                        browser_events: List[BrowserEvent],
                        voice_events: List[VoiceEvent]) -> List[CorrelationResult]:
        """
        关联浏览器事件和语音事件
        
        Args:
            browser_events: 浏览器事件列表
            voice_events: 语音事件列表
            
        Returns:
            关联结果列表
        """
        correlations = []
        
        # 按时间戳排序
        browser_events = sorted(browser_events, key=lambda x: x.timestamp)
        voice_events = sorted(voice_events, key=lambda x: x.timestamp)
        
        for browser_event in browser_events:
            # 找到时间窗口内的语音事件
            candidate_voice_events = self._find_candidate_voice_events(
                browser_event, voice_events
            )
            
            if not candidate_voice_events:
                # 没有候选语音事件，创建空关联
                correlations.append(CorrelationResult(
                    browser_event=browser_event,
                    voice_events=[],
                    correlation_score=0.0,
                    time_window=self.time_window,
                    correlation_method=self.correlation_method,
                    metadata={}
                ))
                continue
            
            # 计算关联度
            best_correlation = self._calculate_best_correlation(
                browser_event, candidate_voice_events
            )
            
            if best_correlation.correlation_score >= self.min_confidence:
                correlations.append(best_correlation)
            else:
                # 关联度不够，创建空关联
                correlations.append(CorrelationResult(
                    browser_event=browser_event,
                    voice_events=[],
                    correlation_score=0.0,
                    time_window=self.time_window,
                    correlation_method=self.correlation_method,
                    metadata={'low_confidence_voices': len(candidate_voice_events)}
                ))
        
        return correlations
    
    def _find_candidate_voice_events(self, 
                                   browser_event: BrowserEvent,
                                   voice_events: List[VoiceEvent]) -> List[VoiceEvent]:
        """找到时间窗口内的候选语音事件"""
        candidates = []
        browser_time = browser_event.timestamp
        
        for voice_event in voice_events:
            time_diff = abs(voice_event.timestamp - browser_time)
            
            # 在时间窗口内且URL匹配
            if (time_diff <= self.time_window and 
                voice_event.url == browser_event.url and
                voice_event.session_id == browser_event.session_id):
                candidates.append(voice_event)
        
        return candidates
    
    def _calculate_best_correlation(self, 
                                  browser_event: BrowserEvent,
                                  voice_events: List[VoiceEvent]) -> CorrelationResult:
        """计算最佳关联"""
        if self.correlation_method == CorrelationMethod.TIME_WINDOW:
            return self._time_window_correlation(browser_event, voice_events)
        elif self.correlation_method == CorrelationMethod.SEMANTIC:
            return self._semantic_correlation(browser_event, voice_events)
        else:  # HYBRID
            return self._hybrid_correlation(browser_event, voice_events)
    
    def _time_window_correlation(self, 
                               browser_event: BrowserEvent,
                               voice_events: List[VoiceEvent]) -> CorrelationResult:
        """基于时间窗口的关联"""
        if not voice_events:
            return CorrelationResult(
                browser_event=browser_event,
                voice_events=[],
                correlation_score=0.0,
                time_window=self.time_window,
                correlation_method=CorrelationMethod.TIME_WINDOW,
                metadata={}
            )
        
        # 计算时间相关性
        browser_time = browser_event.timestamp
        total_score = 0.0
        valid_events = []
        
        for voice_event in voice_events:
            time_diff = abs(voice_event.timestamp - browser_time)
            
            # 时间越近，分数越高
            time_score = max(0, 1 - (time_diff / self.time_window))
            
            # 考虑语音识别置信度
            confidence_score = voice_event.confidence
            
            # 综合分数
            event_score = time_score * confidence_score
            
            if event_score > 0:
                total_score += event_score
                valid_events.append(voice_event)
        
        # 归一化分数
        if valid_events:
            avg_score = total_score / len(valid_events)
        else:
            avg_score = 0.0
        
        return CorrelationResult(
            browser_event=browser_event,
            voice_events=valid_events,
            correlation_score=avg_score,
            time_window=self.time_window,
            correlation_method=CorrelationMethod.TIME_WINDOW,
            metadata={
                'time_scores': [abs(ve.timestamp - browser_time) for ve in valid_events],
                'confidence_scores': [ve.confidence for ve in valid_events]
            }
        )
    
    def _semantic_correlation(self, 
                            browser_event: BrowserEvent,
                            voice_events: List[VoiceEvent]) -> CorrelationResult:
        """基于语义的关联"""
        # 简化的语义关联实现
        semantic_scores = []
        
        for voice_event in voice_events:
            score = self._calculate_semantic_similarity(browser_event, voice_event)
            semantic_scores.append(score)
        
        if semantic_scores:
            avg_score = sum(semantic_scores) / len(semantic_scores)
        else:
            avg_score = 0.0
        
        return CorrelationResult(
            browser_event=browser_event,
            voice_events=voice_events,
            correlation_score=avg_score,
            time_window=self.time_window,
            correlation_method=CorrelationMethod.SEMANTIC,
            metadata={'semantic_scores': semantic_scores}
        )
    
    def _hybrid_correlation(self, 
                          browser_event: BrowserEvent,
                          voice_events: List[VoiceEvent]) -> CorrelationResult:
        """混合关联方法"""
        time_result = self._time_window_correlation(browser_event, voice_events)
        semantic_result = self._semantic_correlation(browser_event, voice_events)
        
        # 加权平均
        time_weight = 0.7
        semantic_weight = 0.3
        
        hybrid_score = (time_result.correlation_score * time_weight + 
                       semantic_result.correlation_score * semantic_weight)
        
        return CorrelationResult(
            browser_event=browser_event,
            voice_events=voice_events,
            correlation_score=hybrid_score,
            time_window=self.time_window,
            correlation_method=CorrelationMethod.HYBRID,
            metadata={
                'time_score': time_result.correlation_score,
                'semantic_score': semantic_result.correlation_score,
                'weights': {'time': time_weight, 'semantic': semantic_weight}
            }
        )
    
    def _calculate_semantic_similarity(self, 
                                     browser_event: BrowserEvent,
                                     voice_event: VoiceEvent) -> float:
        """计算语义相似度"""
        # 简化的语义相似度计算
        browser_type = browser_event.type.lower()
        voice_text = voice_event.text.lower()
        
        # 基于关键词匹配的简单语义相似度
        type_keywords = {
            'click': ['点击', '按', '点', '选择', '确认', '提交'],
            'input': ['输入', '填写', '填入', '写入', '设置'],
            'navigation': ['跳转', '打开', '访问', '转到', '页面'],
            'scroll': ['滚动', '翻页', '下拉', '上拉'],
            'select': ['选择', '选中', '勾选', '下拉']
        }
        
        keywords = type_keywords.get(browser_type, [])
        matches = sum(1 for keyword in keywords if keyword in voice_text)
        
        if keywords:
            similarity = matches / len(keywords)
        else:
            similarity = 0.0
        
        # 考虑元素信息
        if browser_event.element_tag:
            tag_keywords = {
                'button': ['按钮', '点击', '确认', '提交'],
                'input': ['输入', '填写', '输入框'],
                'select': ['选择', '下拉', '选项'],
                'a': ['链接', '跳转', '打开']
            }
            
            tag = browser_event.element_tag.lower()
            tag_words = tag_keywords.get(tag, [])
            tag_matches = sum(1 for word in tag_words if word in voice_text)
            
            if tag_words:
                tag_similarity = tag_matches / len(tag_words)
                similarity = max(similarity, tag_similarity)
        
        return min(similarity, 1.0)
    
    def get_correlation_statistics(self, 
                                 correlations: List[CorrelationResult]) -> Dict[str, any]:
        """获取关联统计信息"""
        if not correlations:
            return {}
        
        total_events = len(correlations)
        correlated_events = sum(1 for c in correlations if c.voice_events)
        correlation_rate = correlated_events / total_events
        
        scores = [c.correlation_score for c in correlations if c.correlation_score > 0]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        voice_event_counts = [len(c.voice_events) for c in correlations]
        avg_voice_events = sum(voice_event_counts) / len(voice_event_counts)
        
        return {
            'total_browser_events': total_events,
            'correlated_events': correlated_events,
            'correlation_rate': correlation_rate,
            'average_correlation_score': avg_score,
            'average_voice_events_per_browser_event': avg_voice_events,
            'score_distribution': {
                'min': min(scores) if scores else 0,
                'max': max(scores) if scores else 0,
                'median': sorted(scores)[len(scores)//2] if scores else 0
            }
        }
