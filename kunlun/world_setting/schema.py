"""
昆仑创作引擎 — 世界观设定结构化 Schema

定义 30 类设定条目的结构化字段，每类包含 category_id / name / icon / fields。
字段类型支持: text / number / select / multiselect / textarea / list。

对标马良写作的世界观设定管理，按类别组织结构化字段，
支持按卷渐进开放与对 AI 隐藏防剧透。
"""

from __future__ import annotations

from typing import Any

# ─── 字段类型常量 ──────────────────────────────────────────────────────────
FIELD_TEXT = "text"
FIELD_NUMBER = "number"
FIELD_SELECT = "select"
FIELD_MULTISELECT = "multiselect"
FIELD_TEXTAREA = "textarea"
FIELD_LIST = "list"


def _field(
    name: str,
    label: str,
    ftype: str = FIELD_TEXT,
    options: list[str] | None = None,
    placeholder: str = "",
) -> dict[str, Any]:
    """构造单个字段定义。

    Args:
        name: 字段键名（英文 snake_case）
        label: 字段显示名（中文）
        ftype: 字段类型
        options: select/multiselect 的可选项
        placeholder: 输入提示占位符

    Returns:
        字段定义字典
    """
    f: dict[str, Any] = {"name": name, "label": label, "type": ftype}
    if options is not None:
        f["options"] = options
    if placeholder:
        f["placeholder"] = placeholder
    return f


