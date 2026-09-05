"""
昆仑创作引擎 — Vibe Writing 氛围引擎

Vibe Writing 设计理念: 每一章、每一场景都有其"氛围基调"，
它决定了读者在阅读时的情绪底色。氛围是情绪驱动的具体化表现。

本模块提供:
  1. 氛围分类体系 (10+ 基础氛围类型)
  2. 场景氛围标注与追踪
  3. 氛围过渡建议（情绪弧线的二维扩展）
  4. Vibe注入提示词生成

六大驱动力之一: Vibe Writing (#6/6)
  - 金手指驱动 → pleasure/
  - 情节驱动   → outline/ + foreshadowing
  - 人物驱动   → arc/ + state/
  - 冲突驱动   → conflict/
  - 情绪驱动   → audit G6 + emotion_curve
  - Vibe Writing → style/vibe.py (本模块)

用法:
    vibe = VibeEngine(book_id="my_book")
    # 注册场景氛围
    vibe.register_scene_vibe(chapter=5, scene_index=0,
                              primary_vibe="tense", intensity=0.8)
    # 获取氛围过渡建议
    advice = vibe.suggest_vibe_transition(chapter=5)
    # 生成Vibe注入prompt
    prompt = vibe.build_vibe_prompt(chapter=5)
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from enum import StrEnum

from loguru import logger

from kunlun.config import settings


class VibeType(StrEnum):
    """基础氛围类型 — 用于标记场景和章节的情绪底色

    每种氛围都有: 中文名、情绪色、适用场景
    """

    TENSE = "tense"  # 紧张: 对峙/追逃/倒计时
    MYSTERIOUS = "mysterious"  # 神秘: 谜团/未知/探索
    SOLEMN = "solemn"  # 肃穆: 生死/仪式/审判
    JOYOUS = "joyous"  # 欢快: 重逢/胜利/喜剧
    MELANCHOLY = "melancholy"  # 忧伤: 离别/失去/回忆
    MAJESTIC = "majestic"  # 壮丽: 奇观/大场面/史诗
    INTIMATE = "intimate"  # 温馨: 日常/感情/友情
    DARK = "dark"  # 黑暗: 阴谋/恐怖/绝望
    HOPEFUL = "hopeful"  # 希望: 黎明/转机/觉醒
    CHAOTIC = "chaotic"  # 混乱: 战场/暴乱/灾难
    NOSTALGIC = "nostalgic"  # 怀旧: 回忆/故地/旧友
    SURREAL = "surreal"  # 梦幻: 幻境/修炼/奇遇
    COMIC = "comic"  # 轻松: 搞笑/吐槽/日常
    EPIC = "epic"  # 史诗: 决战/崛起/传奇


# 氛围 → 写作关键词映射（用于注入prompt）
VIBE_WRITING_KEYWORDS: dict[VibeType, list[str]] = {
    VibeType.TENSE: [
        "短促句式，加快节奏",
        "感官细节放大（心跳/呼吸/汗水）",
        "环境与情绪同调（阴天/暗夜/密闭空间）",
        "对话简短零碎，避免长篇对白",
    ],
    VibeType.MYSTERIOUS: [
        "使用模糊描述，不揭示全貌",
        "光影对比强烈（烛光/阴影/迷雾）",
        "留白和沉默制造悬念",
        "声音细节放大（脚步声/滴水声/风声）",
    ],
    VibeType.SOLEMN: [
        "用长句和排比营造仪式感",
        "环境庄严（大殿/祭坛/星空）",
        "人物动作缓慢克制",
        "用光影和色彩烘托（夕阳/烛火/黑白）",
    ],
    VibeType.JOYOUS: [
        "轻快的短句和对话",
        "明快的色彩和光线描写",
        "人物动作活泼",
        "使用感叹句和笑声",
    ],
    VibeType.MELANCHOLY: [
        "细腻的心理描写",
        "雨/落叶/黄昏等意象",
        "回忆与现实交织",
        "缓慢的叙事节奏",
    ],
    VibeType.MAJESTIC: [
        "全景式描写（俯瞰/远眺）",
        "用数字和对比强调宏大",
        "排比和叠词增强气势",
        "时间维度拉伸（古今对比）",
    ],
    VibeType.INTIMATE: [
        "注重微表情和小动作",
        "温暖的光线和色彩",
        "对话自然口语化",
        "细节描写（茶/饭/灯火）",
    ],
    VibeType.DARK: [
        "压抑的色彩（黑/灰/暗红）",
        "扭曲的感官描写",
        "心理暗示和不安感",
        "密闭/狭窄的空间描写",
    ],
    VibeType.HOPEFUL: [
        "由暗转明的光线变化",
        "向上的动作（抬头/站起/推开窗）",
        "温暖/明亮的色彩词汇",
        "节奏由慢到快的变化",
    ],
    VibeType.CHAOTIC: [
        "极短的片段式描写",
        "多感官信息同时涌入",
        "声音的混乱和重叠",
        "破碎的视觉画面",
    ],
    VibeType.EPIC: [
        "宏大的时间描述（千年/万载）",
        "天地异象（日月同辉/山河变色）",
        "群体视角和个体视角切换",
        "高昂的情绪渲染",
    ],
}


@dataclass
class SceneVibe:
    """单场景的氛围标注"""

    scene_index: int
    primary_vibe: VibeType
    secondary_vibe: VibeType | None = None
    intensity: float = 0.5  # 0.0-1.0
    description: str = ""


@dataclass
class ChapterVibe:
    """章节的整体氛围"""

    chapter: int
    scenes: list[SceneVibe] = field(default_factory=list)
    overall_vibe: VibeType | None = None
    emotional_arc: str = ""  # 情绪弧线描述
    vibe_shift: bool = False  # 是否存在氛围转换


class VibeEngine:
    """
    氛围引擎 (Vibe Writing)

    管理章节和场景级别的氛围标签，提供氛围过渡建议。
    与emotion_curve配合形成"情绪-氛围"二维叙事控制。
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self._chapters: dict[int, ChapterVibe] = {}
        self._data_dir = settings.DATA_DIR / "vibe" / book_id
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    # ─── 氛围注册 ────────────────────────────────────

    def register_scene_vibe(
        self,
        chapter: int,
        scene_index: int,
        primary_vibe: VibeType,
        secondary_vibe: VibeType | None = None,
        intensity: float = 0.5,
        description: str = "",
    ) -> SceneVibe:
        """注册场景氛围"""
        if chapter not in self._chapters:
            self._chapters[chapter] = ChapterVibe(chapter=chapter)

        scene = SceneVibe(
            scene_index=scene_index,
            primary_vibe=primary_vibe,
            secondary_vibe=secondary_vibe,
            intensity=intensity,
            description=description,
        )

        # 更新或添加
        existing = [s for s in self._chapters[chapter].scenes if s.scene_index == scene_index]
        if existing:
            self._chapters[chapter].scenes.remove(existing[0])
        self._chapters[chapter].scenes.append(scene)
        self._chapters[chapter].scenes.sort(key=lambda s: s.scene_index)

        # 自动计算整体氛围
        self._recalc_chapter_vibe(chapter)
        self._save()
        return scene

    def _recalc_chapter_vibe(self, chapter: int):
        """重新计算章节的整体氛围"""
        cv = self._chapters.get(chapter)
        if not cv or not cv.scenes:
            return

        # 整体氛围 = 强度最高的场景氛围
        main_scene = max(cv.scenes, key=lambda s: s.intensity)
        cv.overall_vibe = main_scene.primary_vibe

        # 检测氛围转换
        if len(cv.scenes) >= 2:
            types = [s.primary_vibe for s in cv.scenes]
            cv.vibe_shift = len(set(types)) >= 2

    # ─── 查询分析 ────────────────────────────────────

    def get_chapter_vibe(self, chapter: int) -> ChapterVibe | None:
        return self._chapters.get(chapter)

    def get_vibe_arc(self) -> list[dict]:
        """获取全书氛围弧线"""
        return [
            {
                "chapter": ch,
                "vibe": cv.overall_vibe.value if cv.overall_vibe else "unknown",
                "scenes": len(cv.scenes),
                "vibe_shift": cv.vibe_shift,
                "emotional_arc": cv.emotional_arc,
            }
            for ch, cv in sorted(self._chapters.items())
        ]

    def suggest_vibe_transition(self, current_chapter: int) -> list[str]:
        """建议下一章的氛围过渡方向"""
        prev = self._chapters.get(current_chapter)
        if not prev or not prev.overall_vibe:
            return ["使用默认氛围推进"]

        suggestions = []

        # 如果上一章比较沉重，建议轻松过渡
        if prev.overall_vibe in (VibeType.TENSE, VibeType.DARK, VibeType.SOLEMN):
            suggestions.extend(
                [
                    f"上一章氛围{prev.overall_vibe.value}，建议下一章用对比氛围缓解",
                    f"可考虑 {VibeType.JOYOUS.value}/{VibeType.INTIMATE.value} 作为过渡",
                ]
            )
        # 如果上一章比较轻松，建议制造转折
        elif prev.overall_vibe in (VibeType.JOYOUS, VibeType.COMIC):
            suggestions.extend(
                [
                    "上一章氛围轻松，建议下一章埋下紧张伏笔",
                    f"可在章末转向 {VibeType.TENSE.value}/{VibeType.MYSTERIOUS.value}",
                ]
            )
        # 如果连续多章同氛围，建议变化
        recent = [v.overall_vibe for c, v in sorted(self._chapters.items())[-3:] if v.overall_vibe]
        if len(recent) >= 3 and len(set(recent)) == 1:
            suggestions.append(f"连续{len(recent)}章{recent[0].value}氛围，建议变化")

        return suggestions

    @staticmethod
    def build_vibe_prompt(vibe: VibeType, intensity: float = 0.5) -> str:
        """根据氛围类型生成写作提示词（注入Writer prompt）"""
        keywords = VIBE_WRITING_KEYWORDS.get(vibe, [])
        if not keywords:
            return ""

        # 根据强度选择关键词数量
        num_keys = max(2, min(len(keywords), int(intensity * len(keywords))))
        selected = random.sample(keywords, num_keys)

        return f"\n【氛围基调: {vibe.value} (强度{intensity:.1f})】\n" + "\n".join(
            f"- {k}" for k in selected
        )

    # ─── 持久化 ──────────────────────────────────────

    def _save(self):
        data = {
            str(ch): {
                "chapter": cv.chapter,
                "scenes": [
                    {
                        "scene_index": s.scene_index,
                        "primary_vibe": s.primary_vibe.value,
                        "secondary_vibe": s.secondary_vibe.value if s.secondary_vibe else None,
                        "intensity": s.intensity,
                        "description": s.description,
                    }
                    for s in cv.scenes
                ],
                "overall_vibe": cv.overall_vibe.value if cv.overall_vibe else None,
                "emotional_arc": cv.emotional_arc,
                "vibe_shift": cv.vibe_shift,
            }
            for ch, cv in self._chapters.items()
        }
        path = self._data_dir / "vibe_data.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        path = self._data_dir / "vibe_data.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for cd in data.values():
                cv = ChapterVibe(chapter=cd["chapter"])
                for sd in cd.get("scenes", []):
                    cv.scenes.append(
                        SceneVibe(
                            scene_index=sd["scene_index"],
                            primary_vibe=VibeType(sd["primary_vibe"]),
                            secondary_vibe=VibeType(sd["secondary_vibe"])
                            if sd.get("secondary_vibe")
                            else None,
                            intensity=sd.get("intensity", 0.5),
                            description=sd.get("description", ""),
                        )
                    )
                cv.overall_vibe = VibeType(cd["overall_vibe"]) if cd.get("overall_vibe") else None
                cv.emotional_arc = cd.get("emotional_arc", "")
                cv.vibe_shift = cd.get("vibe_shift", False)
                self._chapters[cd["chapter"]] = cv
        except Exception as e:
            logger.warning(f"[VibeEngine] 加载失败: {e}")


# 全局实例管理
_engines: dict[str, VibeEngine] = {}


def get_vibe_engine(book_id: str) -> VibeEngine:
    if book_id not in _engines:
        _engines[book_id] = VibeEngine(book_id)
    return _engines[book_id]
