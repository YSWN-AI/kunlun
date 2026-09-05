"""
边际收益优化 — 综合验证测试

测试覆盖：
  1. 边际收益分析器正确性
  2. 优化指令生成逻辑
  3. 监控引擎边界条件
  4. 低效边界模块清理效果
  5. 日志体系统一
  6. 异常透明度改善
  7. 路由双轨注册
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kunlun.marginal_efficiency import (  # noqa: E402
    MarginalEfficiencyAnalyzer,
    ModuleTier,
    OptimizationAction,
    OptimizationMetrics,
    OptimizationMonitor,
)


class TestMarginalEfficiencyAnalyzer:
    """边际收益分析器测试"""

    def test_register_and_calculate_roi(self):
        """测试模块注册和ROI计算"""
        analyzer = MarginalEfficiencyAnalyzer()

        # 高ROI核心模块
        metric = analyzer.register_module(
            "test_core",
            ModuleTier.CORE,
            code_lines=300,
            complexity_score=30,
            maintenance_burden=10,
            runtime_overhead_ms=50,
            dependency_count=3,
            usage_frequency=0.95,
            quality_contribution=90,
            test_coverage=80,
            bug_surface_area=5,
        )
        assert metric.roi_score > 1.0, f"Core module should have high ROI, got {metric.roi_score}"
        assert not metric.is_low_efficiency_boundary

    def test_low_efficiency_detection(self):
        """测试低效边界检测"""
        analyzer = MarginalEfficiencyAnalyzer()

        # 低效外围模块（高维护负担，低质量贡献）
        metric = analyzer.register_module(
            "test_peripheral",
            ModuleTier.PERIPHERAL,
            code_lines=20,
            complexity_score=5,
            maintenance_burden=60,
            runtime_overhead_ms=2,
            dependency_count=1,
            usage_frequency=0.05,
            quality_contribution=5,
            test_coverage=10,
            bug_surface_area=2,
        )
        assert metric.roi_score < 1.0

    def test_roi_threshold_boundary(self):
        """测试ROI阈值边界"""
        analyzer = MarginalEfficiencyAnalyzer()

        # 正好在阈值边界
        metric = analyzer.register_module(
            "test_boundary",
            ModuleTier.SUPPORT,
            code_lines=500,
            complexity_score=70,
            maintenance_burden=50,
            runtime_overhead_ms=300,
            dependency_count=8,
            usage_frequency=0.4,
            quality_contribution=40,
            test_coverage=20,
            bug_surface_area=30,
        )
        # ROI应该在中等范围
        assert 0.1 <= metric.roi_score <= 5.0

    def test_generate_directives_for_large_file(self):
        """测试大文件+低ROI的优化指令生成"""
        analyzer = MarginalEfficiencyAnalyzer()

        analyzer.register_module(
            "test_large_low_roi",
            ModuleTier.CORE,
            code_lines=2000,
            complexity_score=85,
            maintenance_burden=70,
            runtime_overhead_ms=1000,
            dependency_count=15,
            usage_frequency=0.9,
            quality_contribution=30,
            test_coverage=5,
            bug_surface_area=60,
        )
        directives = analyzer.analyze()
        assert len(directives) > 0
        assert any(d.action == OptimizationAction.SIMPLIFY for d in directives)

    def test_generate_directives_for_high_maintenance_low_quality(self):
        """测试高维护负担+低质量贡献的降级指令"""
        analyzer = MarginalEfficiencyAnalyzer()

        analyzer.register_module(
            "test_high_burden",
            ModuleTier.PERIPHERAL,
            code_lines=200,
            complexity_score=40,
            maintenance_burden=75,
            runtime_overhead_ms=100,
            dependency_count=3,
            usage_frequency=0.1,
            quality_contribution=10,
            test_coverage=0,
            bug_surface_area=40,
        )
        directives = analyzer.analyze()
        removal_directives = [d for d in directives if d.action == OptimizationAction.REMOVE]
        assert len(removal_directives) > 0, "Peripheral high-burden module should be removed"

    def test_reallocation_logic(self):
        """测试资源重分配逻辑"""
        analyzer = MarginalEfficiencyAnalyzer()

        # 低效模块
        analyzer.register_module(
            "low_efficiency",
            ModuleTier.PERIPHERAL,
            code_lines=500,
            complexity_score=50,
            maintenance_burden=60,
            runtime_overhead_ms=200,
            dependency_count=4,
            usage_frequency=0.2,
            quality_contribution=15,
            test_coverage=0,
            bug_surface_area=30,
        )
        # 高ROI核心
        analyzer.register_module(
            "high_roi_core",
            ModuleTier.CORE,
            code_lines=300,
            complexity_score=30,
            maintenance_burden=10,
            runtime_overhead_ms=50,
            dependency_count=3,
            usage_frequency=0.95,
            quality_contribution=90,
            test_coverage=80,
            bug_surface_area=5,
        )

        reallocations = analyzer.generate_reallocation(["low_efficiency"])
        assert len(reallocations) > 0
        assert reallocations[0].from_module == "low_efficiency"
        assert reallocations[0].to_module == "high_roi_core"

    def test_kunlun_analyzer(self):
        """测试预配置的昆仑项目分析器"""
        # 使用独立实例避免全局单例状态污染
        from kunlun.marginal_efficiency import create_kunlun_analyzer

        analyzer = create_kunlun_analyzer()
        report = analyzer.generate_report()
        assert report.modules_analyzed >= 10
        assert len(report.low_efficiency_modules) >= 2
        assert len(report.directives) > 0
        assert report.total_lines_saved > 0


class TestOptimizationMonitor:
    """优化监控器测试"""

    def test_baseline_and_snapshot(self):
        """测试基线和快照记录"""
        monitor = OptimizationMonitor()

        baseline = OptimizationMetrics(
            total_lines=30000,
            dead_code_lines=500,
            duplicate_lines=300,
            swallowed_exceptions=8,
            todo_count=5,
            avg_roi=1.2,
            low_efficiency_ratio=0.15,
        )
        monitor.set_baseline(baseline)

        # 优化后
        improved = OptimizationMetrics(
            total_lines=29000,
            dead_code_lines=300,
            duplicate_lines=200,
            swallowed_exceptions=2,
            todo_count=3,
            avg_roi=1.5,
            low_efficiency_ratio=0.08,
        )
        delta = monitor.record_snapshot(improved)

        assert delta["lines_reduced"] == 1000
        assert delta["dead_code_reduced"] == 200
        assert abs(delta["roi_change"] - 0.3) < 0.001
        assert abs(delta["low_efficiency_change"] - 0.07) < 0.001

    def test_should_stop_optimization_no_history(self):
        """测试无历史时不停止优化"""
        monitor = OptimizationMonitor()
        assert not monitor.should_stop_optimization("test_module")

    def test_should_stop_optimization_with_data(self):
        """测试边际收益耗尽时停止"""
        monitor = OptimizationMonitor()

        # 连续3轮几乎无变化的ROI
        for i in range(4):
            m = OptimizationMetrics(
                total_lines=30000 - i * 10,
                avg_roi=1.5 + i * 0.001,  # 几乎无变化
                low_efficiency_ratio=0.1,
            )
            monitor.record_snapshot(m)

        assert monitor.should_stop_optimization("test_module")

    def test_health_summary(self):
        """测试健康摘要"""
        monitor = OptimizationMonitor()

        monitor.set_baseline(
            OptimizationMetrics(
                total_lines=30000,
                dead_code_lines=500,
                avg_roi=1.2,
                low_efficiency_ratio=0.15,
            )
        )

        health = monitor.get_health_summary()
        assert health["status"] in ("healthy", "needs_optimization")
        assert "cer" in health
        assert "roi" in health

    def test_save_and_persistence(self):
        """测试监控数据持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "test_history.json"
            monitor = OptimizationMonitor(history_path=history_path)

            monitor.set_baseline(
                OptimizationMetrics(
                    total_lines=1000,
                    avg_roi=1.0,
                    low_efficiency_ratio=0.1,
                )
            )
            monitor.save()

            assert history_path.exists()
            data = json.loads(history_path.read_text(encoding="utf-8"))
            assert data["baseline"]["total_lines"] == 1000
            assert len(data["history"]) == 1


