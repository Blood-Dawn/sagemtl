"""
Pytest configuration for desktop tests.
"""

import pytest
import sys
from pathlib import Path

# Add sagemtl_desktop to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_chinese_text():
    """Sample Chinese text for testing"""
    return """这是一个测试文件。
修真者的道心非常重要。
宗主说："所有弟子都要努力修炼。"
师兄和师妹一起去了秘境。"""


@pytest.fixture
def sample_japanese_text():
    """Sample Japanese text for testing"""
    return """これはテストです。
修行者の心はとても重要です。"""


@pytest.fixture
def sample_english_text():
    """Sample English text for testing"""
    return """This is a test file.
The cultivator's resolve is very important.
The Sect Master said: "All disciples must work hard."
Senior Brother and Junior Sister went to the secret realm together."""
