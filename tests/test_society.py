"""
测试社会推演系统 — 第二阶段扩展的7个新Prompt + SociologistAgent 扩展
"""

import pytest

pytestmark = pytest.mark.integration

from unittest.mock import AsyncMock, patch

from kunlun.agents.sociologist import (
    SocietyResult,
    SociologistAgent,
)
from kunlun.prompts.society import (
    PROMPT_PARAMS,
    SOCIETY_PROMPTS,
    _lazy_load_extensions,
    get_prompt,
)


class TestExtendedPrompts:
    """测试6个毛细血管维度 + 冰山技法 Prompt 模板"""

    def test_all_extended_prompts_registered(self):
        """确保7个新Prompt已在 SOCIETY_PROMPTS 中注册"""
        _lazy_load_extensions()
        expected = {
            "history",
            "power_system",
            "technology",
            "ecology",
            "underworld",
            "philosophy",
            "iceberg",
        }
        assert expected.issubset(set(SOCIETY_PROMPTS.keys()))
        for key in expected:
            assert SOCIETY_PROMPTS[key] is not None

    def test_all_extended_params_registered(self):
        """确保7个新Prompt的参数表已注册"""
        expected_params = {
            "history": ["history_baseline"],
            "power_system": ["power_baseline"],
            "technology": ["tech_baseline"],
            "ecology": ["ecology_baseline"],
            "underworld": ["underworld_baseline"],
            "philosophy": ["philosophy_baseline"],
            "iceberg": ["macro_setting"],
        }
        for key, params in expected_params.items():
            assert PROMPT_PARAMS[key] == params

    def test_get_prompt_history_lazy_load(self):
        """历史维度 Prompt 延迟加载后可用"""
        prompt = get_prompt("history", history_baseline="测试历史基线")
        assert "测试历史基线" in prompt
        assert "开国原罪" in prompt

    def test_get_prompt_power_system(self):
        """力量体系 Prompt 格式化"""
        prompt = get_prompt("power_system", power_baseline="测试战力基线")
        assert "测试战力基线" in prompt
        assert "战力天花板" in prompt

    def test_get_prompt_technology(self):
        """科技百工 Prompt 格式化"""
        prompt = get_prompt("technology", tech_baseline="测试科技基线")
        assert "测试科技基线" in prompt
        assert "隐秘信息传递" in prompt

    def test_get_prompt_ecology(self):
        """生态物产 Prompt 格式化"""
        prompt = get_prompt("ecology", ecology_baseline="测试生态基线")
        assert "测试生态基线" in prompt
        assert "战略物产" in prompt

    def test_get_prompt_underworld(self):
        """灰域 Prompt 格式化"""
        prompt = get_prompt("underworld", underworld_baseline="测试灰域基线")
        assert "测试灰域基线" in prompt
        assert "黑市" in prompt

    def test_get_prompt_philosophy(self):
        """哲学信仰 Prompt 格式化"""
        prompt = get_prompt("philosophy", philosophy_baseline="测试哲学基线")
        assert "测试哲学基线" in prompt
        assert "主流价值观" in prompt

    def test_get_prompt_iceberg(self):
        """冰山技法 Prompt 格式化"""
        prompt = get_prompt("iceberg", macro_setting="测试宏观设定")
        assert "测试宏观设定" in prompt
        assert "冰山" in prompt

    def test_get_prompt_missing_param(self):
        """缺少参数时抛出 ValueError"""
        with pytest.raises(ValueError, match="缺少参数"):
            get_prompt("history")

    def test_original_prompts_still_work(self):
        """确保原有6个 Prompt 不受影响"""
        prompt = get_prompt("economy", economy_baseline="测试")
        assert "经济" in prompt
        prompt = get_prompt("law", law_baseline="测试")
        assert "律法" in prompt
        prompt = get_prompt("culture", culture_baseline="测试")
        assert "阶级" in prompt
        prompt = get_prompt("custom", custom_baseline="测试")
        assert "习俗" in prompt
        prompt = get_prompt("macro_to_micro", macro_setting="测试")
        assert "降维" in prompt
        prompt = get_prompt(
            "social_ripple", world_parameters="测试", proposed_change="测试", chapter_context="测试"
        )
        assert "连锁反应" in prompt


