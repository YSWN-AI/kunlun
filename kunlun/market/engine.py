"""
市场情报系统 — 扫榜拆书 + 热搜热点辅助决策

功能:
  - 热点趋势分析: 通过LLM分析当前网文市场趋势
  - 拆书: 分析优秀作品的叙事结构、爽点布局、角色设计
  - 热搜关联: 将社会热点与创作方向关联
"""

from __future__ import annotations

import json

from loguru import logger


class MarketIntelligence:
    """市场情报分析器"""

    async def analyze_hot_trends(self) -> dict:
        from kunlun.gacha.engine import gacha_engine

        prompt = """你是网文行业资深分析师。请分析当前(2026年)网文市场的最新热点趋势。

输出JSON格式（不要markdown代码块）：
{
  "hot_genres": [{"name": "题材名称", "heat": 95, "trend": "上升/平稳/下降", "reason": "原因"}],
  "hot_tropes": [{"name": "热门套路", "frequency": "高频/中频",
                   "lifecycle": "上升期/成熟期/衰退期"}],
  "reader_preferences": {"male": ["偏好1","偏好2"], "female": ["偏好1","偏好2"]},
  "platform_trends": {"起点": "趋势描述", "番茄": "趋势描述",
                       "七猫": "趋势描述"},
  "new_opportunities": ["蓝海方向1", "蓝海方向2"],
  "risk_warnings": ["风险提示1"]
}

请基于你的训练数据中的行业知识进行分析。"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start : json_end + 1])
        except Exception as e:
            logger.error(f"[Market] 热点分析失败: {e}")

        return {"error": "分析失败", "hot_genres": [], "hot_tropes": []}

    async def dissect_book(self, book_description: str) -> dict:
        from kunlun.gacha.engine import gacha_engine

        prompt = f"""你是专业网文拆书分析师。请对以下作品进行多维度拆解分析。

作品描述: {book_description}

输出JSON格式：
{{
  "narrative_structure": {{
    "opening_strategy": "开篇策略（黄金三章分析）",
    "arc_design": "弧线设计特点",
    "pacing_pattern": "节奏模式"
  }},
  "pleasure_point_analysis": {{
    "density": "爽点密度（每千字）",
    "types": ["类型1","类型2"],
    "distribution": "分布规律"
  }},
  "character_design": {{
    "protagonist_archetype": "主角原型",
    "supporting_roles": "配角配置",
    "relationship_dynamics": "关系动力学"
  }},
  "world_building": {{
    "power_system": "力量体系特点",
    "world_depth": "世界观深度评估"
  }},
  "commercial_elements": {{
    "target_audience": "目标读者群",
    "monetization_potential": "商业价值评估",
    "adaptation_potential": "改编潜力"
  }},
  "lessons_for_writers": ["可借鉴点1","可借鉴点2","可借鉴点3"]
}}"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start : json_end + 1])
        except Exception as e:
            logger.error(f"[Market] 拆书失败: {e}")

        return {"error": "拆书失败"}

    async def link_hot_topics(self, story_seed: str) -> list[dict]:
        from kunlun.gacha.engine import gacha_engine

        prompt = f"""你是网文创意顾问。请将社会热点与以下故事创意关联，给出3-5个创作方向建议。

故事种子: {story_seed}

输出JSON格式：
[
  {{"topic": "热点话题", "angle": "创作切入角度", "hook": "营销钩子", "potential": "高/中/低"}}
]"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start = text.find("[")
            json_end = text.rfind("]")
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start : json_end + 1])
        except Exception as e:
            logger.error(f"[Market] 热点关联失败: {e}")

        return []


market_intel = MarketIntelligence()