def _category(
    category_id: str,
    name: str,
    icon: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """构造一个类别定义。"""
    return {"category_id": category_id, "name": name, "icon": icon, "fields": fields}


# ─── 30 类世界观设定 Schema ────────────────────────────────────────────────
WORLD_SETTING_CATEGORIES: list[dict[str, Any]] = [
    # 1. 力量体系
    _category(
        "power_system",
        "力量体系",
        "⚡",
        [
            _field("realm_name", "境界名称", FIELD_TEXT, placeholder="如：炼气期"),
            _field("power_level", "对应实力", FIELD_TEXTAREA, placeholder="该境界的战力描述"),
            _field("breakthrough_condition", "突破条件", FIELD_TEXTAREA),
            _field("cultivation_path", "修炼路径", FIELD_TEXTAREA),
            _field("technique_system", "功法体系", FIELD_TEXT),
            _field("talent_distinction", "天赋区分", FIELD_TEXTAREA),
            _field("taboo_limit", "禁忌限制", FIELD_TEXTAREA),
        ],
    ),
    # 2. 种族与文明
    _category(
        "race_civilization",
        "种族与文明",
        "👥",
        [
            _field("race_name", "种族名称", FIELD_TEXT),
            _field("appearance", "外貌特征", FIELD_TEXTAREA),
            _field("lifespan", "寿命", FIELD_TEXT, placeholder="如：800年"),
            _field("reproduction", "繁殖方式", FIELD_TEXT),
            _field("innate_ability", "天赋能力", FIELD_TEXTAREA),
            _field("weakness", "弱点", FIELD_TEXTAREA),
            _field("belief", "信仰", FIELD_TEXT),
            _field("social_structure", "社会结构", FIELD_TEXTAREA),
        ],
    ),
    # 3. 地理与地点
    _category(
        "geography",
        "地理与地点",
        "🗺️",
        [
            _field("place_name", "地点名称", FIELD_TEXT),
            _field("location_relation", "位置关系", FIELD_TEXTAREA),
            _field(
                "hierarchy",
                "层级",
                FIELD_SELECT,
                options=["大陆", "国家", "城市", "区域", "秘境", "其他"],
            ),
            _field("specialty_resource", "特产资源", FIELD_TEXT),
            _field("garrison_faction", "驻守势力", FIELD_TEXT),
            _field("special_artifact", "特殊法宝", FIELD_TEXT),
            _field("historical_event", "历史事件", FIELD_TEXTAREA),
        ],
    ),
    # 4. 势力与门派
    _category(
        "faction",
        "势力与门派",
        "🏯",
        [
            _field("faction_name", "势力名称", FIELD_TEXT),
            _field("power_structure", "权力结构", FIELD_TEXTAREA),
            _field("leader", "掌门/领袖", FIELD_TEXT),
            _field("elder_layer", "长老层", FIELD_TEXTAREA),
            _field("disciple_hierarchy", "弟子层级", FIELD_TEXTAREA),
            _field("internal_factions", "内部派系", FIELD_TEXTAREA),
            _field("external_relations", "外部关系", FIELD_TEXTAREA),
            _field("sphere_of_influence", "势力范围", FIELD_TEXT),
        ],
    ),
    # 5. 法宝物品
    _category(
        "artifact",
        "法宝物品",
        "⚔️",
        [
            _field("item_name", "物品名称", FIELD_TEXT),
            _field(
                "grade",
                "品级",
                FIELD_SELECT,
                options=["凡品", "灵品", "宝品", "玄品", "地品", "天品", "仙器", "神器"],
            ),
            _field("function_desc", "功能描述", FIELD_TEXTAREA),
            _field("usage_condition", "使用条件", FIELD_TEXT),
            _field("side_effect", "副作用", FIELD_TEXTAREA),
            _field("holder", "持有者", FIELD_TEXT),
            _field("origin", "来源", FIELD_TEXTAREA),
        ],
    ),
    # 6. 历史事件
    _category(
        "historical_event",
        "历史事件",
        "📜",
        [
            _field("event_name", "事件名称", FIELD_TEXT),
            _field("occur_time", "发生时间", FIELD_TEXT, placeholder="如：开元327年"),
            _field("involved_factions", "涉及势力", FIELD_LIST),
            _field("event_process", "事件经过", FIELD_TEXTAREA),
            _field("impact_consequence", "影响后果", FIELD_TEXTAREA),
            _field(
                "is_public",
                "是否公开",
                FIELD_SELECT,
                options=["公开", "半公开", "秘闻", "绝密"],
            ),
        ],
    ),
    # 7. 角色设定
    _category(
        "character_setting",
        "角色设定",
        "🧙",
        [
            _field("char_name", "角色名称", FIELD_TEXT),
            _field("identity", "身份", FIELD_TEXT),
            _field("appearance", "外貌", FIELD_TEXTAREA),
            _field("personality", "性格", FIELD_TEXTAREA),
            _field("ability", "能力", FIELD_TEXTAREA),
            _field("background_story", "背景故事", FIELD_TEXTAREA),
            _field("relationship_network", "关系网", FIELD_TEXTAREA),
        ],
    ),
    # 8. 功法武技
    _category(
        "technique",
        "功法武技",
        "📖",
        [
            _field("technique_name", "功法名称", FIELD_TEXT),
            _field(
                "grade",
                "品级",
                FIELD_SELECT,
                options=["黄阶", "玄阶", "地阶", "天阶", "仙阶", "神阶"],
            ),
            _field("cultivation_condition", "修炼条件", FIELD_TEXT),
            _field("effect_desc", "效果描述", FIELD_TEXTAREA),
            _field("layer_division", "层级划分", FIELD_TEXTAREA),
            _field("side_effect", "副作用", FIELD_TEXTAREA),
        ],
    ),
    # 9. 资源材料
    _category(
        "resource",
        "资源材料",
        "💎",
        [
            _field("material_name", "材料名称", FIELD_TEXT),
            _field(
                "grade",
                "品级",
                FIELD_SELECT,
                options=["普通", "稀有", "珍贵", "极品", "传说", "神话"],
            ),
            _field("origin_place", "产地", FIELD_TEXT),
            _field("usage", "用途", FIELD_TEXTAREA),
            _field("rarity", "稀有度", FIELD_NUMBER, placeholder="1-10"),
            _field("collection_method", "采集方式", FIELD_TEXTAREA),
        ],
    ),
    # 10. 组织机构
    _category(
        "organization",
        "组织机构",
        "🏛️",
        [
            _field("org_name", "组织名称", FIELD_TEXT),
            _field(
                "org_type",
                "类型",
                FIELD_SELECT,
                options=["商会", "公会", "学院", "情报组织", "暗杀组织", "宗教", "其他"],
            ),
            _field("purpose", "宗旨", FIELD_TEXTAREA),
            _field("org_structure", "组织结构", FIELD_TEXTAREA),
            _field("key_members", "主要成员", FIELD_LIST),
            _field("activity_scope", "活动范围", FIELD_TEXT),
        ],
    ),
    # 11. 规则习俗
    _category(
        "rule_custom",
        "规则习俗",
        "📋",
        [
            _field("rule_name", "规则名称", FIELD_TEXT),
            _field("applicable_scope", "适用范围", FIELD_TEXT),
            _field("content_desc", "内容描述", FIELD_TEXTAREA),
            _field("violation_consequence", "违反后果", FIELD_TEXTAREA),
            _field("origin", "起源", FIELD_TEXTAREA),
        ],
    ),
    # 12. 语言文化
    _category(
        "language_culture",
        "语言文化",
        "🗣️",
        [
            _field("language_name", "语言名称", FIELD_TEXT),
            _field("used_by_races", "使用种族", FIELD_LIST),
            _field("writing_features", "文字特点", FIELD_TEXTAREA),
            _field("cultural_features", "文化特色", FIELD_TEXTAREA),
            _field("important_literature", "重要文献", FIELD_LIST),
        ],
    ),
    # 13. 魔法体系
    _category(
        "magic_system",
        "魔法体系",
        "✨",
        [
            _field("magic_name", "魔法名称", FIELD_TEXT),
            _field("element_type", "元素类型", FIELD_TEXT, placeholder="如：火/水/风/雷"),
            _field("casting_method", "施法方式", FIELD_TEXT),
            _field("mana_cost", "魔力消耗", FIELD_TEXT),
            _field("effect_desc", "效果描述", FIELD_TEXTAREA),
            _field("counter_measure", "克制方式", FIELD_TEXT),
        ],
    ),
    # 14. 神祇与信仰
    _category(
        "deity",
        "神祇与信仰",
        "🙏",
        [
            _field("deity_name", "神祇名称", FIELD_TEXT),
            _field("divine_domain", "神职领域", FIELD_TEXT),
            _field("divine_rank", "神位等级", FIELD_TEXT),
            _field("worship_method", "崇拜方式", FIELD_TEXTAREA),
            _field("divine_power", "神力表现", FIELD_TEXTAREA),
            _field("holy_land", "圣地", FIELD_TEXT),
            _field("relation_with_other", "与其他神祇关系", FIELD_TEXTAREA),
        ],
    ),
    # 15. 宇宙观/创世
    _category(
        "cosmology",
        "宇宙观与创世",
        "🌌",
        [
            _field("world_structure", "世界结构", FIELD_TEXTAREA, placeholder="如：三界六道"),
            _field("creation_myth", "创世神话", FIELD_TEXTAREA),
            _field("cosmic_law", "宇宙法则", FIELD_TEXTAREA),
            _field("heavenly_tribulation", "天劫机制", FIELD_TEXTAREA),
            _field("reincarnation", "轮回机制", FIELD_TEXTAREA),
        ],
    ),
    # 16. 时间历法
    _category(
        "time_system",
        "时间历法",
        "⏳",
        [
            _field("calendar_name", "历法名称", FIELD_TEXT),
            _field("year_length", "一年长度", FIELD_TEXT, placeholder="如：365天"),
            _field("month_division", "月份划分", FIELD_TEXTAREA),
            _field("week_system", "星期制度", FIELD_TEXT),
            _field("important_festival", "重要节日", FIELD_LIST),
            _field("era_division", "纪元划分", FIELD_TEXTAREA),
        ],
    ),
    # 17. 货币经济
    _category(
        "currency_economy",
        "货币经济",
        "💰",
        [
            _field("currency_name", "货币名称", FIELD_TEXT),
            _field("currency_unit", "货币单位", FIELD_TEXT, placeholder="如：灵石/金币"),
            _field("exchange_rate", "兑换比率", FIELD_TEXTAREA),
            _field("economic_system", "经济体系", FIELD_TEXTAREA),
            _field("main_trade", "主要贸易", FIELD_LIST),
            _field("wealth_standard", "财富标准", FIELD_TEXTAREA),
        ],
    ),
    # 18. 交通出行
    _category(
        "transportation",
        "交通出行",
        "🛸",
        [
            _field("transport_name", "交通方式", FIELD_TEXT),
            _field("speed", "速度", FIELD_TEXT),
            _field("carrier", "载体/工具", FIELD_TEXT),
            _field("cost", "费用", FIELD_TEXT),
            _field("route_network", "路线网络", FIELD_TEXTAREA),
            _field("limitation", "限制条件", FIELD_TEXTAREA),
        ],
    ),
    # 19. 通讯方式
    _category(
        "communication",
        "通讯方式",
        "📡",
        [
            _field("comm_name", "通讯方式", FIELD_TEXT),
            _field("comm_principle", "通讯原理", FIELD_TEXTAREA),
            _field("range", "通讯范围", FIELD_TEXT),
            _field("delay", "延迟", FIELD_TEXT),
            _field("cost", "费用", FIELD_TEXT),
            _field("security", "安全性", FIELD_SELECT, options=["公开", "加密", "绝对安全"]),
        ],
    ),
    # 20. 教育体系
    _category(
        "education",
        "教育体系",
        "🎓",
        [
            _field("edu_institution", "教育机构", FIELD_TEXT),
            _field("edu_stage", "教育阶段", FIELD_LIST),
            _field("curriculum", "课程设置", FIELD_TEXTAREA),
            _field("admission_condition", "入学条件", FIELD_TEXTAREA),
            _field("graduation_standard", "毕业标准", FIELD_TEXTAREA),
            _field("famous_alumni", "著名校友", FIELD_LIST),
        ],
    ),
    # 21. 军事体系
    _category(
        "military",
        "军事体系",
        "🛡️",
        [
            _field("army_name", "军队名称", FIELD_TEXT),
            _field("military_rank", "军衔体系", FIELD_TEXTAREA),
            _field("troop_composition", "兵种构成", FIELD_LIST),
            _field("weapon_equipment", "武器装备", FIELD_TEXTAREA),
            _field("tactics", "战术特色", FIELD_TEXTAREA),
            _field("famous_battle", "著名战役", FIELD_LIST),
        ],
    ),
    # 22. 法律司法
    _category(
        "law_justice",
        "法律司法",
        "⚖️",
        [
            _field("law_name", "法律名称", FIELD_TEXT),
            _field("legislative_body", "立法机构", FIELD_TEXT),
            _field("judicial_system", "司法体系", FIELD_TEXTAREA),
            _field("punishment_standard", "刑罚标准", FIELD_TEXTAREA),
            _field("trial_process", "审判流程", FIELD_TEXTAREA),
            _field("famous_case", "著名案例", FIELD_LIST),
        ],
    ),
    # 23. 医药健康
    _category(
        "medicine_health",
        "医药健康",
        "🌿",
        [
            _field("medicine_system", "医学体系", FIELD_TEXT),
            _field("diagnosis_method", "诊断方式", FIELD_TEXTAREA),
            _field("treatment_method", "治疗方式", FIELD_TEXTAREA),
            _field("common_disease", "常见疾病", FIELD_LIST),
            _field("famous_doctor", "名医", FIELD_LIST),
            _field("medical_holy_land", "医学圣地", FIELD_TEXT),
        ],
    ),
    # 24. 饮食文化
    _category(
        "food_cuisine",
        "饮食文化",
        "🍜",
        [
            _field("staple_food", "主食", FIELD_TEXT),
            _field("cuisine_style", "菜系风格", FIELD_TEXTAREA),
            _field("famous_dish", "名菜", FIELD_LIST),
            _field("drink_culture", "饮品文化", FIELD_TEXTAREA),
            _field("table_manner", "餐桌礼仪", FIELD_TEXTAREA),
            _field("food_taboo", "饮食禁忌", FIELD_TEXTAREA),
        ],
    ),
    # 25. 服饰时尚
    _category(
        "clothing_fashion",
        "服饰时尚",
        "👘",
        [
            _field("daily_wear", "日常服饰", FIELD_TEXTAREA),
            _field("formal_wear", "正式礼服", FIELD_TEXTAREA),
            _field("material", "面料材质", FIELD_LIST),
            _field("color_symbolism", "颜色象征", FIELD_TEXTAREA),
            _field("accessory", "配饰", FIELD_LIST),
            _field("dress_code", "着装规范", FIELD_TEXTAREA),
        ],
    ),
    # 26. 建筑风格
    _category(
        "architecture",
        "建筑风格",
        "🏛️",
        [
            _field("building_style", "建筑风格", FIELD_TEXT),
            _field("material", "建筑材料", FIELD_LIST),
            _field("structure_feature", "结构特色", FIELD_TEXTAREA),
            _field("famous_building", "著名建筑", FIELD_LIST),
            _field("layout_principle", "布局原则", FIELD_TEXTAREA),
            _field("defense_feature", "防御特色", FIELD_TEXTAREA),
        ],
    ),
    # 27. 音乐艺术
    _category(
        "music_art",
        "音乐艺术",
        "🎵",
        [
            _field("music_style", "音乐风格", FIELD_TEXTAREA),
            _field("instrument", "乐器", FIELD_LIST),
            _field("art_form", "艺术形式", FIELD_LIST),
            _field("famous_artist", "著名艺术家", FIELD_LIST),
            _field("art_theme", "艺术主题", FIELD_TEXTAREA),
            _field("performance_venue", "演出场所", FIELD_TEXT),
        ],
    ),
    # 28. 体育娱乐
    _category(
        "sports_entertainment",
        "体育娱乐",
        "🎮",
        [
            _field("sport_name", "运动项目", FIELD_TEXT),
            _field("rules", "规则", FIELD_TEXTAREA),
            _field("entertainment", "娱乐活动", FIELD_LIST),
            _field("gambling", "博彩玩法", FIELD_TEXTAREA),
            _field("famous_event", "著名赛事", FIELD_LIST),
            _field("celebrity", "名人", FIELD_LIST),
        ],
    ),
    # 29. 禁忌避讳
    _category(
        "taboo_prohibition",
        "禁忌避讳",
        "🚫",
        [
            _field("taboo_name", "禁忌名称", FIELD_TEXT),
            _field(
                "taboo_type",
                "禁忌类型",
                FIELD_SELECT,
                options=["语言", "行为", "物品", "数字", "时间", "其他"],
            ),
            _field("taboo_content", "禁忌内容", FIELD_TEXTAREA),
            _field("origin", "起源", FIELD_TEXTAREA),
            _field("violation_consequence", "触犯后果", FIELD_TEXTAREA),
            _field("scope", "适用范围", FIELD_TEXT),
        ],
    ),
    # 30. 预言征兆
    _category(
        "prophecy_omen",
        "预言征兆",
        "🔮",
        [
            _field("prophecy_name", "预言名称", FIELD_TEXT),
            _field("prophet", "预言者", FIELD_TEXT),
            _field("prophecy_content", "预言内容", FIELD_TEXTAREA),
            _field("omen_sign", "征兆表现", FIELD_TEXTAREA),
            _field(
                "fulfillment_status",
                "应验状态",
                FIELD_SELECT,
                options=["未应验", "部分应验", "已应验", "被打破"],
            ),
            _field("related_event", "关联事件", FIELD_TEXT),
        ],
    ),
]


# ─── 便捷查询函数 ───────────────────────────────────────────────────────────
def get_all_categories() -> list[dict[str, Any]]:
    """返回所有类别 Schema 列表（深拷贝，防止外部修改）。"""
    import copy

    return copy.deepcopy(WORLD_SETTING_CATEGORIES)


def get_category(category_id: str) -> dict[str, Any] | None:
    """根据 category_id 获取类别定义。"""
    for cat in WORLD_SETTING_CATEGORIES:
        if cat["category_id"] == category_id:
            import copy

            return copy.deepcopy(cat)
    return None


def get_category_count() -> int:
    """返回类别总数。"""
    return len(WORLD_SETTING_CATEGORIES)


def get_field_types() -> list[str]:
    """返回支持的字段类型列表。"""
    return [FIELD_TEXT, FIELD_NUMBER, FIELD_SELECT, FIELD_MULTISELECT, FIELD_TEXTAREA, FIELD_LIST]
