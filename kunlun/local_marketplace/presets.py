"""
昆仑创作引擎 — 本地技能包市场内置预设

定义 5 个官方组合包（Combo Pack），每个包含 Rule + Workflow + Skill 集合。
对标灵蟹创作 Marketplace 组合包，安装后写入书籍的 writing_packs.json。
"""

from __future__ import annotations

# ─── 通用 Rule 定义 ───────────────────────────────────────

RULE_RUTHLESS_PROTAGONIST = {
    "id": "rule_ruthless_protagonist",
    "name": "主角杀伐果断",
    "category": "character",
    "content": (
        "主角必须杀伐果断，不优柔寡断。面对敌人时迅速做出决断，"
        "不拖泥带水，不圣母心。有仇必报，有恩必还。"
    ),
    "priority": "high",
}

RULE_TIGHT_PACING = {
    "id": "rule_tight_pacing",
    "name": "节奏紧凑",
    "category": "pace",
    "content": (
        "保持紧凑节奏，删减不必要的过渡场景和冗长描写。每章至少推进一个剧情节点，避免水字数。"
    ),
    "priority": "high",
}

RULE_CHAPTER_HOOK = {
    "id": "rule_chapter_hook",
    "name": "章节末钩子",
    "category": "structure",
    "content": (
        "每章结尾必须设置悬念或反转钩子，让读者想立刻看下一章。"
        "钩子类型：危机突现、秘密揭露、人物登场、局势逆转。"
    ),
    "priority": "high",
}

RULE_COLLOQUIAL_DIALOGUE = {
    "id": "rule_colloquial_dialogue",
    "name": "对话口语化",
    "category": "dialogue",
    "content": (
        "人物对话必须口语化、自然，符合角色身份和性格。"
        "避免书面语和过于正式的表达，让对话像真人说话。"
    ),
    "priority": "medium",
}

RULE_AVOID_FLOWERY = {
    "id": "rule_avoid_flowery",
    "name": "避免华丽辞藻",
    "category": "style",
    "content": (
        "避免过度使用华丽辞藻和堆砌形容词。用简洁有力的语言表达，以情节和人物驱动故事，而非辞藻。"
    ),
    "priority": "medium",
}

# ─── 通用 Workflow 定义 ───────────────────────────────────

WORKFLOW_CLIMAX_ENHANCE = {
    "id": "wf_climax_enhance",
    "name": "爽点强化",
    "description": "在章节关键节点强化爽感，包括打脸、逆袭、突破、收获等爽点设计",
    "steps": [
        "识别本章爽点位置",
        "强化爽点前的压抑铺垫",
        "设计爽点爆发的具体方式",
        "添加爽点后的余韵和读者满足感",
    ],
}

WORKFLOW_OUTLINE_GEN = {
    "id": "wf_outline_gen",
    "name": "大纲生成",
    "description": "根据题材和核心设定生成完整大纲，含主线、支线、关键节点",
    "steps": [
        "梳理核心设定和主角目标",
        "生成主线剧情脉络（起承转合）",
        "设计支线和伏笔",
        "标注关键爽点和转折节点",
    ],
}

WORKFLOW_CHAPTER_REVIEW = {
    "id": "wf_chapter_review",
    "name": "章节审稿",
    "description": "对生成章节进行多维度审稿，检查节奏、逻辑、人物一致性",
    "steps": [
        "检查章节节奏是否紧凑",
        "验证人物行为是否符合设定",
        "排查逻辑漏洞和前后矛盾",
        "优化对话和描写",
    ],
}

# ─── 通用 Skill 定义 ──────────────────────────────────────

SKILL_XUANHUAN_WORLDBUILDING = {
    "id": "skill_xuanhuan_worldbuilding",
    "name": "玄幻世界观构建",
    "description": "构建玄幻世界观，含境界体系、势力分布、修炼规则、地理设定",
    "parameters": {
        "realm_system": "自定义境界等级体系",
        "factions": "宗门/王朝/异族势力分布",
        "cultivation_rules": "修炼资源和突破规则",
        "geography": "大陆/秘境/险地设定",
    },
}