class TestModuleTierAndAction:
    """枚举和常量测试"""

    def test_module_tier_values(self):
        assert ModuleTier.CORE.value == "core"
        assert ModuleTier.SUPPORT.value == "support"
        assert ModuleTier.PERIPHERAL.value == "peripheral"

    def test_optimization_action_values(self):
        assert OptimizationAction.REMOVE.value == "remove"
        assert OptimizationAction.MERGE.value == "merge"
        assert OptimizationAction.SIMPLIFY.value == "simplify"
        assert OptimizationAction.LAZY_LOAD.value == "lazy_load"


class TestPostOptimizationValidation:
    """优化后验证测试 — 确保核心功能不受影响"""

    def test_kg_repositories_still_importable(self):
        """KG仓储层仍可导入（日志体系统一后）"""
        from kunlun.kg.repositories.neo4j_repo import Neo4jGraphRepository
        from kunlun.kg.repositories.qdrant_repo import QdrantVectorRepository
        from kunlun.kg.repositories.sqlite_fts import SQLiteFTSRepository
        from kunlun.kg.repositories.sqlite_graph import SQLiteGraphRepository

        assert SQLiteGraphRepository is not None
        assert SQLiteFTSRepository is not None
        assert QdrantVectorRepository is not None
        assert Neo4jGraphRepository is not None

    def test_style_engineer_direct_import(self):
        """StyleEngineer可直接从 kunlun.style.engineer 导入"""
        from kunlun.style.engineer import StyleEngineer

        assert StyleEngineer is not None
        assert StyleEngineer.agent_name == "style_engineer"

    def test_style_engineer_forwarding_deleted(self):
        """纯转发文件已删除"""
        forwarding_path = Path(__file__).parent.parent / "kunlun" / "agents" / "style_engineer.py"
        assert not forwarding_path.exists(), "Pure forwarding layer should be removed"

    def test_marginal_api_routes(self):
        """边际收益API路由可导入"""
        from kunlun.api.routers.marginal_efficiency import router

        routes = [r.path for r in router.routes]
        assert "/marginal-efficiency/report" in routes
        assert "/marginal-efficiency/health" in routes
        assert "/marginal-efficiency/analyze" in routes
        assert "/marginal-efficiency/history" in routes

    def test_no_silent_exceptions_in_pipeline_steps(self):
        """验证管线步骤不再静默吞异常 (_record_step已移除,步骤类自行管理)"""
        import inspect

        from kunlun.pipeline.steps._base import BaseStep

        source = inspect.getsource(BaseStep.execute)
        assert "logger.debug" in source or "logger.warning" in source or "logger.error" in source
        assert "except Exception as e:" not in source or "logger" in source
