"""
管线步骤：文风漂移检测 (Step 16)

分析当前章节文风并与基线对比，检测漂移趋势。
迁移自：Makefile._step_style_drift()
"""

from __future__ import annotations

import asyncio
import json as _json
from typing import Any

from loguru import logger

from kunlun.config import settings
from kunlun.pipeline.steps._base import PipelineStepBase


class StyleDriftStep(PipelineStepBase):
    step_name = "style_drift"
    required = False
    timeout = 60.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        from kunlun.audit.style_drift import style_drift_detector

        current_profile = style_drift_detector.analyze_chapter(
            ctx.polished_draft or ctx.draft, chapter=ctx.chapter
        )

        # 加载基线档案（最近3章）
        baseline_profiles = []
        try:
            from kunlun.audit.style_drift import StyleProfile

            drift_dir = settings.DATA_DIR / "style_profiles" / ctx.book_id
            if await asyncio.to_thread(drift_dir.exists):
                entries = await asyncio.to_thread(
                    lambda: sorted(drift_dir.glob("ch*.json"), reverse=True)[:3]
                )
                for f in entries:
                    try:
                        raw = await asyncio.to_thread(lambda p=f: p.read_text(encoding="utf-8"))
                        data = _json.loads(raw)
                        baseline_profiles.append(StyleProfile(**data))
                    except Exception as e_sp:
                        logger.debug(f"[{ctx.pipeline_id}] 文风档案读取跳过: {e_sp}")
        except Exception as e_dir:
            logger.debug(f"[{ctx.pipeline_id}] 文风档案目录读取跳过: {e_dir}")

        drift_report = style_drift_detector.compare_with_baseline(
            current_profile, baseline_profiles
        )
        ctx.result["style_drift"] = {
            "overall_stability": drift_report.overall_stability,
            "trend_direction": drift_report.trend_direction,
            "alert_count": len(drift_report.alerts),
            "summary": style_drift_detector.get_trend_summary(drift_report),
        }

        # 保存当前章节档案
        try:
            drift_dir = settings.DATA_DIR / "style_profiles" / ctx.book_id
            profile_path = drift_dir / f"ch{ctx.chapter:04d}.json"

            def _save_profile():
                drift_dir.mkdir(parents=True, exist_ok=True)
                profile_path.write_text(
                    _json.dumps(current_profile.__dict__, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            await asyncio.to_thread(_save_profile)
        except Exception as e_write:
            logger.debug(f"[{ctx.pipeline_id}] 文风档案写入跳过: {e_write}")

        if drift_report.alerts:
            for alert in drift_report.alerts[:3]:
                logger.info(
                    f"[{ctx.pipeline_id}] [文风漂移] {alert.dimension}: {alert.suggestion[:80]}"
                )
        logger.info(f"[{ctx.pipeline_id}] 文风漂移: {ctx.result['style_drift']['summary']}")

        return ctx.result["style_drift"]