class TestExtended2Prompts:
    """测试第三阶段6个隐秘维度 Prompt 模板"""

    def test_get_prompt_admin(self):
        prompt = get_prompt("admin", admin_baseline="测试行政基线")
        assert "测试行政基线" in prompt
        assert "合法搞钱" in prompt

    def test_get_prompt_clan(self):
        prompt = get_prompt("clan", clan_baseline="测试宗族基线")
        assert "测试宗族基线" in prompt
        assert "护城河" in prompt

    def test_get_prompt_propaganda(self):
        prompt = get_prompt("propaganda", propaganda_baseline="测试舆论基线")
        assert "测试舆论基线" in prompt
        assert "童谣" in prompt

    def test_get_prompt_astronomy(self):
        prompt = get_prompt("astronomy", astronomy_baseline="测试天文基线")
        assert "测试天文基线" in prompt
        assert "日食" in prompt

    def test_get_prompt_mobility(self):
        prompt = get_prompt("mobility", mobility_baseline="测试阶层基线")
        assert "测试阶层基线" in prompt
        assert "跃迁" in prompt

    def test_get_prompt_language(self):
        prompt = get_prompt("language", language_baseline="测试语言基线")
        assert "测试语言基线" in prompt
        assert "文字狱" in prompt

    def test_all_extended2_params_registered(self):
        expected = {
            "admin": ["admin_baseline"],
            "clan": ["clan_baseline"],
            "propaganda": ["propaganda_baseline"],
            "astronomy": ["astronomy_baseline"],
            "mobility": ["mobility_baseline"],
            "language": ["language_baseline"],
        }
        for key, params in expected.items():
            assert PROMPT_PARAMS[key] == params


