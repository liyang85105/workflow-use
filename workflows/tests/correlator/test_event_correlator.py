import pytest
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow_use.correlator.event_correlator import (
    EventCorrelator, VoiceEvent, BrowserEvent, CorrelationMethod, CorrelationResult
)


class TestEventCorrelator:
    
    def setup_method(self):
        """测试前准备"""
        self.correlator = EventCorrelator(time_window=5.0, min_confidence=0.3)
        
        # 创建测试数据
        self.base_time = 1000.0
        self.session_id = "test_session_123"
        self.url = "https://example.com"
    
    def create_browser_event(self, event_type: str, timestamp_offset: float = 0.0) -> BrowserEvent:
        """创建测试用浏览器事件"""
        return BrowserEvent(
            id=f"browser_{event_type}_{timestamp_offset}",
            type=event_type,
            timestamp=self.base_time + timestamp_offset,
            url=self.url,
            xpath="//button[@id='submit']",
            css_selector="#submit",
            element_tag="button",
            value=None,
            session_id=self.session_id,
            tab_id="tab_1"
        )
    
    def create_voice_event(self, text: str, timestamp_offset: float = 0.0, confidence: float = 0.8) -> VoiceEvent:
        """创建测试用语音事件"""
        return VoiceEvent(
            id=f"voice_{timestamp_offset}",
            text=text,
            timestamp=self.base_time + timestamp_offset,
            confidence=confidence,
            session_id=self.session_id,
            url=self.url,
            intent_type="click"
        )
    
    def test_perfect_time_correlation(self):
        """测试完美时间关联"""
        browser_event = self.create_browser_event("click", 0.0)
        voice_event = self.create_voice_event("点击提交按钮", 0.0)
        
        correlations = self.correlator.correlate_events([browser_event], [voice_event])
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert correlation.browser_event == browser_event
        assert len(correlation.voice_events) == 1
        assert correlation.voice_events[0] == voice_event
        assert correlation.correlation_score > 0.5
    
    def test_time_window_correlation(self):
        """测试时间窗口内的关联"""
        browser_event = self.create_browser_event("click", 0.0)
        
        # 在时间窗口内的语音事件
        voice_event_1 = self.create_voice_event("准备点击", -2.0)
        voice_event_2 = self.create_voice_event("点击按钮", 1.0)
        
        # 在时间窗口外的语音事件
        voice_event_3 = self.create_voice_event("这个不相关", -10.0)
        
        correlations = self.correlator.correlate_events(
            [browser_event], 
            [voice_event_1, voice_event_2, voice_event_3]
        )
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert len(correlation.voice_events) == 2  # 只有窗口内的事件
        assert voice_event_3 not in correlation.voice_events
    
    def test_no_correlation(self):
        """测试无关联情况"""
        browser_event = self.create_browser_event("click", 0.0)
        voice_event = self.create_voice_event("无关的语音", 10.0)  # 超出时间窗口
        
        correlations = self.correlator.correlate_events([browser_event], [voice_event])
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert len(correlation.voice_events) == 0
        assert correlation.correlation_score == 0.0
    
    def test_multiple_browser_events(self):
        """测试多个浏览器事件"""
        browser_events = [
            self.create_browser_event("click", 0.0),
            self.create_browser_event("input", 10.0),  # 增大时间间隔
            self.create_browser_event("navigation", 20.0)  # 增大时间间隔
        ]
        
        voice_events = [
            self.create_voice_event("点击按钮", 0.5),
            self.create_voice_event("输入文本", 10.5),  # 对应调整
            self.create_voice_event("跳转页面", 19.5)   # 对应调整
        ]
        
        correlations = self.correlator.correlate_events(browser_events, voice_events)
        
        assert len(correlations) == 3
        # 每个浏览器事件都应该有对应的关联
        for i, correlation in enumerate(correlations):
            assert correlation.browser_event == browser_events[i]
            assert len(correlation.voice_events) == 1
    
    def test_confidence_threshold(self):
        """测试置信度阈值"""
        correlator = EventCorrelator(time_window=5.0, min_confidence=0.8)
        
        browser_event = self.create_browser_event("click", 0.0)
        low_confidence_voice = self.create_voice_event("点击", 0.0, confidence=0.5)
        
        correlations = correlator.correlate_events([browser_event], [low_confidence_voice])
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert len(correlation.voice_events) == 0  # 因为置信度不够
        assert correlation.correlation_score == 0.0
    
    def test_semantic_correlation(self):
        """测试语义关联"""
        correlator = EventCorrelator(
            correlation_method=CorrelationMethod.SEMANTIC,
            min_confidence=0.1
        )
        
        browser_event = self.create_browser_event("click", 0.0)
        voice_event = self.create_voice_event("点击提交按钮", 0.0)
        
        correlations = correlator.correlate_events([browser_event], [voice_event])
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert correlation.correlation_method == CorrelationMethod.SEMANTIC
        assert correlation.correlation_score > 0.0
    
    def test_hybrid_correlation(self):
        """测试混合关联"""
        correlator = EventCorrelator(
            correlation_method=CorrelationMethod.HYBRID,
            min_confidence=0.1
        )
        
        browser_event = self.create_browser_event("click", 0.0)
        voice_event = self.create_voice_event("点击按钮", 1.0)
        
        correlations = correlator.correlate_events([browser_event], [voice_event])
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert correlation.correlation_method == CorrelationMethod.HYBRID
        assert 'time_score' in correlation.metadata
        assert 'semantic_score' in correlation.metadata
    
    def test_session_isolation(self):
        """测试会话隔离"""
        browser_event = self.create_browser_event("click", 0.0)
        
        # 不同会话的语音事件
        voice_event_same_session = self.create_voice_event("点击按钮", 0.0)
        voice_event_different_session = VoiceEvent(
            id="voice_diff_session",
            text="点击按钮",
            timestamp=self.base_time,
            confidence=0.8,
            session_id="different_session",
            url=self.url
        )
        
        correlations = self.correlator.correlate_events(
            [browser_event], 
            [voice_event_same_session, voice_event_different_session]
        )
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert len(correlation.voice_events) == 1
        assert correlation.voice_events[0] == voice_event_same_session
    
    def test_url_matching(self):
        """测试URL匹配"""
        browser_event = self.create_browser_event("click", 0.0)
        
        # 相同URL的语音事件
        voice_event_same_url = self.create_voice_event("点击按钮", 0.0)
        
        # 不同URL的语音事件
        voice_event_different_url = VoiceEvent(
            id="voice_diff_url",
            text="点击按钮",
            timestamp=self.base_time,
            confidence=0.8,
            session_id=self.session_id,
            url="https://different.com"
        )
        
        correlations = self.correlator.correlate_events(
            [browser_event], 
            [voice_event_same_url, voice_event_different_url]
        )
        
        assert len(correlations) == 1
        correlation = correlations[0]
        assert len(correlation.voice_events) == 1
        assert correlation.voice_events[0] == voice_event_same_url
    
    def test_correlation_statistics(self):
        """测试关联统计"""
        browser_events = [
            self.create_browser_event("click", 0.0),
            self.create_browser_event("input", 5.0),
            self.create_browser_event("scroll", 10.0)  # 这个没有对应语音
        ]
        
        voice_events = [
            self.create_voice_event("点击按钮", 0.5),
            self.create_voice_event("输入文本", 5.5)
        ]
        
        correlations = self.correlator.correlate_events(browser_events, voice_events)
        stats = self.correlator.get_correlation_statistics(correlations)
        
        assert stats['total_browser_events'] == 3
        assert stats['correlated_events'] == 2
        assert stats['correlation_rate'] == 2/3
        assert stats['average_correlation_score'] > 0
    
    def test_empty_events(self):
        """测试空事件列表"""
        correlations = self.correlator.correlate_events([], [])
        assert len(correlations) == 0
        
        stats = self.correlator.get_correlation_statistics(correlations)
        assert stats == {}
    
    def test_semantic_similarity_calculation(self):
        """测试语义相似度计算"""
        browser_event = self.create_browser_event("click", 0.0)
        
        # 高相似度的语音事件
        high_sim_voice = self.create_voice_event("点击按钮", 0.0)
        
        # 低相似度的语音事件
        low_sim_voice = self.create_voice_event("输入文本", 0.0)
        
        high_similarity = self.correlator._calculate_semantic_similarity(browser_event, high_sim_voice)
        low_similarity = self.correlator._calculate_semantic_similarity(browser_event, low_sim_voice)
        
        assert high_similarity > low_similarity
        assert 0 <= high_similarity <= 1
        assert 0 <= low_similarity <= 1


if __name__ == "__main__":
    pytest.main([__file__])
