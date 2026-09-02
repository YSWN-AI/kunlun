"""
pytest 全局配置
"""

import os
import sys
from pathlib import Path

import pytest

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """测试启动前：禁用速率限制，避免 TestClient 触发 slowapi 异常"""
    os.environ.setdefault("KUNLUN_RATE_LIMIT_PER_MINUTE", "0")
    from kunlun.config import settings

    settings.rate_limit_per_minute = 0
    settings.rate_limit_generate_per_minute = 999
    settings.rate_limit_export_per_minute = 999


@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试后重置单例状态"""
    yield
    # 重置 KGClient 单例
    import kunlun.kg.client as kg_mod

    if hasattr(kg_mod, "kg_client"):
        kg_mod.kg_client = kg_mod.KGClient()

    # 重置 Embedder 单例
    import kunlun.kg.embedder as emb_mod
    from kunlun.kg.embedder import _embedding_cache

    if hasattr(emb_mod, "_embedder_instance"):
        emb_mod._embedder_instance = None
    if hasattr(emb_mod, "_embedding_cache"):
        _embedding_cache.clear()

    # 重置 GachaEngine 单例
    import kunlun.gacha.engine as gacha_mod

    if hasattr(gacha_mod, "GachaEngine"):
        gacha_mod.GachaEngine._instance = None
        if hasattr(gacha_mod, "gacha_engine"):
            gacha_mod.gacha_engine = gacha_mod.GachaEngine()

    # 重置 TokenTracker 单例
    import kunlun.token_tracker as tt_mod

    if hasattr(tt_mod, "token_tracker"):
        tt_mod.token_tracker = tt_mod.TokenTracker()

    # 重置 ModelRouter 单例
    try:
        import kunlun.model_router as mr_mod

        if hasattr(mr_mod, "model_router") and hasattr(mr_mod, "ModelRouter"):
            mr_mod.model_router = mr_mod.ModelRouter()
    except Exception:
        pass

    # 重置 ICUSystem 单例
    try:
        import kunlun.audit.icu as icu_mod

        if hasattr(icu_mod, "icu_system") and hasattr(icu_mod, "ICUSystem"):
            icu_mod.icu_system = icu_mod.ICUSystem()
    except Exception:
        pass

    # 重置 SkillLoader 单例
    try:
        import kunlun.skills.loader as sl_mod

        if hasattr(sl_mod, "skill_loader") and hasattr(sl_mod, "SkillLoader"):
            sl_mod.skill_loader = sl_mod.SkillLoader()
            if hasattr(sl_mod, "_loaded"):
                sl_mod._loaded = False
            if hasattr(sl_mod, "_cache"):
                sl_mod._cache = {}
    except Exception:
        pass

    # 重置 ConflictManager 单例缓存并清理持久化数据
    try:
        import shutil

        import kunlun.conflict.engine as ce_mod

        if hasattr(ce_mod, "_conflict_managers"):
            ce_mod._conflict_managers.clear()
        # 清理冲突持久化目录，避免测试间数据污染
        from kunlun.config import settings

        conflict_dir = settings.DATA_DIR / "conflict"
        if conflict_dir.exists():
            for item in conflict_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
    except Exception:
        pass

    # 重置 TextRefiner 单例
    try:
        import kunlun.style.refiner as ref_mod

        if hasattr(ref_mod, "text_refiner") and hasattr(ref_mod, "TextRefiner"):
            ref_mod.text_refiner = ref_mod.TextRefiner()
    except Exception:
        pass

    # 重置 QualityDashboard 单例
    try:
        import kunlun.quality.dashboard as qd_mod

        if hasattr(qd_mod, "quality_dashboard") and hasattr(qd_mod, "QualityDashboard"):
            qd_mod.quality_dashboard = qd_mod.QualityDashboard()
    except Exception:
        pass

    # 重置 VibeEngine 单例缓存
    try:
        import kunlun.style.vibe as vibe_mod

        if hasattr(vibe_mod, "_engines"):
            vibe_mod._engines.clear()
    except Exception:
        pass

    # 重置 OutputContractValidator 单例
    try:
        import kunlun.audit.output_contract as oc_mod

        if hasattr(oc_mod, "output_contract") and hasattr(oc_mod, "OutputContractValidator"):
            oc_mod.output_contract = oc_mod.OutputContractValidator()
    except Exception:
        pass

    # 重置 Settings 单例
    try:
        import kunlun.config as config_mod

        if hasattr(config_mod, "_reset_settings"):
            config_mod._reset_settings()
    except Exception:
        pass

    # 重置 LayerRuleEngine 单例
    try:
        from kunlun.rules.layers import reset_layer_engine

        reset_layer_engine()
    except Exception:
        pass