class TestSociologistAgentExtended:
    """测试 SociologistAgent 扩展功能"""

    @pytest.fixture
    def agent(self):
        return SociologistAgent()

    def test_select_model_new_dimensions(self, agent):
        """新维度模型选择（批次2+3+4）"""
        assert agent._select_model("history") == "deepseek-reasoner"
        assert agent._select_model("power_system") == "deepseek-reasoner"
        assert agent._select_model("technology") == "deepseek-reasoner"
        assert agent._select_model("ecology") == "deepseek-chat"
        assert agent._select_model("underworld") == "deepseek-chat"
        assert agent._select_model("philosophy") == "deepseek-chat"
        assert agent._select_model("iceberg") == "deepseek-chat"
        # 第三阶段
        assert agent._select_model("admin") == "deepseek-reasoner"
        assert agent._select_model("clan") == "deepseek-chat"
        assert agent._select_model("propaganda") == "deepseek-chat"
        assert agent._select_model("astronomy") == "deepseek-reasoner"
        assert agent._select_model("mobility") == "deepseek-chat"
        assert agent._select_model("language") == "deepseek-reasoner"
        # 第四阶段
        assert agent._select_model("military") == "deepseek-reasoner"
        assert agent._select_model("entourage") == "deepseek-chat"
        assert agent._select_model("population_control") == "deepseek-reasoner"
        assert agent._select_model("inner_court") == "deepseek-chat"
        assert agent._select_model("medical") == "deepseek-reasoner"
        # 第五阶段
        assert agent._select_model("forensic") == "deepseek-chat"
        assert agent._select_model("cult") == "deepseek-reasoner"
        assert agent._select_model("royal_monopoly") == "deepseek-chat"
        assert agent._select_model("espionage") == "deepseek-chat"
        assert agent._select_model("diplomacy") == "deepseek-reasoner"
        assert agent._select_model("underbelly") == "deepseek-chat"
        # 第六阶段
        assert agent._select_model("pleasure_engineering") == "deepseek-reasoner"
        assert agent._select_model("hook_management") == "deepseek-chat"
        assert agent._select_model("villain_arc") == "deepseek-chat"
        assert agent._select_model("anti_ai_style") == "deepseek-chat"

    def test_select_model_original_unchanged(self, agent):
        """原有维度模型选择不受影响"""
        assert agent._select_model("economy") == "deepseek-reasoner"
        assert agent._select_model("law") == "deepseek-reasoner"
        assert agent._select_model("culture") == "deepseek-chat"
        assert agent._select_model("custom") == "deepseek-chat"
        assert agent._select_model("macro_to_micro") == "deepseek-chat"
        assert agent._select_model("social_ripple") == "deepseek-reasoner"

    @pytest.mark.asyncio
    async def test_deduce_all_default_includes_new_dimensions(self, agent):
        """默认 deduce_all 包含新维度"""
        with patch.object(agent, "deduce", new_callable=AsyncMock) as mock_deduce:
            mock_deduce.return_value = SocietyResult(
                dimension="test", prompt_used="", model_used="", output="ok"
            )
            params = {
                "economy_baseline": "e",
                "law_baseline": "l",
                "culture_baseline": "c",
                "custom_baseline": "cu",
                "history_baseline": "h",
                "power_baseline": "p",
                "tech_baseline": "t",
                "ecology_baseline": "ec",
                "underworld_baseline": "u",
                "philosophy_baseline": "ph",
                "admin_baseline": "ad",
                "clan_baseline": "cl",
                "propaganda_baseline": "pr",
                "astronomy_baseline": "as",
                "mobility_baseline": "mo",
                "language_baseline": "la",
                "military_baseline": "mi",
                "entourage_baseline": "en",
                "population_baseline": "pc",
                "inner_court_baseline": "ic",
                "medical_baseline": "me",
                "forensic_baseline": "fo",
                "cult_baseline": "cu",
                "royal_monopoly_baseline": "rm",
                "espionage_baseline": "es",
                "diplomacy_baseline": "di",
                "underbelly_baseline": "un",
                "pleasure_baseline": "pl",
                "hook_baseline": "ho",
                "villain_baseline": "vi",
                "author_draft": "adraft",
                "ai_logic": "alogic",
                # 第七阶段参数
                "compliance_baseline": "co",
                "platform_baseline": "po",
                "reader_baseline": "re",
                "ip_baseline": "ip",
                "daily_hours": "dh",
                "target_words": "tw",
                "work_mode": "wm",
                "health_issues": "hi",
                "input_ratio": "ir",
                "planning_ratio": "pr",
                "writing_ratio": "wr",
                "review_ratio": "rr",
            }
            results = await agent.deduce_all(params)
            # 应该是44个维度
            assert len(results) == 44
            expected_dims = {
                "economy",
                "law",
                "culture",
                "custom",
                "history",
                "power_system",
                "technology",
                "ecology",
                "underworld",
                "philosophy",
                "admin",
                "clan",
                "propaganda",
                "astronomy",
                "mobility",
                "language",
                "military",
                "entourage",
                "population_control",
                "inner_court",
                "medical",
                "forensic",
                "cult",
                "royal_monopoly",
                "espionage",
                "diplomacy",
                "underbelly",
                "pleasure_engineering",
                "hook_management",
                "villain_arc",
                "anti_ai_style",
                "resource_network",
                "class_barrier",
                "info_blackbox",
                "spatial_ecology",
                "moral_dilemma",
                "serial_crisis",
                "reader_biochem",
                "genre_innovation",
                "compliance_audit",
                "platform_optimization",
                "reader_collab",
                "ip_derivative",
                "author_sop",
            }
            assert set(results.keys()) == expected_dims

    @pytest.mark.asyncio
    async def test_deduce_all_subset(self, agent):
        """自定义子集推演"""
        with patch.object(agent, "deduce", new_callable=AsyncMock) as mock_deduce:
            mock_deduce.return_value = SocietyResult(
                dimension="test", prompt_used="", model_used="", output="ok"
            )
            results = await agent.deduce_all(
                {"history_baseline": "h", "power_baseline": "p"},
                dimensions=["history", "power_system"],
            )
            assert len(results) == 2
            assert set(results.keys()) == {"history", "power_system"}

    @pytest.mark.asyncio
    async def test_iceberg_convert(self, agent):
        """冰山技法转化"""
        with patch.object(agent, "deduce", new_callable=AsyncMock) as mock_deduce:
            mock_deduce.return_value = SocietyResult(
                dimension="iceberg", prompt_used="", model_used="", output="小说片段"
            )
            result = await agent.iceberg_convert("盐铁专卖导致盐价高昂")
            assert result.dimension == "iceberg"
            assert result.output == "小说片段"