SKILL_BATTLE_WRITING = {
    "id": "skill_battle_writing",
    "name": "战斗场景写作",
    "description": "高质量战斗场景写作，含招式描写、节奏控制、情绪渲染",
    "parameters": {
        "move_description": "招式和动作描写技巧",
        "battle_pacing": "战斗节奏控制（快/慢/停顿）",
        "emotion_render": "战斗中的情绪和心理渲染",
        "aftermath": "战斗结果和影响描写",
    },
}

SKILL_CHARACTER_ARC = {
    "id": "skill_character_arc",
    "name": "人物弧光设计",
    "description": "设计人物成长弧光，含初始状态、转变节点、最终形态",
    "parameters": {
        "initial_state": "人物初始性格和能力",
        "turning_points": "关键转变事件",
        "growth_trajectory": "成长轨迹设计",
        "final_form": "人物最终形态",
    },
}

# ─── 5 个组合包 ───────────────────────────────────────────

COMBO_PACKS: list[dict] = [
    {
        "id": "pack_xuanhuan_shuangwen",
        "name": "玄幻爽文套餐",
        "description": (
            "专为玄幻爽文打造，主角杀伐果断+节奏紧凑+章节钩子，"
            "配合爽点强化和战斗写作，让读者欲罢不能。"
        ),
        "author": "昆仑官方",
        "category": "xuanhuan",
        "rule_ids": [
            RULE_RUTHLESS_PROTAGONIST["id"],
            RULE_TIGHT_PACING["id"],
            RULE_CHAPTER_HOOK["id"],
        ],
        "workflow_ids": [WORKFLOW_CLIMAX_ENHANCE["id"]],
        "skill_ids": [
            SKILL_XUANHUAN_WORLDBUILDING["id"],
            SKILL_BATTLE_WRITING["id"],
        ],
        "rule_contents": [
            RULE_RUTHLESS_PROTAGONIST,
            RULE_TIGHT_PACING,
            RULE_CHAPTER_HOOK,
        ],
        "workflow_contents": [WORKFLOW_CLIMAX_ENHANCE],
        "skill_contents": [
            SKILL_XUANHUAN_WORLDBUILDING,
            SKILL_BATTLE_WRITING,
        ],
        "installed": False,
        "rating": 4.8,
        "downloads": 12580,
        "tags": ["玄幻", "爽文", "杀伐果断", "战斗", "热门"],
    },
    {
        "id": "pack_xianxia_xiuzhen",
        "name": "仙侠修真套餐",
        "description": (
            "仙侠修真风格，口语化对话+避免华丽辞藻，配合大纲生成和人物弧光设计，适合慢热修真流。"
        ),
        "author": "昆仑官方",
        "category": "xianxia",
        "rule_ids": [
            RULE_COLLOQUIAL_DIALOGUE["id"],
            RULE_AVOID_FLOWERY["id"],
        ],
        "workflow_ids": [WORKFLOW_OUTLINE_GEN["id"]],
        "skill_ids": [
            SKILL_XUANHUAN_WORLDBUILDING["id"],
            SKILL_CHARACTER_ARC["id"],
        ],
        "rule_contents": [
            RULE_COLLOQUIAL_DIALOGUE,
            RULE_AVOID_FLOWERY,
        ],
        "workflow_contents": [WORKFLOW_OUTLINE_GEN],
        "skill_contents": [
            SKILL_XUANHUAN_WORLDBUILDING,
            SKILL_CHARACTER_ARC,
        ],
        "installed": False,
        "rating": 4.6,
        "downloads": 8930,
        "tags": ["仙侠", "修真", "口语化", "慢热", "人物成长"],
    },
    {
        "id": "pack_dushi_yineng",
        "name": "都市异能套餐",
        "description": (
            "都市异能题材，节奏紧凑+主角杀伐果断，配合章节审稿和人物弧光，适合现代都市爽文。"
        ),
        "author": "昆仑官方",
        "category": "dushi",
        "rule_ids": [
            RULE_TIGHT_PACING["id"],
            RULE_RUTHLESS_PROTAGONIST["id"],
        ],
        "workflow_ids": [WORKFLOW_CHAPTER_REVIEW["id"]],
        "skill_ids": [SKILL_CHARACTER_ARC["id"]],
        "rule_contents": [
            RULE_TIGHT_PACING,
            RULE_RUTHLESS_PROTAGONIST,
        ],
        "workflow_contents": [WORKFLOW_CHAPTER_REVIEW],
        "skill_contents": [SKILL_CHARACTER_ARC],
        "installed": False,
        "rating": 4.5,
        "downloads": 7620,
        "tags": ["都市", "异能", "爽文", "现代", "审稿"],
    },
    {
        "id": "pack_lishi_chuanyue",
        "name": "历史穿越套餐",
        "description": (
            "历史穿越题材，口语化对话+避免华丽辞藻+章节钩子，"
            "配合大纲生成和人物弧光，适合历史正剧流。"
        ),
        "author": "昆仑官方",
        "category": "lishi",
        "rule_ids": [
            RULE_COLLOQUIAL_DIALOGUE["id"],
            RULE_AVOID_FLOWERY["id"],
            RULE_CHAPTER_HOOK["id"],
        ],
        "workflow_ids": [WORKFLOW_OUTLINE_GEN["id"]],
        "skill_ids": [SKILL_CHARACTER_ARC["id"]],
        "rule_contents": [
            RULE_COLLOQUIAL_DIALOGUE,
            RULE_AVOID_FLOWERY,
            RULE_CHAPTER_HOOK,
        ],
        "workflow_contents": [WORKFLOW_OUTLINE_GEN],
        "skill_contents": [SKILL_CHARACTER_ARC],
        "installed": False,
        "rating": 4.7,
        "downloads": 6840,
        "tags": ["历史", "穿越", "正剧", "口语化", "大纲"],
    },
    {
        "id": "pack_kehuan_moshi",
        "name": "科幻末世套餐",
        "description": (
            "科幻末世题材，节奏紧凑+章节钩子，配合爽点强化和战斗写作+人物弧光，适合末世生存爽文。"
        ),
        "author": "昆仑官方",
        "category": "kehuan",
        "rule_ids": [
            RULE_TIGHT_PACING["id"],
            RULE_CHAPTER_HOOK["id"],
        ],
        "workflow_ids": [WORKFLOW_CLIMAX_ENHANCE["id"]],
        "skill_ids": [
            SKILL_BATTLE_WRITING["id"],
            SKILL_CHARACTER_ARC["id"],
        ],
        "rule_contents": [
            RULE_TIGHT_PACING,
            RULE_CHAPTER_HOOK,
        ],
        "workflow_contents": [WORKFLOW_CLIMAX_ENHANCE],
        "skill_contents": [
            SKILL_BATTLE_WRITING,
            SKILL_CHARACTER_ARC,
        ],
        "installed": False,
        "rating": 4.4,
        "downloads": 5210,
        "tags": ["科幻", "末世", "生存", "战斗", "爽点"],
    },
]


def get_all_packs() -> list[dict]:
    """获取所有内置组合包（深拷贝，避免外部修改）"""
    import copy

    return [copy.deepcopy(p) for p in COMBO_PACKS]


def get_pack_by_id(pack_id: str) -> dict | None:
    """根据 ID 获取组合包"""
    for pack in COMBO_PACKS:
        if pack["id"] == pack_id:
            import copy

            return copy.deepcopy(pack)
    return None
