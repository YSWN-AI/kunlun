"""
自进化反馈闭环 — 作者画像 + 历史追踪 + 自动技能生成

组件:
  - AuthorProfile: 多维作者画像
  - EvolutionTracker: 追踪写作能力随时间的变化
  - SkillGenerator: 从反馈中自动生成技能文件
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from kunlun.config import settings


@dataclass
class AuthorProfile:
    """作者画像 — 多维特征向量"""

    book_id: str
    # 写作习惯
    avg_chapter_length: float = 3000.0
    preferred_write_time: str = ""
    chapters_per_week: float = 7.0
    revision_rate: float = 0.2  # 需要修订的比例

    # 风格特征
    style_vector: list[float] = field(default_factory=lambda: [0.5] * 20)
    genre_preferences: dict = field(default_factory=dict)

    # 质量趋势
    avg_audit_score: float = 0.0
    audit_score_trend: list[float] = field(default_factory=list)
    improvement_rate: float = 0.0

    # 成长轨迹
    total_chapters: int = 0
    total_words: int = 0
    skills_learned: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class EvolutionTracker:
    """进化追踪器 — 记录写作能力的演化"""

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.profile_path = settings.DATA_DIR / "learn" / f"{book_id}_profile.json"
        self.history_path = settings.DATA_DIR / "learn" / f"{book_id}_history.jsonl"
        self.profile = self._load_profile()
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_profile(self) -> AuthorProfile:
        if self.profile_path.exists():
            try:
                data = json.loads(self.profile_path.read_text(encoding="utf-8"))
                ap = AuthorProfile(book_id=self.book_id)
                for k, v in data.items():
                    if hasattr(ap, k):
                        setattr(ap, k, v)
                return ap
            except Exception:
                logger.warning("[Evolve] 加载画像失败，使用默认画像")
                pass
        return AuthorProfile(book_id=self.book_id)

    def record_chapter(
        self,
        chapter: int,
        word_count: int,
        audit_score: float,
        revision_count: int,
        _style_changes: int,
    ):
        """记录每章数据，追踪进化"""
        self.profile.total_chapters += 1
        self.profile.total_words += word_count
        self.profile.avg_chapter_length = self.profile.avg_chapter_length * 0.9 + word_count * 0.1
        self.profile.revision_rate = (
            self.profile.revision_rate * 0.9 + (1 if revision_count > 0 else 0) * 0.1
        )

        # 质量趋势
        self.profile.audit_score_trend.append(audit_score)
        if len(self.profile.audit_score_trend) > 50:
            self.profile.audit_score_trend = self.profile.audit_score_trend[-50:]
        self.profile.avg_audit_score = sum(self.profile.audit_score_trend) / len(
            self.profile.audit_score_trend
        )

        # 进步率（最近10章 vs 前10章）
        recent = self.profile.audit_score_trend[-10:]
        earlier = self.profile.audit_score_trend[-20:-10]
        if earlier and sum(earlier) > 0:
            self.profile.improvement_rate = (
                sum(recent) / len(recent) - sum(earlier) / len(earlier)
            ) / (sum(earlier) / len(earlier))

        self.profile.updated_at = time.time()
        self._save()

        # 写入历史
        with self.history_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "chapter": chapter,
                        "word_count": word_count,
                        "audit_score": audit_score,
                        "revisions": revision_count,
                        "time": time.time(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    def get_evolution_summary(self) -> str:
        """生成进化摘要"""
        p = self.profile
        lines = [f"## 作者进化报告 ({p.total_chapters}章, {p.total_words}字)"]
        lines.append(f"- 平均字数: {p.avg_chapter_length:.0f}字/章")
        lines.append(f"- 平均审计分: {p.avg_audit_score:.1f}")
        lines.append(f"- 修订率: {p.revision_rate:.1%}")
        lines.append(f"- 近10章进步率: {p.improvement_rate:+.1%}")
        lines.append(f"- 已学技能: {p.skills_learned}个")
        return "\n".join(lines)

    def _save(self):
        try:
            data = {k: v for k, v in self.profile.__dict__.items() if not k.startswith("_")}
            self.profile_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"[Evolve] 保存画像失败: {e}")


class SkillGenerator:
    """技能生成器 — 从反馈模式中自动创建SKILL.md"""

    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or settings.SKILLS_DIR

    async def generate_skill_from_feedback(
        self, feedback_text: str, feedback_context: dict
    ) -> Path | None:
        """从作者反馈中通过LLM生成技能文件"""
        from kunlun.gacha.engine import gacha_engine

        prompt = f"""你是写作技能提炼专家。根据以下作者反馈，提炼一条可复用的写作技能规则。

作者反馈: {feedback_text}
上下文: {json.dumps(feedback_context, ensure_ascii=False)}

生成格式（直接输出Markdown，不超过300字）：
# 技能名称（简短）
## 触发条件
描述什么时候应用这个技能
## 操作指南
具体操作步骤
## 预期效果
应用后的改善"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            skill_text = result.get("best_text", "")
            if not skill_text or len(skill_text) < 50:
                return None

            # 保存技能文件
            skill_name = f"evolved_{int(time.time())}.md"
            skill_path = self.skills_dir / skill_name
            skill_path.write_text(skill_text, encoding="utf-8")
            logger.info(f"[Evolve] 新技能已生成: {skill_name}")
            return skill_path
        except Exception as e:
            logger.error(f"[Evolve] 生成技能失败: {e}")
            return None


# 全局实例管理
_trackers: dict[str, EvolutionTracker] = {}


def get_evolution_tracker(book_id: str) -> EvolutionTracker:
    if book_id not in _trackers:
        _trackers[book_id] = EvolutionTracker(book_id)
    return _trackers[book_id]


skill_generator = SkillGenerator()