class TestExtended3Prompts:
    """测试第四阶段5个微观与中观生态维度 Prompt 模板"""

    def test_get_prompt_military(self):
        prompt = get_prompt("military", military_baseline="测试军制基线")
        assert "测试军制基线" in prompt
        assert "营啸" in prompt

    def test_get_prompt_entourage(self):
        prompt = get_prompt("entourage", entourage_baseline="测试幕僚基线")
        assert "测试幕僚基线" in prompt
        assert "白手套" in prompt

    def test_get_prompt_population_control(self):
        prompt = get_prompt("population_control", population_baseline="测试户籍基线")
        assert "测试户籍基线" in prompt
        assert "海捕" in prompt

    def test_get_prompt_inner_court(self):
        prompt = get_prompt("inner_court", inner_court_baseline="测试内宅基线")
        assert "测试内宅基线" in prompt
        assert "联姻" in prompt

    def test_get_prompt_medical(self):
        prompt = get_prompt("medical", medical_baseline="测试医疗基线")
        assert "测试医疗基线" in prompt
        assert "药渣" in prompt

    def test_all_extended3_params_registered(self):
        expected = {
            "military": ["military_baseline"],
            "entourage": ["entourage_baseline"],
            "population_control": ["population_baseline"],
            "inner_court": ["inner_court_baseline"],
            "medical": ["medical_baseline"],
        }
        for key, params in expected.items():
            assert PROMPT_PARAMS[key] == params

    def test_all_extended3_prompts_registered(self):
        """确保5个新Prompt已在 SOCIETY_PROMPTS 中注册"""
        _lazy_load_extensions()
        expected = {
            "military",
            "entourage",
            "population_control",
            "inner_court",
            "medical",
        }
        assert expected.issubset(set(SOCIETY_PROMPTS.keys()))
        for key in expected:
            assert SOCIETY_PROMPTS[key] is not None


class TestStressTests:
    """压力测试方法"""

    @pytest.fixture
    def agent(self):
        return SociologistAgent()

    @pytest.mark.asyncio
    async def test_stress_butterfly(self, agent):
        with patch.object(agent, "deduce_all", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "clan": SocietyResult("clan", "", "", "宗族反扑"),
                "admin": SocietyResult("admin", "", "", "漕运中断"),
                "underworld": SocietyResult("underworld", "", "", "私盐通道易主"),
            }
            results = await agent.stress_test_butterfly(
                {"official_name": "李纲", "position": "户部侍郎", "crime": "贪墨"}
            )
            assert len(results) == 3
            assert set(results.keys()) == {"clan", "admin", "underworld"}

    @pytest.mark.asyncio
    async def test_stress_survival(self, agent):
        with patch.object(agent, "deduce_all", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "economy": SocietyResult("economy", "", "", "粮价崩溃"),
                "clan": SocietyResult("clan", "", "", "宗族闭仓"),
                "mobility": SocietyResult("mobility", "", "", "落草为寇"),
            }
            results = await agent.stress_test_survival({"disaster": "大旱", "region": "山西某县"})
            assert len(results) == 3
            assert set(results.keys()) == {"economy", "clan", "mobility"}

    @pytest.mark.asyncio
    async def test_stress_villain(self, agent):
        with patch.object(agent, "deduce_all", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "admin": SocietyResult("admin", "", "", "卡粮草"),
                "propaganda": SocietyResult("propaganda", "", "", "童谣抹黑"),
                "astronomy": SocietyResult("astronomy", "", "", "彗星解读"),
                "language": SocietyResult("language", "", "", "文字狱"),
            }
            results = await agent.stress_test_villain(
                {"name": "张守正", "position": "知府", "weakness": "刚直"}
            )
            assert len(results) == 4
            assert set(results.keys()) == {"admin", "propaganda", "astronomy", "language"}


