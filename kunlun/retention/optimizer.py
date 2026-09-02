"""
昆仑创作引擎 — 留存优化建议生成器
"""

from __future__ import annotations

from typing import Any

from .types import DropOffPrediction, RetentionOptimizationPlan, RetentionReport


class RetentionOptimizer:
    """留存优化建议生成器

    基于竞品研究的最佳实践，针对不同平台生成优化建议。
    """

    PLATFORM_TIPS: dict[str, dict[str, list[str]]] = {
        "fanqie": {
            "hook": [
                "番茄读者耐心≤3秒，每章结尾必须有强悬念",
                "使用'突然/竟然/没想到'类反转句式结尾",
                "每2000字至少一个'装逼打脸'桥段",
            ],
            "pleasure": [
                "番茄算法偏好高互动率，打脸/装逼类爽点优先",
                "前3章必须打脸≥3次，否则推荐量减半",
                "避免连续2章无打脸的'水章'",
            ],
            "structure": [
                "章节字数1500-3000字最佳（番茄推荐算法偏好）",
                "每章2-3个场景，超过3个场景读者跳出率+40%",
            ],
        },
        "qidian": {
            "hook": [
                "起点读者耐心较好，但结尾仍需悬念断章",
                "长线伏笔≥30章可增加追读深度",
                "每章结尾预告下一章精彩点",
            ],
            "pleasure": [
                "起点读者偏好慢热升级流，暴爽节奏反而不佳",
                "每10-15章安排一个阶段高潮",
                "修炼体系清晰程度直接影响留存",
            ],
            "structure": [
                "章节字数2000-5000字均可接受",
                "每章建议2-4个场景",
            ],
        },
        "qimao": {
            "hook": [
                "七猫偏休闲，结尾需要轻松有趣+悬念",
                "每章结尾可以是一句有趣的吐槽/反转",
                "对话占比30%-50%为佳",
            ],
            "pleasure": [
                "七猫读者偏好轻松搞笑+爽点并重",
                "每千字≥3个爽点/笑点",
                "避免长时间压抑剧情",
            ],
            "structure": [
                "章节1500-3000字最佳",
                "轻对话+轻动作+轻描述 = 七猫黄金比例",
            ],
        },
    }

    @classmethod
    def generate_plan(
        cls,
        chapter_number: int,
        retention_report: RetentionReport,
        dropoff: DropOffPrediction | None = None,
        target_platform: str = "",
        _genre_template: str = "",
    ) -> RetentionOptimizationPlan:
        """生成留存优化方案"""
        priority_actions: list[dict[str, Any]] = []
        quick_wins: list[str] = []
        structural: list[str] = []

        overall = retention_report.overall_score

        if retention_report.hook_score < 0.5:
            priority_actions.append(
                {
                    "priority": 1,
                    "area": "hook",
                    "severity": "high" if retention_report.hook_score < 0.3 else "medium",
                    "action": f"增强钩子强度（当前{retention_report.hook_score:.2f}），"
                    f"优先强化结尾钩子",
                    "quick_fix": "在最后一段加入'突然/然而/就在此时'句式",
                }
            )
            quick_wins.append("在章节末尾加入悬念/反转/预告句式")

        if retention_report.pleasure_score < 0.5:
            priority_actions.append(
                {
                    "priority": 2,
                    "area": "pleasure",
                    "severity": "high" if retention_report.pleasure_score < 0.3 else "medium",
                    "action": f"提升爽点密度（当前{retention_report.pleasure_score:.2f}），"
                    f"增加打脸/升级/装逼类爽点",
                    "quick_fix": "穿插1-2个'装逼打脸'场景",
                }
            )
            quick_wins.append("增加2-3个打脸/碾压/装逼场景")

        if retention_report.debt_score < 0.5:
            priority_actions.append(
                {
                    "priority": 3,
                    "area": "debt",
                    "severity": "high" if retention_report.debt_score < 0.3 else "medium",
                    "action": f"减少未回收伏笔（当前评分{retention_report.debt_score:.2f}），"
                    f"建议回收1-2个旧伏笔",
                    "quick_fix": "在本章或下章安排一个伏笔回收",
                }
            )
            structural.append("建议回顾并回收超过10章的活跃伏笔")

        if retention_report.features and retention_report.features.dialogue_ratio > 0.55:
            quick_wins.append("对话占比过高，减少纯对话场景，增加动作/描述")
            structural.append("调整节奏: 55%对话 → 30-40%对话 + 20-30%动作")

        if retention_report.features and retention_report.features.dialogue_ratio < 0.12:
            quick_wins.append("对话不足，增加人物互动/对话增加可读性")
            structural.append("增加人物对话，当前对话比<12%过于沉闷")

        if dropoff and dropoff.predicted_dropoff_rate > 0.30:
            priority_actions.insert(
                0,
                {
                    "priority": 0,
                    "area": "dropoff",
                    "severity": "critical" if dropoff.predicted_dropoff_rate > 0.45 else "high",
                    "action": f"预测流失率{dropoff.predicted_dropoff_rate:.0%}，"
                    f"原因: {', '.join(dropoff.contributing_factors[:3])}",
                    "quick_fix": "优先解决导致流失的首要因素",
                },
            )

        platform_tips: dict[str, list[str]] = {}
        if target_platform and target_platform in cls.PLATFORM_TIPS:
            tips = cls.PLATFORM_TIPS[target_platform]
            platform_tips = {
                "hook": tips.get("hook", []),
                "pleasure": tips.get("pleasure", []),
                "structure": tips.get("structure", []),
            }

        if not priority_actions and overall >= 0.7:
            priority_actions.append(
                {
                    "priority": 99,
                    "area": "overall",
                    "severity": "low",
                    "action": "综合留存评分良好，保持当前水平",
                    "quick_fix": "微调爽点多样性/钩子类型避免疲劳",
                }
            )

        return RetentionOptimizationPlan(
            chapter_number=chapter_number,
            overall_retention_score=overall,
            priority_actions=priority_actions,
            quick_wins=quick_wins,
            structural_changes=structural,
            platform_specific_tips=platform_tips,
        )
