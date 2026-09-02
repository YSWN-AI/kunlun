"""
昆仑创作引擎 — 边际收益优化引擎

基于边界效应理论（边际收益递减规律）的代码与架构优化框架。
核心理念：识别"低效边界"模块——即继续增加资源或优化努力已无法带来显著质量提升的区域，
将资源精准转移到高收益核心模块，实现降本增效。

设计原则：
  1. 量化每个模块的投入产出比（ROI）
  2. 识别边际收益 < 阈值的低效边界
  3. 提供自动化资源重分配策略
  4. 持续监控优化效果
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger

from kunlun.common.json_store import save_json

# ═══════════════════════════════════════════════════════════════════
# 核心数据模型
# ═══════════════════════════════════════════════════════════════════


class ModuleTier(Enum):
    """模块分层"""

    CORE = "core"  # 核心：必须维持高质量
    SUPPORT = "support"  # 支撑：中等优先级
    PERIPHERAL = "peripheral"  # 外围：可降级


class OptimizationAction(Enum):
    """优化动作类型"""

    REMOVE = "remove"  # 删除冗余代码
    MERGE = "merge"  # 合并重复逻辑
    SIMPLIFY = "simplify"  # 简化过度设计
    LAZY_LOAD = "lazy_load"  # 延迟加载
    CACHE = "cache"  # 缓存高频数据
    BATCH = "batch"  # 批量化处理
    DEMOTE = "demote"  # 降级（从核心→外围）


@dataclass
class ModuleMetric:
    """模块度量指标 — 量化投入产出比"""

    module_name: str
    tier: ModuleTier = ModuleTier.SUPPORT

    # --- 投入指标（成本） ---
    code_lines: int = 0  # 代码行数
    complexity_score: float = 0.0  # 圈复杂度（0-100）
    maintenance_burden: float = 0.0  # 维护负担（TODO数量/重复率/异常吞咽等）
    runtime_overhead_ms: float = 0.0  # 平均运行开销（毫秒）
    dependency_count: int = 0  # 被依赖模块数

    # --- 产出指标（收益） ---
    usage_frequency: float = 0.0  # 使用频率（0-1）
    quality_contribution: float = 0.0  # 对核心质量贡献（0-100）
    test_coverage: float = 0.0  # 测试覆盖率（0-100）
    bug_surface_area: float = 0.0  # 缺陷面（越低越好，0-100）

    # --- 衍生指标 ---
    roi_score: float = 0.0  # 综合投入产出比（越高越好）
    marginal_efficiency: float = 0.0  # 边际效率（当前优化轮次的ROI变化率）
    optimization_round: int = 0  # 当前优化轮次
    is_low_efficiency_boundary: bool = False  # 是否为低效边界


@dataclass
class OptimizationDirective:
    """优化指令 — 具体的重构建议"""

    module_name: str
    action: OptimizationAction
    target: str  # 目标代码位置（函数名/文件名）
    reason: str  # 原因说明
    expected_saving_lines: int = 0  # 预期节省代码行数
    expected_saving_ms: float = 0.0  # 预期节省运行时间（ms）
    priority: int = 5  # 优先级 1-10（10最高）


@dataclass
class ResourceReallocation:
    """资源重分配方案 — 从低效→高收益"""

    from_module: str
    to_module: str
    resource_type: str  # "code_lines" | "test_budget" | "maintenance_time"
    amount: int
    expected_roi_gain: float  # 预期ROI增益


@dataclass
class OptimizationReport:
    """优化报告"""

    round_number: int
    modules_analyzed: int
    low_efficiency_modules: list[str]
    directives: list[OptimizationDirective]
    reallocations: list[ResourceReallocation]
    total_lines_saved: int
    total_ms_saved: float
    overall_roi_improvement: float
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════
# 边际收益分析引擎
# ═══════════════════════════════════════════════════════════════════


class MarginalEfficiencyAnalyzer:
    """边际收益分析器 — 识别低效边界模块

    基于边界效应理论：
      - 初始阶段：投入增加 → 质量快速提升（高边际收益）
      - 拐点之后：投入增加 → 质量缓慢提升（低边际收益）
      - 边界之后：投入增加 → 质量几乎不变（负边际收益）

    识别策略：
      1. 计算每个模块的 ROI（产出/投入）
      2. 计算边际 ROI（ΔROI/Δ投入）
      3. 标记边际 ROI < 阈值的模块为低效边界
    """

    # 阈值配置
    ROI_LOW_THRESHOLD: ClassVar[float] = 0.3  # ROI低于此值视为低效
    MARGINAL_ROI_THRESHOLD: ClassVar[float] = 0.05  # 边际ROI低于此值视为边界
    COMPLEXITY_HIGH_THRESHOLD: ClassVar[float] = 70.0  # 高复杂度阈值
    MAINTENANCE_BURDEN_HIGH: ClassVar[float] = 50.0  # 高维护负担阈值
    CODE_LINES_LARGE: ClassVar[int] = 500  # 大文件阈值

    def __init__(self) -> None:
        self._module_metrics: dict[str, ModuleMetric] = {}
        self._optimization_history: list[OptimizationReport] = []

    def register_module(
        self,
        name: str,
        tier: ModuleTier,
        code_lines: int,
        complexity_score: float = 0.0,
        maintenance_burden: float = 0.0,
        runtime_overhead_ms: float = 0.0,
        dependency_count: int = 0,
        usage_frequency: float = 0.0,
        quality_contribution: float = 0.0,
        test_coverage: float = 0.0,
        bug_surface_area: float = 0.0,
    ) -> ModuleMetric:
        """注册模块并计算ROI"""
        metric = ModuleMetric(
            module_name=name,
            tier=tier,
            code_lines=code_lines,
            complexity_score=complexity_score,
            maintenance_burden=maintenance_burden,
            runtime_overhead_ms=runtime_overhead_ms,
            dependency_count=dependency_count,
            usage_frequency=usage_frequency,
            quality_contribution=quality_contribution,
            test_coverage=test_coverage,
            bug_surface_area=bug_surface_area,
        )
        metric.roi_score = self._calculate_roi(metric)
        self._module_metrics[name] = metric
        return metric

    def _calculate_roi(self, m: ModuleMetric) -> float:
        """计算综合ROI分数

        产出维度（加权）：
          - 质量贡献 (weight: 0.40)
          - 使用频率 (weight: 0.25)
          - 测试覆盖率 (weight: 0.20)
          - 低缺陷面 (weight: 0.15，取反）

        投入维度（加权）：
          - 代码复杂度 (weight: 0.35)
          - 维护负担 (weight: 0.30)
          - 运行开销 (weight: 0.20)
          - 依赖数 (weight: 0.15)

        ROI = 加权产出 / 加权投入（均归一化到0-1）
        """
        # 产出（越高越好）
        output = (
            0.40 * (m.quality_contribution / 100.0)
            + 0.25 * m.usage_frequency
            + 0.20 * (m.test_coverage / 100.0)
            + 0.15 * max(0, (100 - m.bug_surface_area) / 100.0)
        )

        # 投入（越低越好，取反）
        input_normalized = (
            0.35 * (m.complexity_score / 100.0)
            + 0.30 * (m.maintenance_burden / 100.0)
            + 0.20 * min(1.0, m.runtime_overhead_ms / 500.0)
            + 0.15 * min(1.0, m.dependency_count / 20.0)
        )

        if input_normalized < 0.01:
            return output * 10  # 近乎零投入 → 高ROI

        return output / max(input_normalized, 0.001)

    def analyze(self) -> list[OptimizationDirective]:
        """分析所有模块，生成优化指令"""
        directives: list[OptimizationDirective] = []

        for name, metric in self._module_metrics.items():
            # 计算边际效率（与上一轮的ROI差值）
            if name in self._module_metrics and metric.optimization_round > 0:
                prev = self._module_metrics.get(f"{name}_prev")
                if prev and prev.roi_score > 0:
                    metric.marginal_efficiency = (
                        metric.roi_score - prev.roi_score
                    ) / prev.roi_score

            # 判断是否为低效边界
            metric.is_low_efficiency_boundary = metric.roi_score < self.ROI_LOW_THRESHOLD or (
                metric.marginal_efficiency < self.MARGINAL_ROI_THRESHOLD
                and metric.marginal_efficiency >= 0
            )

            if not metric.is_low_efficiency_boundary:
                continue

            # 生成具体优化指令
            directives.extend(self._generate_directives(name, metric))

        # 按优先级排序
        directives.sort(key=lambda d: d.priority, reverse=True)
        return directives

    def _generate_directives(self, name: str, m: ModuleMetric) -> list[OptimizationDirective]:
        """根据模块特征生成针对性优化指令"""
        directives: list[OptimizationDirective] = []

        # 大文件 + 低ROI → 拆分/精简
        if m.code_lines > self.CODE_LINES_LARGE and m.roi_score < 0.5:
            directives.append(
                OptimizationDirective(
                    module_name=name,
                    action=OptimizationAction.SIMPLIFY,
                    target=f"{name}: 超大函数拆分",
                    reason=f"代码行数{m.code_lines}行，ROI仅{m.roi_score:.2f}，需拆分精简",
                    expected_saving_lines=max(100, m.code_lines // 4),
                    priority=9,
                )
            )

        # 高维护负担 + 低质量贡献 → 降级或移除
        if m.maintenance_burden > self.MAINTENANCE_BURDEN_HIGH and m.quality_contribution < 30:
            if m.tier == ModuleTier.PERIPHERAL:
                directives.append(
                    OptimizationDirective(
                        module_name=name,
                        action=OptimizationAction.REMOVE,
                        target=name,
                        reason=f"维护负担{m.maintenance_burden:.0f}但质量贡献仅{m.quality_contribution:.0f}，建议移除",
                        expected_saving_lines=m.code_lines,
                        priority=8,
                    )
                )
            else:
                directives.append(
                    OptimizationDirective(
                        module_name=name,
                        action=OptimizationAction.DEMOTE,
                        target=name,
                        reason="高维护负担低质量贡献，建议降级处理",
                        priority=7,
                    )
                )

        # 高复杂度 + 低测试覆盖 → 存在质量债务
        if m.complexity_score > self.COMPLEXITY_HIGH_THRESHOLD and m.test_coverage < 30:
            directives.append(
                OptimizationDirective(
                    module_name=name,
                    action=OptimizationAction.SIMPLIFY,
                    target=f"{name}: 降低复杂度+补充测试",
                    reason=f"复杂度{m.complexity_score:.0f}，测试覆盖仅{m.test_coverage:.0f}%",
                    priority=6,
                )
            )

        # 低使用频率 + 外围模块 → 延迟加载
        if m.usage_frequency < 0.2 and m.tier == ModuleTier.PERIPHERAL:
            directives.append(
                OptimizationDirective(
                    module_name=name,
                    action=OptimizationAction.LAZY_LOAD,
                    target=f"{name}: 延迟导入",
                    reason=f"使用频率仅{m.usage_frequency:.1%}，建议延迟加载",
                    expected_saving_ms=m.runtime_overhead_ms * 0.5,
                    priority=5,
                )
            )

        return directives

    def generate_reallocation(
        self, low_efficiency_modules: list[str]
    ) -> list[ResourceReallocation]:
        """生成资源重分配方案：从低效模块转移到高收益核心"""
        reallocations: list[ResourceReallocation] = []

        # 找到高收益核心模块（ROI > 2.0）
        high_roi_cores = [
            (name, m)
            for name, m in self._module_metrics.items()
            if m.tier == ModuleTier.CORE and m.roi_score > 2.0
        ]
        high_roi_cores.sort(key=lambda x: x[1].roi_score, reverse=True)

        if not high_roi_cores:
            return reallocations

        for low_name in low_efficiency_modules:
            low_m = self._module_metrics.get(low_name)
            if not low_m or low_m.code_lines < 50:
                continue

            # 将低效模块50%的资源重新分配给最高ROI的核心模块
            target = high_roi_cores[0]
            saved_lines = low_m.code_lines // 2

            reallocations.append(
                ResourceReallocation(
                    from_module=low_name,
                    to_module=target[0],
                    resource_type="code_lines",
                    amount=saved_lines,
                    expected_roi_gain=(target[1].roi_score - low_m.roi_score)
                    * (saved_lines / max(low_m.code_lines, 1)),
                )
            )

        return reallocations

    def generate_report(self) -> OptimizationReport:
        """生成完整优化报告"""
        directives = self.analyze()
        low_efficiency = [
            name for name, m in self._module_metrics.items() if m.is_low_efficiency_boundary
        ]

        reallocations = self.generate_reallocation(low_efficiency)

        total_lines_saved = sum(d.expected_saving_lines for d in directives)
        total_ms_saved = sum(d.expected_saving_ms for d in directives)

        # 预期改善（保守估计）
        overall_improvement = min(0.3, len(low_efficiency) * 0.05)  # 每个低效模块移除最多改善5%

        report = OptimizationReport(
            round_number=len(self._optimization_history) + 1,
            modules_analyzed=len(self._module_metrics),
            low_efficiency_modules=low_efficiency,
            directives=directives,
            reallocations=reallocations,
            total_lines_saved=total_lines_saved,
            total_ms_saved=total_ms_saved,
            overall_roi_improvement=overall_improvement,
        )
        self._optimization_history.append(report)
        return report


# ═══════════════════════════════════════════════════════════════════
# 优化效果监控器
# ═══════════════════════════════════════════════════════════════════


@dataclass
class OptimizationMetrics:
    """运行时优化指标"""

    # 代码质量
    total_lines: int = 0
    dead_code_lines: int = 0  # 死代码行数
    duplicate_lines: int = 0  # 重复代码行数
    swallowed_exceptions: int = 0  # 静默吞异常数量
    todo_count: int = 0  # TODO数量

    # 性能
    avg_import_time_ms: float = 0.0  # 平均导入时间
    avg_api_response_ms: float = 0.0  # 平均API响应时间
    peak_memory_mb: float = 0.0  # 峰值内存

    # 架构
    module_count: int = 0  # 模块总数
    high_coupling_pairs: int = 0  # 高耦合模块对
    circular_deps: int = 0  # 循环依赖数

    # ROI
    avg_roi: float = 0.0
    low_efficiency_ratio: float = 0.0  # 低效模块占比


class OptimizationMonitor:
    """优化效果持续监控器

    关键指标（KPI）：
      1. 代码效率比 (CER) = 核心功能行 / 总代码行
      2. 异常透明度 (ETI) = 非静默异常 / 总异常
      3. 模块ROI中位数
      4. 低效模块占比
      5. 边际收益斜率（连续3轮优化后的ROI变化率）
    """

    def __init__(self, history_path: Path | None = None) -> None:
        self._history: list[OptimizationMetrics] = []
        self._history_path = history_path or Path("data/optimization_history.json")
        self._baseline: OptimizationMetrics | None = None

    def set_baseline(self, metrics: OptimizationMetrics) -> None:
        """设置基线指标（优化前状态）"""
        self._baseline = metrics
        self._history.append(metrics)
        logger.info(
            f"[边际收益监控] 基线已设置: "
            f"总行数={metrics.total_lines}, "
            f"死代码={metrics.dead_code_lines}, "
            f"ROI={metrics.avg_roi:.2f}, "
            f"低效占比={metrics.low_efficiency_ratio:.1%}"
        )

    def record_snapshot(self, metrics: OptimizationMetrics) -> dict[str, Any]:
        """记录一轮优化后的快照，返回变化量"""
        self._history.append(metrics)
        if self._baseline is None:
            self._baseline = metrics

        delta = {
            "lines_reduced": self._baseline.total_lines - metrics.total_lines,
            "dead_code_reduced": self._baseline.dead_code_lines - metrics.dead_code_lines,
            "duplicate_reduced": self._baseline.duplicate_lines - metrics.duplicate_lines,
            "exceptions_fixed": self._baseline.swallowed_exceptions - metrics.swallowed_exceptions,
            "roi_change": metrics.avg_roi - self._baseline.avg_roi,
            "low_efficiency_change": (
                self._baseline.low_efficiency_ratio - metrics.low_efficiency_ratio
            ),
            "import_time_change_ms": self._baseline.avg_import_time_ms - metrics.avg_import_time_ms,
            "cer": (metrics.total_lines - metrics.dead_code_lines - metrics.duplicate_lines)
            / max(metrics.total_lines, 1),
        }

        # 计算边际收益斜率
        if len(self._history) >= 3:
            recent_rois = [m.avg_roi for m in self._history[-3:]]
            delta["marginal_roi_slope"] = (
                (recent_rois[-1] - recent_rois[0])
                / max(abs(recent_rois[-1] - recent_rois[0]), 0.001)
                if len(recent_rois) >= 2
                else 0
            )

            # 边际收益递减警告
            if delta["marginal_roi_slope"] < 0.1 and len(self._history) >= 4:
                logger.warning(
                    "[边际收益递减警告] 最近3轮ROI斜率={:.3f}，已进入低效边界区域。"
                    "建议停止该方向优化，转向其他模块。".format(delta["marginal_roi_slope"])
                )

        logger.info(
            f"[边际收益监控] 快照#{len(self._history)}: "
            f"减少{delta['lines_reduced']}行, "
            f"ROI变化{delta['roi_change']:+.2f}, "
            f"CER={delta['cer']:.2%}"
        )

        return delta

    def should_stop_optimization(self, module_name: str) -> bool:
        """判断是否应停止对某模块的优化（边际收益已耗尽）"""
        if len(self._history) < 3:
            return False

        recent_deltas = []
        for i in range(1, len(self._history)):
            prev = self._history[i - 1]
            curr = self._history[i]
            if prev.total_lines > 0:
                delta_roi = curr.avg_roi - prev.avg_roi
                delta_lines = prev.total_lines - curr.total_lines
                if delta_lines > 0:
                    recent_deltas.append(delta_roi / delta_lines)

        if len(recent_deltas) >= 2 and all(abs(d) < 0.001 for d in recent_deltas[-2:]):
            logger.info(
                f"[边际收益耗尽] 模块'{module_name}'的边际收益已趋近于零，"
                f"建议停止优化并将资源转移到其他模块。"
            )
            return True

        return False

    def get_health_summary(self) -> dict[str, Any]:
        """获取健康摘要"""
        if not self._history:
            return {"status": "no_data"}

        current = self._history[-1]
        baseline = self._baseline or current

        return {
            "status": "healthy" if current.avg_roi > 1.0 else "needs_optimization",
            "cer": (current.total_lines - current.dead_code_lines - current.duplicate_lines)
            / max(current.total_lines, 1),
            "roi": current.avg_roi,
            "roi_change_from_baseline": current.avg_roi - baseline.avg_roi,
            "low_efficiency_ratio": current.low_efficiency_ratio,
            "total_lines": current.total_lines,
            "optimization_rounds": len(self._history),
            "marginal_roi_warning": (
                len(self._history) >= 4
                and abs(self._history[-1].avg_roi - self._history[-3].avg_roi) < 0.05
            ),
        }

    def save(self) -> None:
        """持久化监控数据"""
        data = {
            "baseline": self._baseline.__dict__ if self._baseline else None,
            "history": [m.__dict__ for m in self._history],
        }
        save_json(self._history_path, data, pretty=True)


# ═══════════════════════════════════════════════════════════════════
# 自动化资源重分配器
# ═══════════════════════════════════════════════════════════════════


class ResourceReallocator:
    """资源重分配器 — 将资源从低效模块转移到高收益核心

    自动化策略：
      1. 移除纯转发层（如 style_engineer.py）
      2. 统一日志体系（消除 logging/loguru 混用）
      3. 删除重复检查点保存代码
      4. 清理静默吞异常
      5. 将省下的维护精力投入到高ROI核心模块
    """

    def __init__(
        self,
        analyzer: MarginalEfficiencyAnalyzer,
        monitor: OptimizationMonitor,
    ) -> None:
        self._analyzer = analyzer
        self._monitor = monitor

    def execute_optimization(self) -> OptimizationReport:
        """执行一轮优化"""
        report = self._analyzer.generate_report()

        logger.info(f"[资源重分配] 发现{len(report.low_efficiency_modules)}个低效边界模块")
        for name in report.low_efficiency_modules:
            logger.info(f"  - {name}")

        logger.info(f"[资源重分配] 生成{len(report.directives)}条优化指令")
        for d in report.directives:
            logger.info(f"  [{d.priority}] {d.action.value}: {d.target} — {d.reason}")

        logger.info(f"[资源重分配] 预计节省 {report.total_lines_saved} 行代码")
        logger.info(f"[资源重分配] {len(report.reallocations)} 条资源转移方案")

        for r in report.reallocations:
            logger.info(
                f"  {r.from_module} → {r.to_module}: "
                f"转移{r.amount}{r.resource_type}，预期ROI增益{r.expected_roi_gain:+.2f}"
            )

        return report


# ═══════════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════════


# 预配置的昆仑项目模块分析（基于实际代码分析结果）
def create_kunlun_analyzer() -> MarginalEfficiencyAnalyzer:
    """创建预配置的昆仑项目边际收益分析器"""
    analyzer = MarginalEfficiencyAnalyzer()

    # === 核心模块（高ROI，需保护） ===
    analyzer.register_module(
        "agents/makefile.py",
        ModuleTier.CORE,
        code_lines=2200,
        complexity_score=85,
        maintenance_burden=70,
        runtime_overhead_ms=1200,
        dependency_count=15,
        usage_frequency=1.0,
        quality_contribution=90,
        test_coverage=10,
        bug_surface_area=60,
    )

    analyzer.register_module(
        "gacha/engine.py",
        ModuleTier.CORE,
        code_lines=800,
        complexity_score=60,
        maintenance_burden=20,
        runtime_overhead_ms=300,
        dependency_count=8,
        usage_frequency=0.95,
        quality_contribution=85,
        test_coverage=15,
        bug_surface_area=25,
    )

    analyzer.register_module(
        "gacha/circuit_breaker.py",
        ModuleTier.CORE,
        code_lines=280,
        complexity_score=45,
        maintenance_burden=10,
        runtime_overhead_ms=5,
        dependency_count=3,
        usage_frequency=0.90,
        quality_contribution=80,
        test_coverage=0,
        bug_surface_area=15,
    )

    analyzer.register_module(
        "agents/editor.py",
        ModuleTier.CORE,
        code_lines=850,
        complexity_score=65,
        maintenance_burden=35,
        runtime_overhead_ms=200,
        dependency_count=10,
        usage_frequency=0.90,
        quality_contribution=75,
        test_coverage=0,
        bug_surface_area=35,
    )

    # === 支撑模块（中等ROI） ===
    analyzer.register_module(
        "agents/architect.py",
        ModuleTier.SUPPORT,
        code_lines=350,
        complexity_score=40,
        maintenance_burden=15,
        runtime_overhead_ms=100,
        dependency_count=5,
        usage_frequency=0.80,
        quality_contribution=65,
        test_coverage=30,
        bug_surface_area=20,
    )

    analyzer.register_module(
        "agents/writer.py",
        ModuleTier.SUPPORT,
        code_lines=400,
        complexity_score=50,
        maintenance_burden=25,
        runtime_overhead_ms=500,
        dependency_count=7,
        usage_frequency=0.85,
        quality_contribution=70,
        test_coverage=20,
        bug_surface_area=30,
    )

    analyzer.register_module(
        "agents/auditor.py",
        ModuleTier.SUPPORT,
        code_lines=200,
        complexity_score=35,
        maintenance_burden=15,
        runtime_overhead_ms=150,
        dependency_count=4,
        usage_frequency=0.75,
        quality_contribution=60,
        test_coverage=25,
        bug_surface_area=18,
    )

    analyzer.register_module(
        "audit/audit33.py",
        ModuleTier.SUPPORT,
        code_lines=1900,
        complexity_score=75,
        maintenance_burden=40,
        runtime_overhead_ms=600,
        dependency_count=6,
        usage_frequency=0.70,
        quality_contribution=55,
        test_coverage=0,
        bug_surface_area=45,
    )

    analyzer.register_module(
        "api/routers/pipeline.py",
        ModuleTier.SUPPORT,
        code_lines=350,
        complexity_score=30,
        maintenance_burden=10,
        runtime_overhead_ms=10,
        dependency_count=2,
        usage_frequency=0.60,
        quality_contribution=40,
        test_coverage=5,
        bug_surface_area=10,
    )

    # === 外围/低效边界模块（低ROI，优化目标） ===
    analyzer.register_module(
        "agents/style_engineer.py",
        ModuleTier.PERIPHERAL,
        code_lines=13,
        complexity_score=5,
        maintenance_burden=5,
        runtime_overhead_ms=1,
        dependency_count=2,
        usage_frequency=0.05,
        quality_contribution=5,
        test_coverage=10,
        bug_surface_area=2,
    )

    analyzer.register_module(
        "agents/reflector_agent.py",
        ModuleTier.PERIPHERAL,
        code_lines=320,
        complexity_score=40,
        maintenance_burden=55,
        runtime_overhead_ms=200,
        dependency_count=5,
        usage_frequency=0.30,
        quality_contribution=20,
        test_coverage=0,
        bug_surface_area=40,
    )

    analyzer.register_module(
        "agents/scheduler.py",
        ModuleTier.PERIPHERAL,
        code_lines=380,
        complexity_score=45,
        maintenance_burden=30,
        runtime_overhead_ms=50,
        dependency_count=6,
        usage_frequency=0.35,
        quality_contribution=25,
        test_coverage=0,
        bug_surface_area=30,
    )

    analyzer.register_module(
        "kg/repositories/ (logging混用)",
        ModuleTier.PERIPHERAL,
        code_lines=250,
        complexity_score=25,
        maintenance_burden=50,
        runtime_overhead_ms=20,
        dependency_count=3,
        usage_frequency=0.20,
        quality_contribution=10,
        test_coverage=0,
        bug_surface_area=15,
    )

    return analyzer


# 全局单例
marginal_analyzer = create_kunlun_analyzer()
optimization_monitor = OptimizationMonitor()
resource_reallocator = ResourceReallocator(marginal_analyzer, optimization_monitor)