class TestExtended4Prompts:
    """测试第五阶段6个边缘深度维度 Prompt 模板"""

    def test_get_prompt_forensic(self):
        prompt = get_prompt("forensic", forensic_baseline="测试司法基线")
        assert "测试司法基线" in prompt
        assert "仵作" in prompt

    def test_get_prompt_cult(self):
        prompt = get_prompt("cult", cult_baseline="测试宗教基线")
        assert "测试宗教基线" in prompt
        assert "神迹" in prompt

    def test_get_prompt_royal_monopoly(self):
        prompt = get_prompt("royal_monopoly", royal_monopoly_baseline="测试内帑基线")
        assert "测试内帑基线" in prompt
        assert "采办" in prompt

    def test_get_prompt_espionage(self):
        prompt = get_prompt("espionage", espionage_baseline="测试谍战基线")
        assert "测试谍战基线" in prompt
        assert "死间" in prompt

    def test_get_prompt_diplomacy(self):
        prompt = get_prompt("diplomacy", diplomacy_baseline="测试外交基线")
        assert "测试外交基线" in prompt
        assert "互市" in prompt

    def test_get_prompt_underbelly(self):
        prompt = get_prompt("underbelly", underbelly_baseline="测试贱业基线")
        assert "测试贱业基线" in prompt
        assert "粪车" in prompt

    def test_all_extended4_params_registered(self):
        expected = {
            "forensic": ["forensic_baseline"],
            "cult": ["cult_baseline"],
            "royal_monopoly": ["royal_monopoly_baseline"],
            "espionage": ["espionage_baseline"],
            "diplomacy": ["diplomacy_baseline"],
            "underbelly": ["underbelly_baseline"],
        }
        for key, params in expected.items():
            assert PROMPT_PARAMS[key] == params

    def test_all_extended4_prompts_registered(self):
        """确保6个新Prompt已在 SOCIETY_PROMPTS 中注册"""
        _lazy_load_extensions()
        expected = {
            "forensic",
            "cult",
            "royal_monopoly",
            "espionage",
            "diplomacy",
            "underbelly",
        }
        assert expected.issubset(set(SOCIETY_PROMPTS.keys()))
        for key in expected:
            assert SOCIETY_PROMPTS[key] is not None


class TestExtended5Prompts:
    """测试第六阶段4个叙事工程与商业逻辑维度 Prompt 模板"""

    def test_get_prompt_pleasure_engineering(self):
        prompt = get_prompt("pleasure_engineering", pleasure_baseline="测试爽点基线")
        assert "测试爽点基线" in prompt
        assert "权谋爽点工程" in prompt

    def test_get_prompt_hook_management(self):
        prompt = get_prompt("hook_management", hook_baseline="测试钩子基线")
        assert "测试钩子基线" in prompt
        assert "连载悬念与钩子矩阵" in prompt

    def test_get_prompt_villain_arc(self):
        prompt = get_prompt("villain_arc", villain_baseline="测试反派基线")
        assert "测试反派基线" in prompt
        assert "反派弧光与高光谢幕" in prompt

    def test_get_prompt_anti_ai_style(self):
        prompt = get_prompt("anti_ai_style", author_draft="作者草稿", ai_logic="AI逻辑")
        assert "作者草稿" in prompt
        assert "AI逻辑" in prompt
        assert "清除AI味" in prompt

    def test_all_extended5_params_registered(self):
        expected = {
            "pleasure_engineering": ["pleasure_baseline"],
            "hook_management": ["hook_baseline"],
            "villain_arc": ["villain_baseline"],
            "anti_ai_style": ["author_draft", "ai_logic"],
        }
        for key, params in expected.items():
            assert PROMPT_PARAMS[key] == params

    def test_all_extended5_prompts_registered(self):
        """确保4个新Prompt已在 SOCIETY_PROMPTS 中注册"""
        _lazy_load_extensions()
        expected = {
            "pleasure_engineering",
            "hook_management",
            "villain_arc",
            "anti_ai_style",
        }
        assert expected.issubset(set(SOCIETY_PROMPTS.keys()))
        for key in expected:
            assert SOCIETY_PROMPTS[key] is not None


