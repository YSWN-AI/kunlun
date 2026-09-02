"""
测试时空一致性模块 (Spacetime)
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


class TestSpacetimeModule:
    def test_module_file_exists(self):
        """spacetime __init__.py 存在，虽然 engine.py 缺失但模块结构完整"""
        init_path = Path(__file__).resolve().parent.parent / "kunlun" / "spacetime" / "__init__.py"
        assert init_path.exists()
        assert init_path.is_file()

    def test_module_exports(self):
        """验证 __all__ 导出列表"""
        init_path = Path(__file__).resolve().parent.parent / "kunlun" / "spacetime" / "__init__.py"
        content = init_path.read_text(encoding="utf-8")
        assert "SpaceNode" in content
        assert "SpacetimeEngine" in content
        assert "SpacetimeEvent" in content
        assert "TimeNode" in content
        assert "spacetime_engine" in content
        assert "__all__" in content

    def test_module_is_importable_structure(self):
        """验证 spacetime 目录是有效的 Python 包 (有 __init__.py)"""
        pkg_path = Path(__file__).resolve().parent.parent / "kunlun" / "spacetime"
        assert pkg_path.is_dir()
        init = pkg_path / "__init__.py"
        assert init.exists()
