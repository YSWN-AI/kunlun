"""
测试: GachaEngine 抽卡引擎
"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.gacha.engine import DEFAULT_MODELS, GachaEngine


class TestGachaScoring:
    """评分体系"""

    def test_score_returns_float(self):
        engine = GachaEngine()
        score = engine._score_text("这是一个测试文本段落。包含一些内容用于评分验证。")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_score_empty_text(self):
        engine = GachaEngine()
        score = engine._score_text("")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_score_short_text(self):
        engine = GachaEngine()
        score = engine._score_text("短。")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_humanness_scoring(self):
        engine = GachaEngine()
        ai_text = "然而，他意识到这一点的同时，此外还面临着多重挑战。因此，他采取了行动。"
        human_text = "他蹲下。手触电门。火花。他看着冒烟的手指，吹了吹。"

        score_ai = engine._score_humanness(ai_text)
        score_human = engine._score_humanness(human_text)
        assert 0.0 <= score_ai <= 1.0
        assert 0.0 <= score_human <= 1.0

    def test_all_score_dims(self):
        engine = GachaEngine()
        text = "测试文本。" * 10
        for method_name in [
            "_score_diversity", "_score_coherence", "_score_info_density",
            "_score_emotion", "_score_rhythm", "_score_novelty",
            "_score_fluency", "_score_completeness", "_score_humanness",
        ]:
            score = getattr(engine, method_name)(text)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0


class TestGachaGenerate:
    """生成流程"""

    @pytest.mark.asyncio
    async def test_generate_mock(self):
        engine = GachaEngine()
        result = await engine.generate(
            prompt="写一段武侠小说的开头，200字左右。",
            mode="gacha_cascade",
        )
        assert "best_text" in result
        assert "best_model" in result
        assert "best_score" in result

    @pytest.mark.asyncio
    async def test_generate_single_fix(self):
        engine = GachaEngine()
        result = await engine.generate(
            prompt="修复这段文本中的语法错误。",
            mode="single_fix",
        )
        assert "best_text" in result
        assert result["best_model"] in ("deepseek-chat", "gpt-4o-mini", "")

    @pytest.mark.asyncio
    async def test_generate_cascade(self):
        engine = GachaEngine()
        result = await engine.generate(
            prompt="测试prompt",
            mode="gacha_cascade",
        )
        assert "best_text" in result
        assert "candidates" in result

    @pytest.mark.asyncio
    async def test_generate_ultimate(self):
        engine = GachaEngine()
        result = await engine.generate(
            prompt="写一段玄幻小说，300字。\n\n段落1: 测试\n\n段落2: 测试\n\n段落3: 测试",
            mode="gacha_cascade",
            chapter_type="opening",
        )
        assert "best_text" in result


class TestGachaEdgeCases:
    """边界情况"""

    def test_default_models_structure(self):
        assert isinstance(DEFAULT_MODELS, list)
        for model in DEFAULT_MODELS:
            assert "provider" in model
            assert "model" in model

    def test_ngrams(self):
        result = GachaEngine.ngrams("abcde", 2)
        assert "ab" in result
        assert "bc" in result
        assert len(result) == 4

    def test_get_cascade_threshold(self):
        engine = GachaEngine()
        threshold = engine.get_cascade_threshold("normal")
        assert "min_candidates" in threshold
        assert "min_score" in threshold

    def test_last_best_model(self):
        engine = GachaEngine()
        engine.last_best_model = "test-model"
        assert engine.last_best_model == "test-model"