class TestExtended6Prompts:
    """测试第七阶段5个现实运营与精力管理维度 Prompt 模板"""

    def test_get_prompt_compliance_audit(self):
        prompt = get_prompt("compliance_audit", compliance_baseline="测试合规基线")
        assert "测试合规基线" in prompt
        assert "红线排查" in prompt

    def test_get_prompt_platform_optimization(self):
        prompt = get_prompt("platform_optimization", platform_baseline="测试平台基线")
        assert "测试平台基线" in prompt
        assert "爆款书名矩阵" in prompt

    def test_get_prompt_reader_collab(self):
        prompt = get_prompt("reader_collab", reader_baseline="测试读者基线")
        assert "测试读者基线" in prompt
        assert "情绪曲线" in prompt

    def test_get_prompt_ip_derivative(self):
        prompt = get_prompt("ip_derivative", ip_baseline="测试IP基线")
        assert "测试IP基线" in prompt
        assert "感官锚点" in prompt

    def test_get_prompt_author_sop(self):
        prompt = get_prompt(
            "author_sop",
            daily_hours="4",
            target_words="4000",
            work_mode="兼职",
            health_issues="颈椎不适",
            input_ratio="20",
            planning_ratio="30",
            writing_ratio="40",
            review_ratio="10",
        )
        assert "4" in prompt
        assert "4000" in prompt
        assert "兼职" in prompt
        assert "颈椎不适" in prompt
        assert "创作SOP" in prompt

    def test_all_extended6_params_registered(self):
        expected = {
            "compliance_audit": ["compliance_baseline"],
            "platform_optimization": ["platform_baseline"],
            "reader_collab": ["reader_baseline"],
            "ip_derivative": ["ip_baseline"],
            "author_sop": [
                "daily_hours",
                "target_words",
                "work_mode",
                "health_issues",
                "input_ratio",
                "planning_ratio",
                "writing_ratio",
                "review_ratio",
            ],
        }
        for key, params in expected.items():
            assert PROMPT_PARAMS[key] == params

    def test_all_extended6_prompts_registered(self):
        """确保5个新Prompt已在 SOCIETY_PROMPTS 中注册"""
        _lazy_load_extensions()
        expected = {
            "compliance_audit",
            "platform_optimization",
            "reader_collab",
            "ip_derivative",
            "author_sop",
        }
        assert expected.issubset(set(SOCIETY_PROMPTS.keys()))
        for key in expected:
            assert SOCIETY_PROMPTS[key] is not None

    def test_select_model_extended6(self):
        agent = SociologistAgent()
        assert agent._select_model("compliance_audit") == "deepseek-reasoner"
        assert agent._select_model("platform_optimization") == "deepseek-chat"
        assert agent._select_model("reader_collab") == "deepseek-chat"
        assert agent._select_model("ip_derivative") == "deepseek-chat"
        assert agent._select_model("author_sop") == "deepseek-reasoner"


