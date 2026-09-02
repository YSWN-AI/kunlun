"""
昆仑创作引擎 — 作品全量配置管理器

将所有可安全定制的配置项统一开放给用户，包括:
  - 模型参数 (temperature/top_p/max_tokens等)
  - 门禁权重 (8 Gate的权重和通过阈值)
  - 体裁相关 (章节类型/节奏/爽点重心)
  - 写作风格提示
  - 禁用词/偏好词
  - 每章目标字数
  - 审计严格程度

对于用户未设定的配置项，支持 LLM 自动推演建议值。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from loguru import logger

from kunlun.config import settings


@dataclass
class BookConfig:
    """作品全量配置"""

    # 基本信息
    book_id: str = ""
    title: str = ""
    genre: str = "xuanhuan"
    description: str = ""

    # 创作参数
    target_chapter_words: int = 2500  # 每章目标字数
    total_chapters: int = 100  # 预计总章节
    chapter_types: list[str] = field(
        default_factory=lambda: ["normal", "battle", "climax", "intro"]
    )

    # 节奏控制
    pacing: str = "medium"  # slow/medium/fast
    pleasure_density: str = "medium"  # 爽点密度 low/medium/high
    description_density: str = "medium"  # 描写密度 low/medium/high
    dialogue_ratio: str = "medium"  # 对话比例 low/medium/high

    # 写作风格
    style_hints: list[str] = field(default_factory=list)
    taboo_words: list[str] = field(default_factory=list)
    preferred_words: list[str] = field(default_factory=list)

    # 门禁配置
    gate_weights: dict[str, float] = field(
        default_factory=lambda: {
            "G1": 0.15,
            "G2": 0.15,
            "G3": 0.20,
            "G4": 0.10,
            "G5": 0.10,
            "G6": 0.10,
            "G7": 0.10,
            "G8": 0.10,
        }
    )
    audit_pass_threshold: float = 0.6  # 审计通过阈值

    # 角色/世界观
    main_characters: list[dict] = field(default_factory=list)
    world_rules: list[str] = field(default_factory=list)

    # 模型偏好
    preferred_model: str = "deepseek-chat"
    fallback_model: str = "deepseek-chat"

    # 金手指/核心设定(LLM自动推演)
    golden_finger: dict = field(default_factory=dict)
    core_conflict: str = ""
    target_audience: str = ""


class BookConfigManager:
    """
    作品配置管理器

    能力:
      1. 读写作品 JSON 配置
      2. 自动补全未设定字段（用 LLM 推演）
      3. 导出为注入文本（供 Prompt 使用）
      4. 通过 API 完全开放给用户
    """

    def __init__(self):
        self._config_dir = settings.DATA_DIR / "configs"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, BookConfig] = {}

    def load(self, book_id: str) -> BookConfig:
        """加载作品配置"""
        if book_id in self._cache:
            return self._cache[book_id]

        path = self._path(book_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                config = BookConfig(**data)
                self._cache[book_id] = config
                return config
            except Exception as e:
                logger.warning(f"[BookConfig] 加载失败 {book_id}: {e}")

        # 创建默认配置
        config = BookConfig(book_id=book_id)
        self._cache[book_id] = config
        return config

    def save(self, config: BookConfig):
        """保存作品配置"""
        path = self._path(config.book_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(config)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._cache[config.book_id] = config
        logger.info(f"[BookConfig] {config.book_id} 配置已保存")

    def update(self, book_id: str, updates: dict) -> BookConfig:
        """更新作品配置（部分更新）"""
        config = self.load(book_id)
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save(config)
        return config

    def get_all(self, book_id: str) -> dict:
        """获取完整配置字典"""
        config = self.load(book_id)
        return asdict(config)

    # ─── LLM 自动推演 ─────────────────────────────────

    async def auto_deduce(self, book_id: str, field: str, user_hint: str = "") -> str:
        """
        对未设定的字段用 LLM 自动推演。

        当用户问到或用到某个未配置的字段时调用。

        Args:
            book_id: 作品ID
            field: 要推演的字段名
            user_hint: 用户的额外提示

        Returns:
            推演结果描述
        """
        config = self.load(book_id)

        field_prompts = {
            "golden_finger": (
                f"为作品《{config.title}》({config.genre}) 设计一个金手指/核心能力设定。"
                f"包括: 名称、来源、表现形式、限制条件、成长路径。"
                f"输出 JSON 格式。"
            ),
            "core_conflict": (
                f"为{config.genre}小说《{config.title}》定义核心冲突。"
                f"考虑: 人与人的冲突、人与世界的冲突、人与自我的冲突。"
                f"一句话概括核心冲突。"
            ),
            "target_audience": (
                f"分析{config.genre}小说《{config.title}》的目标读者群体画像。"
                f"包括: 年龄段、性别比例、阅读偏好、付费意愿。"
            ),
            "style_hints": (
                f"为{config.genre}小说《{config.title}》推荐5条写作风格提示。"
                f"每条约10个字，如'气势恢宏的修炼场景'。"
                f"输出 JSON 字符串数组。"
            ),
            "taboo_words": (
                f"为{config.genre}小说《{config.title}》推荐应避免的词汇列表。"
                f"考虑题材一致性。输出 JSON 字符串数组。"
            ),
            "world_rules": (
                f"为{config.genre}小说《{config.title}》定义3-5条核心世界观规则。"
                f"如战力体系规则、社会等级规则等。输出 JSON 字符串数组。"
            ),
        }

        prompt = field_prompts.get(field)
        if not prompt:
            return f"未知字段: {field}"

        if user_hint:
            prompt += f"\n用户额外提示: {user_hint}"

        try:
            from kunlun.gacha.engine import gacha_engine

            result = await gacha_engine.generate(prompt, mode="single_fix")
            deduced = result.get("best_text", "")

            # 更新配置
            self.update(book_id, {field: deduced})

            logger.info(f"[BookConfig] LLM推演 {book_id}.{field} 完成")
            return deduced
        except Exception as e:
            logger.warning(f"[BookConfig] LLM推演失败 {field}: {e}")
            return f"推演失败: {e}"

    async def auto_deduce_all_missing(self, book_id: str) -> dict[str, str]:
        """自动推演所有未设定的字段"""
        config = self.load(book_id)
        results = {}
        auto_fields = [
            "golden_finger",
            "core_conflict",
            "target_audience",
            "style_hints",
            "taboo_words",
            "world_rules",
        ]

        for fld in auto_fields:
            if not getattr(config, fld, None):
                result = await self.auto_deduce(book_id, fld)
                results[fld] = result

        return results

    # ─── 注入文本 ─────────────────────────────────────

    def build_config_prompt(self, book_id: str) -> str:
        """
        将作品配置构建为注入文本，供 Prompt 使用。

        在 Agent 调用 LLM 前将此文本注入到系统提示中。
        """
        config = self.load(book_id)
        lines = ["## 📖 作品配置", ""]

        if config.title:
            lines.append(f"- 书名: {config.title}")
        if config.genre:
            from kunlun.genres import get_genre

            g = get_genre(config.genre)
            if g:
                lines.append(f"- 体裁: {g.name}")
        lines.append(f"- 每章目标字数: {config.target_chapter_words}")
        lines.append(f"- 节奏偏好: {config.pacing}")
        lines.append(f"- 爽点密度: {config.pleasure_density}")

        if config.style_hints:
            lines.append("\n### 写作风格提示")
            lines.extend(f"- {h}" for h in config.style_hints)

        if config.taboo_words:
            lines.append("\n### 避免使用的词")
            lines.append(", ".join(config.taboo_words[:10]))

        if config.golden_finger:
            lines.append("\n### 金手指设定")
            if isinstance(config.golden_finger, dict):
                for k, v in config.golden_finger.items():
                    lines.append(f"- {k}: {v}")
            else:
                lines.append(f"- {config.golden_finger}")

        if config.core_conflict:
            lines.append("\n### 核心冲突")
            lines.append(f"- {config.core_conflict}")

        return "\n".join(lines)

    def _path(self, book_id: str) -> Path:
        return self._config_dir / f"{book_id}.json"


# 全局单例
book_config_manager = BookConfigManager()
