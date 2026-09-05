"""
测试: Writer 正文生成与修订
"""

import pytest

from kunlun.agents.writer import Writer

pytestmark = pytest.mark.unit

class TestWriterPromptBuilding:
    """提示词构建 - 验证蓝图结构化数据消费"""

    @pytest.fixture
    def minimal_blueprint(self):
        """最小化蓝图"""
        return {
            "chapter": 5,
            "chapter_type": "normal",
            "word_count_target": 2500,
            "hook_requirement": {"type": "question"},
        }

    @pytest.fixture
    def full_blueprint(self):
        """完整蓝图"""
        return {
            "chapter": 10,
            "chapter_type": "climax",
            "word_count_target": 3500,
            "hook_requirement": {
                "type": "cliffhanger",
                "description": "主角被围困，生死未卜",
            },
            "arc_stage": "ordeal",
            "scenes": [
                {
                    "title": "绝境",
                    "function": "climax",
                    "summary": "主角被三大高手围攻",
                    "characters_involved": ["主角", "反派A", "反派B"],
                    "pleasure_points": ["level_up"],
                },
                {
                    "title": "转机",
                    "function": "resolve",
                    "summary": "主角临阵突破",
                    "characters_involved": ["主角"],
                    "pleasure_points": ["revelation"],
                },
            ],
            "emotion_curve": {
                "start_emotion": "tense",
                "end_emotion": "triumphant",
            },
            "pleasure_points": [
                {"type": "level_up", "scene_at": 1, "description": "主角临阵突破"},
                {"type": "revelation", "scene_at": 1, "description": "发现反派阴谋"},
            ],
            "foreshadowing": {
                "to_reveal": ["神秘人身份"],
                "to_plant": ["新秘境线索"],
            },
            "audit_risk_marks": {
                "G1_arc_deviation": False,
                "G2_info_dump": True,
                "G3_ai_detection": False,
            },
        }

    def test_build_prompt_minimal(self, minimal_blueprint):
        """最小蓝图生成基础prompt"""
        writer = Writer()
        prompt = writer._build_prompt(minimal_blueprint, "snap_001")
        assert "第5章" in prompt
        assert "normal" in prompt
        assert "2500" in prompt
        assert "question" in prompt
        assert "KG快照" in prompt

    def test_build_prompt_full_blueprint(self, full_blueprint):
        """完整蓝图消费所有结构化数据"""
        writer = Writer()
        prompt = writer._build_prompt(full_blueprint, "snap_002")

        # 基础信息
        assert "第10章" in prompt
        assert "climax" in prompt
        assert "3500" in prompt
        assert "cliffhanger" in prompt
        assert "主角被围困，生死未卜" in prompt

        # 章节蓝图
        assert "弧线阶段: ordeal" in prompt
        assert "情绪曲线: tense → triumphant" in prompt

        # 场景设计
        assert "场景设计 (2个)" in prompt
        assert "【绝境】climax - 主角被三大高手围攻" in prompt
        assert "涉及角色: 主角, 反派A, 反派B" in prompt
        assert "爽点: level_up" in prompt
        assert "【转机】resolve - 主角临阵突破" in prompt

        # 爽点排布
        assert "爽点排布 (2个)" in prompt
        assert "level_up: 主角临阵突破 (场景2)" in prompt
        assert "revelation: 发现反派阴谋 (场景2)" in prompt

        # 伏笔指令
        assert "必须揭示: 神秘人身份" in prompt
        assert "必须安插: 新秘境线索" in prompt

        # 审计风险
        assert "审计风险预标" in prompt
        assert "G2_info_dump" in prompt

        # 写作要求
        assert "严格按场景顺序和功能推进" in prompt
        assert "实现情绪曲线: tense → triumphant" in prompt
        assert "结尾必须实现 cliffhanger 钩子" in prompt

    def test_build_prompt_with_preference_hints(self, minimal_blueprint):
        """偏好提示注入"""
        writer = Writer()
        prompt = writer._build_prompt(
            minimal_blueprint, "snap_001", preference_hints="多写心理描写，少写环境"
        )
        assert "作者偏好提示" in prompt
        assert "多写心理描写，少写环境" in prompt

    def test_build_prompt_empty_scenes(self, minimal_blueprint):
        """空场景列表不报错"""
        blueprint = {**minimal_blueprint, "scenes": []}
        writer = Writer()
        prompt = writer._build_prompt(blueprint, "snap_001")
        assert "场景设计 (0个)" in prompt

    def test_build_prompt_missing_optional_fields(self, minimal_blueprint):
        """缺失可选字段时使用默认值"""
        writer = Writer()
        prompt = writer._build_prompt(minimal_blueprint, "snap_001")
        # 不应崩溃
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_build_prompt_audit_risk_no_risks(self, full_blueprint):
        """无风险时不显示风险区"""
        blueprint = {**full_blueprint}
        blueprint["audit_risk_marks"] = {
            "G1_arc_deviation": False,
            "G2_info_dump": False,
            "G3_ai_detection": False,
        }
        writer = Writer()
        prompt = writer._build_prompt(blueprint, "snap_001")
        assert "审计风险预标" not in prompt


class TestWriterFixPrompt:
    """修订提示词构建"""

    @pytest.fixture
    def audit_report(self):
        return {
            "gates": {
                "G1": {"level": "PASS", "detail": "弧线正常"},
                "G3": {"level": "FATAL", "detail": "AI味过浓，连词密度超标"},
                "G4": {"level": "FATAL", "detail": "爽点间隔过长，第3段到第8段无爽点"},
            }
        }

    def test_build_fix_prompt(self, audit_report):
        """构建修订提示词"""
        writer = Writer()
        draft = "这是原始正文..."
        failed_gates = ["G3", "G4"]
        prompt = writer._build_fix_prompt(draft, audit_report, failed_gates)

        assert "以下网文章节未通过质检" in prompt
        assert "G3: AI味过浓，连词密度超标" in prompt
        assert "G4: 爽点间隔过长，第3段到第8段无爽点" in prompt
        assert "原始正文:" in prompt
        assert "这是原始正文..." in prompt
        assert "修复后的正文" in prompt

    def test_build_fix_prompt_empty_failed_gates(self, audit_report):
        """无失败门禁时提示词仍有效"""
        writer = Writer()
        draft = "正文"
        prompt = writer._build_fix_prompt(draft, audit_report, [])
        assert "问题:" in prompt
        assert "原始正文:" in prompt


class TestWriterAgentMetadata:
    """Agent元数据验证"""

    def test_agent_name(self):
        writer = Writer()
        assert writer.agent_name == "writer"

    def test_capabilities(self):
        writer = Writer()
        assert "draft_generation" in writer.capabilities
        assert "multi_model_parallel" in writer.capabilities
        assert "audit_fix_revision" in writer.capabilities
        assert "style_injection" in writer.capabilities

    def test_gacha_engine_initialized(self):
        """验证Gacha引擎已初始化"""
        writer = Writer()
        assert hasattr(writer, "gacha")
        assert writer.gacha is not None
