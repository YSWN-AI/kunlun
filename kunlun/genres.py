"""
昆仑创作引擎 — 体裁模板系统

借鉴 InkOS 的体裁系统 (10 English + 5 Chinese genres)，
为不同体裁提供专用的 Prompt 模板、门禁权重、节奏配置。

每个体裁定义:
  - 章节类型模板
  - 写作风格提示
  - 门禁权重配置
  - 节奏偏好
  - 禁用词列表
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GenreConfig:
    """体裁配置"""

    name: str  # 体裁名称
    description: str  # 简短描述
    chapter_types: list[str]  # 支持的章节类型
    style_hints: list[str]  # 写作风格提示
    pacing: str  # 节奏偏好 (slow/medium/fast)
    pleasure_focus: list[str]  # 爽点重心
    taboo_words: list[str]  # 禁用/避免词
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
    word_count_target: int = 2500  # 每章目标字数
    description_density: str = "medium"  # 描述密度 (low/medium/high)


GENRES: dict[str, GenreConfig] = {
    "xuanhuan": GenreConfig(
        name="玄幻",
        description="东方玄幻，修炼升级、奇遇冒险、位面征战",
        chapter_types=["normal", "battle", "climax", "intro", "cultivation", "treasure"],
        style_hints=["气势恢宏的修炼场景", "层次分明的境界体系", "热血的战斗描写"],
        pacing="medium",
        pleasure_focus=["打脸", "升级", "获得宝物", "复仇"],
        taboo_words=["现代科技", "枪炮", "民主", "科学"],
        word_count_target=2800,
    ),
    "xianxia": GenreConfig(
        name="仙侠",
        description="中国仙侠，修真问道、宗门恩怨、天道轮回",
        chapter_types=["normal", "battle", "climax", "intro", "comprehend", "tribulation"],
        style_hints=["飘逸出尘的意境", "诗意的修炼描写", "因果轮回的叙事感"],
        pacing="slow",
        pleasure_focus=["突破", "领悟", "奇遇", "复仇"],
        taboo_words=["现代化词汇", "科学解释", "西方魔法"],
        word_count_target=2600,
    ),
    "dushi": GenreConfig(
        name="都市",
        description="现代都市，商战/异能/生活/娱乐",
        chapter_types=["normal", "battle", "climax", "intro", "daily", "business"],
        style_hints=["贴近现代生活的细节", "快节奏的叙事", "现实主义基底"],
        pacing="fast",
        pleasure_focus=["打脸", "扬名", "赚钱", "感情推进"],
        taboo_words=["修仙", "炼丹", "法宝", "灵兽"],
        word_count_target=2200,
    ),
    "ke huan": GenreConfig(
        name="科幻",
        description="科幻未来，星际文明、AI觉醒、时空穿越",
        chapter_types=["normal", "battle", "climax", "intro", "exploration", "reveal"],
        style_hints=["硬核科技设定", "逻辑严谨的推演", "宏大的星际叙事"],
        pacing="medium",
        pleasure_focus=["真相揭露", "技术突破", "战略博弈", "奇观展示"],
        taboo_words=["魔法", "斗气", "灵气", "丹田"],
        word_count_target=3000,
        gate_weights={
            "G1": 0.10,
            "G2": 0.20,
            "G3": 0.15,
            "G4": 0.10,
            "G5": 0.10,
            "G6": 0.10,
            "G7": 0.10,
            "G8": 0.15,
        },
    ),
    "yanqing": GenreConfig(
        name="言情",
        description="女性向言情，现代/古代/穿越/甜宠",
        chapter_types=["normal", "romance", "climax", "intro", "daily", "angst"],
        style_hints=["细腻的情感描写", "人物心理活动丰富", "浪漫的场景营造"],
        pacing="slow",
        pleasure_focus=["感情推进", "甜蜜互动", "误会解开", "角色魅力"],
        taboo_words=["打打杀杀", "血腥", "残酷"],
        word_count_target=2000,
        gate_weights={
            "G1": 0.10,
            "G2": 0.10,
            "G3": 0.15,
            "G4": 0.05,
            "G5": 0.05,
            "G6": 0.25,
            "G7": 0.20,
            "G8": 0.10,
        },
    ),
    "kongbu": GenreConfig(
        name="恐怖",
        description="悬疑恐怖，灵异/克苏鲁/心理恐怖",
        chapter_types=["normal", "climax", "intro", "investigation", "escape"],
        style_hints=["压抑的氛围营造", "层层递进的紧张感", "留白的恐怖"],
        pacing="slow",
        pleasure_focus=["真相揭露", "危机逃脱", "谜题破解", "心理博弈"],
        taboo_words=["搞笑", "轻松", "甜蜜"],
        word_count_target=2000,
        gate_weights={
            "G1": 0.10,
            "G2": 0.15,
            "G3": 0.15,
            "G4": 0.10,
            "G5": 0.10,
            "G6": 0.20,
            "G7": 0.10,
            "G8": 0.10,
        },
    ),
    "lishi": GenreConfig(
        name="历史",
        description="历史架空，权谋/争霸/种田/改制",
        chapter_types=["normal", "battle", "climax", "intro", "strategy", "court"],
        style_hints=["考究的历史细节", "严谨的政治逻辑", "步步为营的权谋"],
        pacing="slow",
        pleasure_focus=["权谋胜利", "国力增强", "人才招募", "文化复兴"],
        taboo_words=["现代科技", "超自然力量", "穿越者金手指过强"],
        word_count_target=2600,
    ),
    "youxi": GenreConfig(
        name="游戏",
        description="游戏/电竞/虚拟现实，系统流/数据流",
        chapter_types=["normal", "battle", "climax", "intro", "dungeon", "pvp"],
        style_hints=["数据化的成长体系", "策略性的战斗描写", "游戏术语自然融入"],
        pacing="fast",
        pleasure_focus=["升级", "获得装备", "PK胜利", "副本通关"],
        taboo_words=["现实世界", "平淡日常"],
        word_count_target=2500,
        gate_weights={
            "G1": 0.10,
            "G2": 0.15,
            "G3": 0.15,
            "G4": 0.15,
            "G5": 0.10,
            "G6": 0.05,
            "G7": 0.10,
            "G8": 0.20,
        },
    ),
    "wuxia": GenreConfig(
        name="武侠",
        description="传统武侠，江湖恩怨、武学传承",
        chapter_types=["normal", "battle", "climax", "intro", "training", "investigation"],
        style_hints=["古风文笔", "侠义精神", "武学哲理"],
        pacing="medium",
        pleasure_focus=["武功突破", "复仇", "奇遇", "侠义之举"],
        taboo_words=["修仙", "魔法", "系统"],
        word_count_target=2500,
    ),
    "qihuan": GenreConfig(
        name="奇幻",
        description="西方奇幻，魔法/骑士/史诗冒险",
        chapter_types=["normal", "battle", "climax", "intro", "adventure", "revelation"],
        style_hints=["西方奇幻风格", "史诗感叙事", "魔法系统自洽"],
        pacing="medium",
        pleasure_focus=["冒险收获", "真相揭露", "战斗胜利", "伙伴羁绊"],
        taboo_words=["灵气", "丹田", "修炼"],
        word_count_target=2800,
        gate_weights={
            "G1": 0.15,
            "G2": 0.15,
            "G3": 0.15,
            "G4": 0.10,
            "G5": 0.10,
            "G6": 0.10,
            "G7": 0.10,
            "G8": 0.15,
        },
    ),
}


def get_genre(genre_name: str) -> GenreConfig | None:
    """获取体裁配置，不区分大小写"""
    genre_name = genre_name.lower().strip()
    # 支持中英文体裁名
    name_map = {
        "xuanhuan": "xuanhuan",
        "玄幻": "xuanhuan",
        "xianxia": "xianxia",
        "仙侠": "xianxia",
        "dushi": "dushi",
        "都市": "dushi",
        "kehuan": "ke huan",
        "科幻": "ke huan",
        "yanqing": "yanqing",
        "言情": "yanqing",
        "kongbu": "kongbu",
        "恐怖": "kongbu",
        "lishi": "lishi",
        "历史": "lishi",
        "youxi": "youxi",
        "游戏": "youxi",
        "wuxia": "wuxia",
        "武侠": "wuxia",
        "qihuan": "qihuan",
        "奇幻": "qihuan",
    }
    key = name_map.get(genre_name)
    return GENRES.get(key) if key else None


def list_genres() -> list[dict]:
    """列出所有支持的体裁"""
    return [
        {
            "key": key,
            "name": g.name,
            "description": g.description,
            "pacing": g.pacing,
            "chapter_types": g.chapter_types,
            "word_count_target": g.word_count_target,
        }
        for key, g in GENRES.items()
    ]
