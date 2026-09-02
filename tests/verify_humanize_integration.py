"""
Humanize 模块集成验证 — 标准 pytest 测试
验证：包导入、引擎方法、Gacha集成、API路由、配置项
"""


class TestHumanizeIntegration:
    """Humanize 完整集成"""

    def test_package_import(self):
        from kunlun import humanize
        assert humanize is not None

    def test_engine_methods_exist(self):
        from kunlun.humanize import humanize_engine
        assert hasattr(humanize_engine, 'detect'), "缺少 detect 方法"
        assert hasattr(humanize_engine, 'humanize'), "缺少 humanize 方法"
        assert hasattr(humanize_engine, 'quick_process'), "缺少 quick_process 方法"

    def test_gacha_integration(self):
        """GachaEngine.generate 应接受 humanize 参数"""
        import inspect

        from kunlun.gacha.engine import gacha_engine
        sig = inspect.signature(gacha_engine.generate)
        params = list(sig.parameters.keys())
        assert 'humanize' in params, f"generate 缺少 humanize 参数: {params}"

    def test_api_routes_registered(self):
        """Humanize 路由已注册到 api_router"""
        from kunlun.api.routers import api_router
        routes = [r.path for r in api_router.routes]
        humanize_routes = [r for r in routes if "humanize" in r]
        assert len(humanize_routes) > 0, "Humanize API 路由未注册"

    def test_config_enabled(self):
        from kunlun.config import settings
        assert hasattr(settings, 'humanize_enabled')
        assert hasattr(settings, 'humanize_default_strategy')

    def test_detector_returns_risk(self):
        from kunlun.humanize import anti_ai_detector
        result = anti_ai_detector.detect("测试文本")
        assert isinstance(result, dict)
        assert 'risk_level' in result
