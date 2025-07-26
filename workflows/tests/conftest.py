"""
pytest 配置文件
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径，确保可以导入 workflow_use 模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 可以在这里添加全局的 pytest fixtures
import pytest


@pytest.fixture
def sample_voice_events():
    """提供示例语音事件数据"""
    from workflow_use.correlator.event_correlator import VoiceEvent
    
    return [
        VoiceEvent(
            id="voice_1",
            text="点击提交按钮",
            timestamp=1000.0,
            confidence=0.9,
            session_id="test_session",
            url="https://example.com"
        ),
        VoiceEvent(
            id="voice_2", 
            text="输入用户名admin",
            timestamp=1005.0,
            confidence=0.8,
            session_id="test_session",
            url="https://example.com"
        )
    ]


@pytest.fixture
def sample_browser_events():
    """提供示例浏览器事件数据"""
    from workflow_use.correlator.event_correlator import BrowserEvent
    
    return [
        BrowserEvent(
            id="browser_1",
            type="click",
            timestamp=1001.0,
            url="https://example.com",
            xpath="//button[@id='submit']",
            css_selector="#submit",
            element_tag="button",
            session_id="test_session"
        ),
        BrowserEvent(
            id="browser_2",
            type="input", 
            timestamp=1006.0,
            url="https://example.com",
            xpath="//input[@name='username']",
            css_selector="input[name='username']",
            element_tag="input",
            value="admin",
            session_id="test_session"
        )
    ]