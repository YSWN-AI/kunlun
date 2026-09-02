"""
昆仑创作引擎 — 生成参数随机化器（增强版）

核心作用: 在生成时自动随机搭配参数，规避套路化风险。

7 维随机化:
  1. temperature: 基准值 ± 范围内随机
  2. top_p: 范围内均匀随机
  3. presence_penalty: 减少词语重复
  4. frequency_penalty: 减少短语重复
  5. max_tokens: ±15% 随机波动
  6. 写作风格提示词: 从风格库中随机选取
  7. 模型组合: 同成本等内随机切换

章节类型感知:
  - climax: 更高温度(创意) + 更宽范围
  - transition: 更低温度(保守) + 更窄范围
  - normal: 标准范围

历史追踪: 连续 N 章不使用完全相同参数组合

灵感来源:
  - NovelForger: 动态 temperature + 3层策略
  - InkOS: 不使用固定 temperature
  - TextHumanize: 变化本身就是去AI
  - Humanizer: 24种写作特征需不同参数配合
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from dataclasses import dataclass

# ——— 各 Agent 的参数波动范围 ————————————

AGENT_PARAM_RANGES: dict[str, dict] = {
    "writer": {
        "temperature": {"base": 0.80, "range": 0.15},  # 0.65~0.95
        "top_p": {"min": 0.85, "max": 0.95},
        "presence_penalty": {"min": 0.0, "max": 0.3},
        "frequency_penalty": {"min": 0.0, "max": 0.2},
        "max_tokens_vary": 0.15,  # ±15%
    },
    "architect": {
        "temperature": {"base": 0.70, "range": 0.10},  # 0.60~0.80
        "top_p": {"min": 0.85, "max": 0.95},
        "presence_penalty": {"min": 0.0, "max": 0.1},
        "frequency_penalty": {"min": 0.0, "max": 0.1},
        "max_tokens_vary": 0.10,
    },
    "auditor": {
        "temperature": {"base": 0.30, "range": 0.05},  # 0.25~0.35（审计需稳定）
        "top_p": {"min": 0.90, "max": 0.95},
        "presence_penalty": {"min": 0.0, "max": 0.0},
        "frequency_penalty": {"min": 0.0, "max": 0.0},
        "max_tokens_vary": 0.05,
    },
    "reviser": {
        "temperature": {"base": 0.50, "range": 0.10},  # 0.40~0.60
        "top_p": {"min": 0.88, "max": 0.95},
        "presence_penalty": {"min": 0.0, "max": 0.1},
        "frequency_penalty": {"min": 0.0, "max": 0.1},
        "max_tokens_vary": 0.10,
    },
    "sociologist": {
        "temperature": {"base": 0.70, "range": 0.15},  # 0.55~0.85
        "top_p": {"min": 0.85, "max": 0.95},
        "presence_penalty": {"min": 0.0, "max": 0.15},
        "frequency_penalty": {"min": 0.0, "max": 0.1},
        "max_tokens_vary": 0.10,
    },
    "default": {
        "temperature": {"base": 0.70, "range": 0.10},
        "top_p": {"min": 0.88, "max": 0.95},
        "presence_penalty": {"min": 0.0, "max": 0.1},
        "frequency_penalty": {"min": 0.0, "max": 0.1},
        "max_tokens_vary": 0.10,
    },
}

# 章节类型 → 参数偏移量（Chapter-Type-Aware Randomization）
CHAPTER_TYPE_ADJUSTMENTS: dict[str, dict] = {
    "climax": {
        "temp_offset": +0.08,  # 高潮章更高温度 → 更有创意
        "range_multiplier": 1.3,  # 更宽范围
        "tag_bias": "creative",  # 倾向创意标签
    },
    "battle": {
        "temp_offset": +0.05,
        "range_multiplier": 1.2,
        "tag_bias": "creative",
    },
    "normal": {
        "temp_offset": 0.0,
        "range_multiplier": 1.0,
        "tag_bias": "",  # 无偏
    },
    "transition": {
        "temp_offset": -0.05,  # 过渡章更低温度 → 更稳定
        "range_multiplier": 0.8,
        "tag_bias": "conservative",
    },
}

# 写作风格提示词轮换库（避免每次生成指令相同）
STYLE_INSTRUCTIONS: list[str] = [
    "使用简洁有力的短句推进情节，长句用于渲染气氛。",
    "对话中多使用语气词和动作描写，避免完美对白。",
    "节奏张弛有度，紧张场景用短句，舒缓场景用长句。",
    "多用具象的感官细节（视觉/听觉/触觉）替代抽象叙述。",
    "减少'知道/觉得/感到'等心理直述，通过行动展现角色内心。",
    "段落长度不均匀分布，避免AI风格的整齐段落。",
    "战斗场面用短促有力的句式，情感场面用绵长的描写。",
    "开头直入主题，不铺垫；结尾留悬念，不总结。",
    "在关键情节点使用意想不到的转折词，避免'然而/但是'。",
    "用环境描写暗示角色情绪，代替直接情感陈述。",
    "对话符合角色性格和身份，不追求语法完美。",
    "信息通过情节自然展现，不做解释性说明。",
]


@dataclass
class VariedParams:
    """一次生成调用的随机参数（7维）"""

    temperature: float
    top_p: float
    presence_penalty: float
    frequency_penalty: float
    max_tokens: int = 0  # 随机化后的 max_tokens
    variation_seed: int = 0  # 随机种子(用于复现)
    variation_tag: str = ""  # 标记本次变体类型
    style_hint: str = ""  # 本次随机选中的写作风格提示

    def to_dict(self) -> dict:
        d = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
        }
        if self.max_tokens > 0:
            d["max_tokens"] = self.max_tokens
        return d

    def __str__(self):
        return (
            f"T={self.temperature:.2f} P={self.top_p:.2f} "
            f"PP={self.presence_penalty:.2f} FP={self.frequency_penalty:.2f} "
            f"MT={self.max_tokens} tag={self.variation_tag}"
        )


class ParamVariator:
    """
    参数随机化器（增强版）

    7 维随机化 + 章节类型感知 + 历史追踪防重复。

    用法:
        params = param_variator.get_params("writer", chapter=5, chapter_type="climax")
        # 返回随机化的 7 维参数
    """

    # 温度变体风格标签
    VARIATION_TAGS = [
        "conservative",  # 保守：低温度
        "balanced",  # 平衡：中等
        "creative",  # 创意：高温度
        "chaotic",  # 混沌：最高温度+高penalty
    ]

    def __init__(self):
        # 历史追踪：{agent: [(chapter, tag, temp)]} 用于防重复
        self._history: dict[str, list[tuple]] = defaultdict(list)
        self._max_history = 10

    def get_params(
        self,
        agent: str = "default",
        chapter: int = 0,
        chapter_type: str = "normal",
        force_tag: str | None = None,
        base_max_tokens: int = 4096,
    ) -> VariedParams:
        """
        获取随机化的生成参数（增强版：7维 + 章节类型感知）

        Args:
            agent: Agent 名称
            chapter: 当前章节号
            chapter_type: 章节类型 (normal/climax/transition/battle)
            force_tag: 强制指定风格标签
            base_max_tokens: 基准 max_tokens 值

        Returns:
            VariedParams 带随机化的参数（7维）
        """
        ranges = AGENT_PARAM_RANGES.get(agent, AGENT_PARAM_RANGES["default"])
        type_adj = CHAPTER_TYPE_ADJUSTMENTS.get(chapter_type, CHAPTER_TYPE_ADJUSTMENTS["normal"])

        # 使用章节号+确定性哈希派生随机种子，确保每章不同且跨进程可复现
        import hashlib

        agent_hash = (
            int(hashlib.md5(agent.encode(), usedforsecurity=False).hexdigest()[:8], 16) % 10000
        )
        seed = (chapter * 1000 + int(time.time() * 1000) % 10000) + agent_hash
        rng = random.Random(seed)

        # ── 1. 风格标签选择（章节类型感知） ──
        if force_tag:
            tag = force_tag
        elif type_adj["tag_bias"]:
            # 章节类型有偏时，70% 概率使用偏向标签
            tag = rng.choices(
                [type_adj["tag_bias"], *self.VARIATION_TAGS],
                weights=[0.7, 0.1, 0.1, 0.05, 0.05],
                k=1,
            )[0]
        else:
            tag = rng.choice(self.VARIATION_TAGS)

        # ── 2. 温度（章节类型感知偏移 + 范围乘法） ──
        tag_offsets = {"conservative": -0.10, "balanced": 0.0, "creative": +0.08, "chaotic": +0.15}
        temp_offset = tag_offsets.get(tag, 0.0) + type_adj["temp_offset"]
        base = ranges["temperature"]["base"]
        temp_range = ranges["temperature"]["range"] * type_adj["range_multiplier"]
        temperature = round(
            base + temp_offset + rng.uniform(-temp_range * 0.5, temp_range * 0.5), 3
        )
        temperature = max(0.1, min(1.5, temperature))

        # ── 3. top_p ──
        top_p = round(rng.uniform(ranges["top_p"]["min"], ranges["top_p"]["max"]), 3)

        # ── 4. presence_penalty（防词语重复） ──
        presence_penalty = round(
            rng.uniform(ranges["presence_penalty"]["min"], ranges["presence_penalty"]["max"]), 3
        )

        # ── 5. frequency_penalty（防短语重复） ──
        frequency_penalty = round(
            rng.uniform(ranges["frequency_penalty"]["min"], ranges["frequency_penalty"]["max"]), 3
        )

        # ── 6. max_tokens 随机波动 ──
        vary_pct = ranges.get("max_tokens_vary", 0.10)
        max_tokens = int(base_max_tokens * (1 + rng.uniform(-vary_pct, vary_pct)))

        # ── 7. 写作风格提示（每次不同） ──
        style_hint = rng.choice(STYLE_INSTRUCTIONS)

        # ── 历史追踪防重复 ──
        self._record_history(agent, chapter, tag, temperature)

        return VariedParams(
            temperature=temperature,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            max_tokens=round(max_tokens, -1),  # 取整到10的倍数
            variation_seed=seed,
            variation_tag=tag,
            style_hint=style_hint,
        )

    def _record_history(self, agent: str, chapter: int, tag: str, temp: float):
        """记录本次参数组合到历史，用于防重复"""
        self._history[agent].append((chapter, tag, round(temp, 2)))
        if len(self._history[agent]) > self._max_history:
            self._history[agent] = self._history[agent][-self._max_history :]

    def has_repeated_params(self, agent: str, tag: str, temp: float) -> bool:
        """检查最近N次是否用过相同参数组合"""
        recent = self._history.get(agent, [])
        if len(recent) < 2:
            return False
        # 检查最近3次是否有相同 tag + temp
        same_count = sum(1 for _, t, tp in recent[-3:] if t == tag and abs(tp - temp) < 0.05)
        return same_count >= 2

    def get_model_combination(
        self,
        mode: str,
        chapter: int = 0,
        chapter_type: str = "normal",
        available_models: list[str] | None = None,
    ) -> list[dict]:
        """
        获取模式+模型的随机组合（章节类型感知）

        Args:
            mode: 基础模式
            chapter: 章节号
            chapter_type: 章节类型 (normal/climax/transition/battle)
            available_models: 可用模型列表

        Returns:
            [{"name": str, "temperature": float, "top_p": float}, ...]
        """
        rng = random.Random(chapter)
        models = available_models or ["deepseek-chat"]

        if mode in ("single_fix",):
            params = self.get_params("writer", chapter, chapter_type)
            return [
                {
                    "name": rng.choice(models),
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                    "max_tokens": params.max_tokens,
                }
            ]

        if mode == "gacha_cheap_2":
            params_a = self.get_params("writer", chapter, chapter_type, force_tag="conservative")
            params_b = self.get_params("writer", chapter + 1, chapter_type, force_tag="creative")
            return [
                {
                    "name": rng.choice(models),
                    "temperature": params_a.temperature,
                    "top_p": params_a.top_p,
                },
                {
                    "name": rng.choice(models),
                    "temperature": params_b.temperature,
                    "top_p": params_b.top_p,
                },
            ]

        if mode == "gacha_parallel_3":
            return [
                self._model_with_params(
                    rng, models, "writer", chapter, chapter_type, "conservative"
                ),
                self._model_with_params(
                    rng, models, "writer", chapter + 1, chapter_type, "balanced"
                ),
                self._model_with_params(
                    rng, models, "writer", chapter + 2, chapter_type, "creative"
                ),
            ]

        if mode == "gacha_ultimate_5":
            return [
                self._model_with_params(
                    rng, models, "writer", chapter, chapter_type, "conservative"
                ),
                self._model_with_params(
                    rng, models, "writer", chapter + 1, chapter_type, "balanced"
                ),
                self._model_with_params(
                    rng, models, "writer", chapter + 2, chapter_type, "creative"
                ),
                self._model_with_params(
                    rng, models, "writer", chapter + 3, chapter_type, "creative"
                ),
                self._model_with_params(
                    rng, models, "writer", chapter + 4, chapter_type, "chaotic"
                ),
            ]

        return [{"name": rng.choice(models), "temperature": 0.7}]

    @classmethod
    def _model_with_params(
        cls,
        rng: random.Random,
        models: list[str],
        agent: str,
        chapter: int,
        chapter_type: str,
        tag: str,
    ) -> dict:
        """生成单模型的随机参数（带章节类型感知）。
        使用全局单例 param_variator 以保持历史记录一致性，避免创建临时实例导致去重失效。
        """
        params = param_variator.get_params(agent, chapter, chapter_type=chapter_type, force_tag=tag)
        return {
            "name": rng.choice(models),
            "temperature": params.temperature,
            "top_p": params.top_p,
            "max_tokens": params.max_tokens,
        }


# 全局单例
param_variator = ParamVariator()


def randomize_params(agent: str = "default", chapter: int = 0) -> VariedParams:
    """便捷函数：获取随机参数"""
    return param_variator.get_params(agent, chapter)
