"""
昆仑创作引擎 — SKILL.md 技能加载器

职责: 启动时读取 skills/ 目录下的所有 .md 文件，
组装为 System Prompt 注入到 Architect / Writer / Auditor 的 prompt 中。

设计: 惰性加载 + 缓存，仅在首次请求时读取文件系统。
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from kunlun.config import settings


class SkillLoader:
    """
    技能加载器

    读取 skills/ 目录下的 Markdown 技能文件，
    提供按分类查询和全量注入接口。
    """

    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or settings.SKILLS_DIR
        self._cache: dict[str, str] = {}
        self._loaded = False

    def load_all(self) -> dict[str, str]:
        """加载所有 .md 文件，键为文件名(不含扩展名)"""
        if self._loaded and self._cache:
            return self._cache

        self._cache = {}
        if not self.skills_dir.exists():
            logger.warning(f"skills 目录不存在: {self.skills_dir}")
            return self._cache

        for fpath in sorted(self.skills_dir.glob("*.md")):
            try:
                content = fpath.read_text(encoding="utf-8")
                name = fpath.stem  # 去扩展名
                self._cache[name] = content
                logger.info(f"已加载技能文件: {name} ({len(content)} 字符)")
            except Exception as e:
                logger.warning(f"加载技能文件失败 {fpath}: {e}")

        self._loaded = True
        return self._cache

    def get(self, name: str) -> str:
        """按名称获取单个技能内容"""
        skills = self.load_all()
        return skills.get(name, "")

    def get_by_category(self, category: str) -> dict[str, str]:
        """
        按分类获取技能。
        分类在文件名中通过前缀识别，如 'prompt_创意阶段.md' -> 分类 'prompt'
        """
        skills = self.load_all()
        return {
            name: content
            for name, content in skills.items()
            if name.startswith(f"{category}_") or name == category
        }

    def inject_as_system_prompt(self, skill_names: list[str] | None = None) -> str:
        """
        将指定技能注入为 System Prompt 格式。

        Args:
            skill_names: 要注入的技能名列表，不传则全部注入

        Returns:
            格式化的 System Prompt 追加文本
        """
        skills = self.load_all()
        if not skills:
            return ""

        selected = {k: v for k, v in skills.items() if k in skill_names} if skill_names else skills

        if not selected:
            return ""

        parts = ["## 创作技能指引", ""]
        for name, content in selected.items():
            # 提取标题行
            title = name
            lines = content.split("\n")
            if lines and lines[0].startswith("# "):
                title = lines[0][2:].strip()

            parts.append(f"### {title}")
            parts.append(content)
            parts.append("")

        return "\n".join(parts)

    def get_golden_three_chapters(self) -> str:
        """获取黄金三章模板"""
        return self.get("黄金三章模板")

    def get_audit_checklist(self) -> str:
        """获取过签审核清单"""
        return self.get("过签审核清单")

    def get_rewrite_rules(self) -> str:
        """获取口语化改写规则"""
        return self.get("口语化改写规则")

    def clear_cache(self):
        """清除缓存，下次访问时重新加载"""
        self._cache.clear()
        self._loaded = False


# 全局单例
skill_loader = SkillLoader()

__all__ = ["SkillLoader", "skill_loader"]
