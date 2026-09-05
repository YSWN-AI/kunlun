"""
测试: Architect 蓝图生成
"""

import pytest

from kunlun.agents.architect import Architect

pytestmark = pytest.mark.unit

class TestArchitectBlueprint:
    """蓝图生成核心逻辑"""

    @pytest.fixture
    def architect(self):
        return Architect()

    def test_chapter_templates_complete(self, architect):
        """验证4种章节类型模板均完整"""
        for chap_type in ["normal", "climax", "transition", "battle"]:
            template = architect.CHAPTER_TEMPLATES[chap_type]
            assert "word_count_range" in template
            assert "scene_count" in template
            assert len(template["word_count_range"]) == 2
            assert len(template["scene_count"]) == 2

    def test_merge_blueprint_empty_llm_output(self, architect):
        """LLM输出为空时，合并结果仍完整"""
        result = architect._merge_blueprint(
            llm_output={},
            template=architect.CHAPTER_TEMPLATES["normal"],
            book_id="book_001",
            chapter=5,
            chapter_type="normal",
            kg_snapshot_id="snap_001",
        )
        assert result["book_id"] == "book_001"
        assert result["chapter"] == 5
        assert result["chapter_type"] == "normal"
        assert isinstance(result["scenes"], list)
        assert isinstance(result["pleasure_points"], list)
        assert "emotion_curve" in result
        assert "foreshadowing" in result
        assert result["scenes"] == []
        assert result["pleasure_points"] == []

    def test_merge_blueprint_with_llm_output(self, architect):
        """LLM有输出时，保留其内容"""
        llm = {
            "arc_stage": "tests",
            "scenes": [
                {
                    "title": "入城",
                    "function": "introduce",
                    "summary": "主角进入新城",
                    "characters_involved": ["主角", "城门守卫"],
                    "pleasure_points": [],
                }
            ],
            "emotion_curve": {
                "start_emotion": "tense",
                "end_emotion": "excited",
            },
        }
        result = architect._merge_blueprint(
            llm_output=llm,
            template=architect.CHAPTER_TEMPLATES["normal"],
            book_id="book_001",
            chapter=5,
            chapter_type="normal",
            kg_snapshot_id="snap_001",
        )
        assert result["arc_stage"] == "tests"
        assert len(result["scenes"]) == 1
        assert result["scenes"][0]["title"] == "入城"

    def test_build_blueprint_prompt_basic(self, architect):
        """验证基础prompt生成"""
        prompt = architect._build_blueprint_prompt(
            chapter=3,
            chapter_type="normal",
            template=architect.CHAPTER_TEMPLATES["normal"],
            kg_summary="测试快照",
            preference_hints="",
        )
        assert "第3章" in prompt
        assert "normal" in prompt
        assert "JSON" in prompt
        assert "arc_stage" in prompt
        assert "scenes" in prompt
        assert "emotion_curve" in prompt
        assert "foreshadowing" in prompt

    def test_build_blueprint_prompt_with_hints(self, architect):
        """验证偏好注入"""
        prompt = architect._build_blueprint_prompt(
            chapter=3,
            chapter_type="battle",
            template=architect.CHAPTER_TEMPLATES["battle"],
            kg_summary="KG数据",
            preference_hints="多写打斗场面",
        )
        assert "多写打斗场面" in prompt
        assert "battle" in prompt

    def test_parse_valid_json(self, architect):
        """解析合法的JSON蓝图"""
        text = '{"arc_stage": "tests", "scenes": [{"title": "测试"}]}'
        result = architect._parse_blueprint_json(text)
        assert result is not None
        assert result["arc_stage"] == "tests"

    def test_parse_json_with_markdown_wrapper(self, architect):
        """解析带markdown代码块标记的JSON"""
        text = '```json\n{"arc_stage": "tests", "scenes": []}\n```'
        result = architect._parse_blueprint_json(text)
        assert result is not None
        assert result["arc_stage"] == "tests"

    def test_parse_trailing_comma_json(self, architect):
        """解析带尾随逗号的JSON"""
        text = '{"arc_stage": "tests", "scenes": [],}'
        result = architect._parse_blueprint_json(text)
        assert result is not None
        assert result.get("arc_stage") == "tests"  # 验证实际解析内容
        assert result.get("scenes") == []

    def test_parse_invalid_json(self, architect):
        """非法JSON返回None"""
        text = "这只是一段普通文本没有JSON"
        result = architect._parse_blueprint_json(text)
        assert result is None

    def test_parse_empty_text(self, architect):
        """空文本返回None"""
        assert architect._parse_blueprint_json("") is None
        assert architect._parse_blueprint_json(None) is None


class TestArchitectAgentMetadata:
    """Agent元数据验证"""

    def test_agent_name(self):
        architect = Architect()
        assert architect.agent_name == "architect"

    def test_capabilities(self):
        architect = Architect()
        assert "blueprint_generation" in architect.capabilities
        assert "emotion_curve_planning" in architect.capabilities
        assert "pleasure_point_scheduling" in architect.capabilities
        assert "foreshadowing_management" in architect.capabilities