class TestExtended7Prompts:
    """测试第八阶段5个跨题材通用底层维度 Prompt 模板"""

    def test_get_prompt_resource_network(self):
        prompt = get_prompt(
            "resource_network",
            genre_type="赛博朋克",
            core_resource="算力",
            controller="财阀联盟",
            bottom_access="黑市义体",
        )
        assert "赛博朋克" in prompt
        assert "算力" in prompt
        assert "垄断" in prompt

    def test_get_prompt_class_barrier(self):
        prompt = get_prompt(
            "class_barrier",
            genre_type="修仙",
            start_class="外门杂役",
            target_class="核心长老会",
            surface_channel="宗门大比",
        )
        assert "修仙" in prompt
        assert "外门杂役" in prompt
        assert "护城河" in prompt

    def test_get_prompt_info_blackbox(self):
        prompt = get_prompt(
            "info_blackbox",
            genre_type="科幻",
            hidden_truth="人类被圈养",
            control_medium="全息网络",
            info_access="旧日志解密",
        )
        assert "科幻" in prompt
        assert "人类被圈养" in prompt
        assert "先行者" in prompt

    def test_get_prompt_spatial_ecology(self):
        prompt = get_prompt(
            "spatial_ecology",
            genre_type="末世废土",
            core_location="地下避难所",
            spatial_layers="上层军官区/中层平民区/底层锅炉房",
            choke_points="唯一电梯井;水循环中枢",
        )
        assert "末世废土" in prompt
        assert "地下避难所" in prompt
        assert "咽喉要道" in prompt

    def test_get_prompt_moral_dilemma(self):
        prompt = get_prompt(
            "moral_dilemma",
            genre_type="都市商战",
            bond_characters="导师兼投资人",
            final_battle_context="恶意收购决战",
            villain_profile="冷酷投行家",
        )
        assert "都市商战" in prompt
        assert "导师" in prompt
        assert "电车难题" in prompt

    def test_all_extended7_params_registered(self):
        expected = {
            "resource_network": ["genre_type", "core_resource", "controller", "bottom_access"],
            "class_barrier": ["genre_type", "start_class", "target_class", "surface_channel"],
            "info_blackbox": ["genre_type", "hidden_truth", "control_medium", "info_access"],
            "spatial_ecology": ["genre_type", "core_location", "spatial_layers", "choke_points"],
            "moral_dilemma": [
                "genre_type",
                "bond_characters",
                "final_battle_context",
                "villain_profile",
            ],
        }
        for key, params in expected.items():
            assert PROMPT_PARAMS[key] == params

    def test_all_extended7_prompts_registered(self):
        """确保5个新Prompt已在 SOCIETY_PROMPTS 中注册"""
        _lazy_load_extensions()
        expected = {
            "resource_network",
            "class_barrier",
            "info_blackbox",
            "spatial_ecology",
            "moral_dilemma",
        }
        assert expected.issubset(set(SOCIETY_PROMPTS.keys()))
        for key in expected:
            assert SOCIETY_PROMPTS[key] is not None

    def test_select_model_extended7(self):
        agent = SociologistAgent()
        assert agent._select_model("resource_network") == "deepseek-reasoner"
        assert agent._select_model("class_barrier") == "deepseek-chat"
        assert agent._select_model("info_blackbox") == "deepseek-reasoner"
        assert agent._select_model("spatial_ecology") == "deepseek-chat"
        assert agent._select_model("moral_dilemma") == "deepseek-chat"

    @pytest.mark.asyncio
    async def test_deduce_all_includes_extended7(self):
        agent = SociologistAgent()
        with patch.object(agent, "deduce", new_callable=AsyncMock) as mock_deduce:
            mock_deduce.return_value = SocietyResult(
                dimension="test", prompt_used="", model_used="", output="ok"
            )
            # 只需覆盖所有36个维度的参数
            params = {
                "economy_baseline": "x",
                "law_baseline": "x",
                "culture_baseline": "x",
                "custom_baseline": "x",
                "history_baseline": "x",
                "power_baseline": "x",
                "tech_baseline": "x",
                "ecology_baseline": "x",
                "underworld_baseline": "x",
                "philosophy_baseline": "x",
                "admin_baseline": "x",
                "clan_baseline": "x",
                "propaganda_baseline": "x",
                "astronomy_baseline": "x",
                "mobility_baseline": "x",
                "language_baseline": "x",
                "military_baseline": "x",
                "entourage_baseline": "x",
                "population_baseline": "x",
                "inner_court_baseline": "x",
                "medical_baseline": "x",
                "forensic_baseline": "x",
                "cult_baseline": "x",
                "royal_monopoly_baseline": "x",
                "espionage_baseline": "x",
                "diplomacy_baseline": "x",
                "underbelly_baseline": "x",
                "pleasure_baseline": "x",
                "hook_baseline": "x",
                "villain_baseline": "x",
                "author_draft": "x",
                "ai_logic": "x",
                # 第八阶段参数
                "genre_type": "x",
                "core_resource": "x",
                "controller": "x",
                "bottom_access": "x",
                "start_class": "x",
                "target_class": "x",
                "surface_channel": "x",
                "hidden_truth": "x",
                "control_medium": "x",
                "info_access": "x",
                "core_location": "x",
                "spatial_layers": "x",
                "choke_points": "x",
                "bond_characters": "x",
                "final_battle_context": "x",
                "villain_profile": "x",
                # 第七阶段参数
                "compliance_baseline": "x",
                "platform_baseline": "x",
                "reader_baseline": "x",
                "ip_baseline": "x",
                "daily_hours": "x",
                "target_words": "x",
                "work_mode": "x",
                "health_issues": "x",
                "input_ratio": "x",
                "planning_ratio": "x",
                "writing_ratio": "x",
                "review_ratio": "x",
            }
            results = await agent.deduce_all(params)
            assert len(results) == 44
            assert "resource_network" in results
            assert "class_barrier" in results
            assert "info_blackbox" in results
            assert "spatial_ecology" in results
            assert "moral_dilemma" in results


