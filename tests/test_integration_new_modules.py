"""新模块集成测试"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.audit.ai_features import calculate_ai_score
from kunlun.audit.output_contract import OutputContractValidator
from kunlun.audit.post_write_validator import PostWriteValidator
from kunlun.context.budget import ContextBudgetAllocator
from kunlun.gacha.param_variator import ParamVariator
from kunlun.style.refiner import TextRefiner


class TestNewModulesIntegration:
    def test_ai_features_detect_ai_text(self):
        ai_text = (
            "首先，值得注意的是，从某种意义上来说，"
            "综上所述，我们确实需要仔细思考这个问题。"
            * 20
            + "换句话说，这个故事具有一定的复杂性。" * 20
        )
        score = calculate_ai_score(ai_text)
        assert score < 0.5

    def test_refine_then_validate(self):
        refiner = TextRefiner()
        validator = PostWriteValidator()
        refined, rpt = refiner.refine("他淡淡地说：“好的。”")
        assert rpt.total_fixes >= 1
        v_report = validator.validate(refined)
        assert v_report.overall_score >= 0

    def test_context_budget(self):
        allocator = ContextBudgetAllocator(total_budget=5000)
        result = allocator.assemble({"current_draft": "测试。" * 200})
        assert len(result["current_draft"]) <= 5000

    def test_param_variator(self):
        variator = ParamVariator()
        for ch in range(1, 6):
            params = variator.get_params("writer", chapter=ch)
            assert 0.1 <= params.temperature <= 1.5

    def test_output_contract(self):
        v = OutputContractValidator()
        r = v.validate(
            "chapter_summary",
            {
                "chapter": 1,
                "title": "T",
                "summary": "S" * 10,
                "characters": ["a"],
                "key_events": ["b"],
            },
        )
        assert r.valid

    def test_all_modules_importable(self):
        for mod in [
            "kunlun.audit.post_write_validator",
            "kunlun.audit.ai_features",
            "kunlun.audit.output_contract",
            "kunlun.context.budget",
            "kunlun.style.refiner",
            "kunlun.gacha.param_variator",
            "kunlun.core.extension_base",
        ]:
            __import__(mod)
