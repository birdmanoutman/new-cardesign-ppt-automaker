"""
测试配置
"""

import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """创建测试数据目录"""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir) 