class TestExtended8Prompts:
    """测试第九阶段：连载生存、读者心理与题材创新"""

    def test_extended8_prompts_registered(self):
        _lazy_load_extensions()
        expected = {"serial_crisis", "reader_biochem", "genre_innovation"}
        assert expected.issubset(set(SOCIETY_PROMPTS.keys()))
        for key in expected:
            assert SOCIETY_PROMPTS[key] is not None

    def test_extended8_params_registered(self):
        expected_params = {
            "serial_crisis": ["serial_crisis_baseline"],
            "reader_biochem": ["reader_biochem_baseline"],
            "genre_innovation": ["genre_innovation_baseline"],
        }
        for key, params in expected_params.items():
            assert PROMPT_PARAMS[key] == params

    def test_get_prompt_serial_crisis(self):
        prompt = get_prompt("serial_crisis", serial_crisis_baseline="主角某章节引发读者争议")
        assert "主角某章节引发读者争议" in prompt
        assert "行为动机反转优化" in prompt
        assert "行为代价落地设计" in prompt
        assert "爽点急救注入方案" in prompt

    def test_get_prompt_reader_biochem(self):
        prompt = get_prompt("reader_biochem", reader_biochem_baseline="单卷收尾决战背景")
        assert "单卷收尾决战背景" in prompt
        assert "多巴胺" in prompt
        assert "情绪过山车" in prompt
        assert "生理反应触发点" in prompt
        assert "多巴胺奖励节奏" in prompt

    def test_get_prompt_genre_innovation(self):
        prompt = get_prompt("genre_innovation", genre_innovation_baseline="长生修炼流、规则探秘类")
        assert "长生修炼流" in prompt
        assert "题材缝隙定位分析" in prompt
        assert "类型元素融合方案" in prompt
        assert "创新节奏控制" in prompt

    @pytest.mark.asyncio
    async def test_deduce_all_includes_extended8(self):
        agent = SociologistAgent()
        with patch.object(agent, "deduce", new_callable=AsyncMock) as mock_deduce:
            mock_deduce.return_value = SocietyResult(
                dimension="test", prompt_used="", model_used="", output="ok"
            )
            params = {
                "economy_baseline": "x",
                "law_baseline": "x",
                "culture_baseline": "x",
                "custom_baseline": "x",
                "history_baseline": "x",
                "power_baseline": "x",
                "tech_baseline": "x",
                "ecology_baseline": "x",
                "underworld_baseline": "x",
                "philosophy_baseline": "x",
                "admin_baseline": "x",
                "clan_baseline": "x",
                "propaganda_baseline": "x",
                "astronomy_baseline": "x",
                "mobility_baseline": "x",
                "language_baseline": "x",
                "military_baseline": "x",
                "entourage_baseline": "x",
                "population_baseline": "x",
                "inner_court_baseline": "x",
                "medical_baseline": "x",
                "forensic_baseline": "x",
                "cult_baseline": "x",
                "royal_monopoly_baseline": "x",
                "espionage_baseline": "x",
                "diplomacy_baseline": "x",
                "underbelly_baseline": "x",
                "pleasure_baseline": "x",
                "hook_baseline": "x",
                "villain_baseline": "x",
                "author_draft": "x",
                "ai_logic": "x",
                "genre_type": "x",
                "core_resource": "x",
                "controller": "x",
                "bottom_access": "x",
                "start_class": "x",
                "target_class": "x",
                "surface_channel": "x",
                "hidden_truth": "x",
                "control_medium": "x",
                "info_access": "x",
                "core_location": "x",
                "spatial_layers": "x",
                "choke_points": "x",
                "bond_characters": "x",
                "final_battle_context": "x",
                "villain_profile": "x",
                # 第九阶段参数
                "serial_crisis_baseline": "x",
                "reader_biochem_baseline": "x",
                "genre_innovation_baseline": "x",
                # 第七阶段参数
                "compliance_baseline": "x",
                "platform_baseline": "x",
                "reader_baseline": "x",
                "ip_baseline": "x",
                "daily_hours": "x",
                "target_words": "x",
                "work_mode": "x",
                "health_issues": "x",
                "input_ratio": "x",
                "planning_ratio": "x",
                "writing_ratio": "x",
                "review_ratio": "x",
            }
            results = await agent.deduce_all(params)
            assert len(results) == 44
            assert "serial_crisis" in results
            assert "reader_biochem" in results
            assert "genre_innovation" in results
