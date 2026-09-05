"""
名字生成器 — 纯模板+规则，离线可用

支持角色/地点/物品/功法四种类型，古风/现代/西方三种风格。
"""

from __future__ import annotations

import random

from kunlun.toolbox.models import NameGenerateRequest, NameResult

# ── 古风角色名 ───────────────────────────────────────────

_ANCIENT_SURNAMES = [
    "林",
    "苏",
    "叶",
    "萧",
    "楚",
    "顾",
    "沈",
    "陆",
    "江",
    "白",
    "秦",
    "墨",
    "夜",
    "云",
    "风",
    "花",
    "雪",
    "月",
    "星",
    "辰",
    "龙",
    "凤",
    "轩辕",
    "上官",
    "欧阳",
    "司马",
    "诸葛",
    "东方",
    "南宫",
    "北冥",
]

_ANCIENT_MALE_GIVEN = [
    "绝尘",
    "无忌",
    "逍遥",
    "问天",
    "凌云",
    "长空",
    "惊鸿",
    "破晓",
    "寒川",
    "煜城",
    "子轩",
    "墨渊",
    "夜辰",
    "风烈",
    "剑魂",
    "弑天",
    "逆鳞",
    "苍穹",
    "玄烨",
    "青阳",
    "修远",
    "明诚",
    "知行",
    "怀瑾",
    "握瑜",
    "景行",
    "观澜",
    "听潮",
    "观星",
    "望月",
]

_ANCIENT_FEMALE_GIVEN = [
    "若曦",
    "语嫣",
    "清欢",
    "素心",
    "凝霜",
    "如烟",
    "若水",
    "倾城",
    "绝世",
    "无双",
    "梦璃",
    "雪琪",
    "灵儿",
    "月如",
    "阿奴",
    "婉儿",
    "芷若",
    "赵敏",
    "黄蓉",
    "小龙女",
    "扶苏",
    "采薇",
    "蒹葭",
    "白露",
    "清秋",
    "暮雪",
    "朝颜",
    "夕颜",
    "夕颜",
    "惊鸿",
]

# ── 现代角色名 ───────────────────────────────────────────

_MODERN_SURNAMES = [
    "李",
    "王",
    "张",
    "刘",
    "陈",
    "杨",
    "赵",
    "黄",
    "周",
    "吴",
    "徐",
    "孙",
    "胡",
    "朱",
    "高",
    "林",
    "何",
    "郭",
    "马",
    "罗",
]

_MODERN_MALE_GIVEN = [
    "浩然",
    "子涵",
    "宇轩",
    "梓豪",
    "俊杰",
    "志强",
    "建国",
    "伟",
    "磊",
    "洋",
    "明",
    "超",
    "涛",
    "斌",
    "鹏",
    "华",
    "峰",
    "健",
    "俊",
    "飞",
    "思远",
    "天佑",
    "博文",
    "泽宇",
    "铭轩",
    "晨曦",
    "皓然",
    "锦程",
    "睿",
    "昊",
]

_MODERN_FEMALE_GIVEN = [
    "芳",
    "娜",
    "敏",
    "静",
    "丽",
    "强",
    "磊",
    "洋",
    "艳",
    "勇",
    "军",
    "杰",
    "娟",
    "涛",
    "明",
    "超",
    "秀英",
    "霞",
    "平",
    "刚",
    "梓涵",
    "欣怡",
    "子萱",
    "雨桐",
    "诗涵",
    "梦琪",
    "若曦",
    "语嫣",
    "思颖",
    "佳怡",
]

# ── 西方角色名 ───────────────────────────────────────────

_WESTERN_FIRST_MALE = [
    "Arthur",
    "Lancelot",
    "Gawain",
    "Percival",
    "Tristan",
    "Galahad",
    "Alexander",
    "Caesar",
    "Augustus",
    "Maximus",
    "Lucius",
    "Marcus",
    "William",
    "Richard",
    "Henry",
    "Edward",
    "Charles",
    "George",
    "Dante",
    "Virgil",
    "Orlando",
    "Romeo",
    "Hamlet",
    "Othello",
]

_WESTERN_FIRST_FEMALE = [
    "Guinevere",
    "Elaine",
    "Morgana",
    "Isolde",
    "Brunhilde",
    "Sigrid",
    "Cleopatra",
    "Zenobia",
    "Boudica",
    "Joan",
    "Eleanor",
    "Isabella",
    "Juliet",
    "Ophelia",
    "Desdemona",
    "Portia",
    "Rosalind",
    "Viola",
    "Aurora",
    "Luna",
    "Stella",
    "Celeste",
    "Seraphina",
    "Evangeline",
]

_WESTERN_TITLES = [
    "the Great",
    "the Lionheart",
    "the Wise",
    "the Conqueror",
    "the Magnificent",
    "of Camelot",
    "of Avalon",
    "of Winterfell",
    "of Storm's End",
    "the Undying",
]

# ── 地点名词库 ───────────────────────────────────────────

_ANCIENT_LOCATION_PREFIX = [
    "青云",
    "玄天",
    "紫霄",
    "碧落",
    "黄泉",
    "幽冥",
    "蓬莱",
    "昆仑",
    "方丈",
    "瀛洲",
    "万剑",
    "百花",
    "落霞",
    "孤鹜",
    "秋水",
    "长天",
    "明月",
    "清风",
    "细雨",
    "斜阳",
]

_ANCIENT_LOCATION_SUFFIX = [
    "山",
    "峰",
    "崖",
    "谷",
    "洞",
    "府",
    "宫",
    "殿",
    "阁",
    "楼",
    "宗",
    "门",
    "派",
    "帮",
    "会",
    "盟",
    "城",
    "镇",
    "村",
    "岛",
    "秘境",
    "禁地",
    "遗迹",
    "废墟",
    "战场",
    "陵园",
    "祭坛",
    "神殿",
    "圣山",
    "魔渊",
]

_MODERN_LOCATIONS = [
    "中央公园",
    "时代广场",
    "金融中心",
    "科技园",
    "大学城",
    "老城区",
    "滨江大道",
    "CBD",
    "创意园",
    "艺术区",
    "商业街",
    "美食街",
    "高铁站",
    "机场",
    "码头",
    "地铁站",
    "立交桥",
    "步行街",
]

_WESTERN_LOCATIONS = [
    "Stormwind",
    "Ironforge",
    "Darnassus",
    "Orgrimmar",
    "Undercity",
    "Camelot",
    "Avalon",
    "Asgard",
    "Olympus",
    "Valhalla",
    "Winterfell",
    "King's Landing",
    "Casterly Rock",
    "Highgarden",
    "Dorne",
    "Hogwarts",
    "Diagon Alley",
    "Hogsmeade",
    "Minas Tirith",
    "Rivendell",
]

# ── 物品名词库 ───────────────────────────────────────────

_ANCIENT_ITEM_PREFIX = [
    "太虚",
    "混元",
    "太极",
    "两仪",
    "三才",
    "四象",
    "五行",
    "六合",
    "七星",
    "八卦",
    "九转",
    "十方",
    "百炼",
    "千钧",
    "万劫",
    "无量",
    "永恒",
    "不朽",
    "封神",
    "诛仙",
]

_ANCIENT_ITEM_SUFFIX = [
    "剑",
    "刀",
    "枪",
    "戟",
    "斧",
    "钺",
    "钩",
    "叉",
    "鞭",
    "锏",
    "锤",
    "爪",
    "镗",
    "棍",
    "槊",
    "棒",
    "弓",
    "弩",
    "盾",
    "甲",
    "丹",
    "药",
    "符",
    "阵",
    "盘",
    "镜",
    "铃",
    "印",
    "珠",
    "塔",
]

_MODERN_ITEMS = [
    "智能手环",
    "量子芯片",
    "纳米机器人",
    "基因药剂",
    "脑机接口",
    "全息投影",
    "反重力装置",
    "时空穿梭机",
    "能量护盾",
    "人工智能核心",
]

_WESTERN_ITEMS = [
    "Excalibur",
    "Mjolnir",
    "Gungnir",
    "Draupnir",
    "Anduril",
    "the One Ring",
    "the Elder Wand",
    "the Philosopher's Stone",
    "the Ark of the Covenant",
    "the Holy Grail",
]

# ── 功法名词库 ───────────────────────────────────────────

_TECHNIQUE_PREFIX = [
    "太虚",
    "混元",
    "太极",
    "两仪",
    "三才",
    "四象",
    "五行",
    "六合",
    "七星",
    "八卦",
    "九转",
    "大日",
    "明月",
    "星辰",
    "雷霆",
    "烈焰",
    "寒冰",
    "疾风",
    "大地",
    "深渊",
]

_TECHNIQUE_SUFFIX = [
    "真经",
    "宝典",
    "秘录",
    "神诀",
    "仙法",
    "魔功",
    "妖术",
    "鬼典",
    "圣典",
    "天书",
    "剑诀",
    "刀法",
    "枪法",
    "拳法",
    "掌法",
    "指法",
    "腿法",
    "身法",
    "心法",
    "功法",
    "十八式",
    "三十六变",
    "七十二般",
    "一百零八式",
    "九重",
    "三层",
    "四篇",
    "六卷",
]


def _gen_character_names(style: str, gender: str, count: int, rng: random.Random) -> list[str]:
    """生成角色名。"""
    names: list[str] = []
    seen: set[str] = set()

    if style == "ancient":
        surnames = _ANCIENT_SURNAMES
        if gender == "女":
            given = _ANCIENT_FEMALE_GIVEN
        elif gender == "男":
            given = _ANCIENT_MALE_GIVEN
        else:
            given = _ANCIENT_MALE_GIVEN + _ANCIENT_FEMALE_GIVEN
        while len(names) < count:
            name = rng.choice(surnames) + rng.choice(given)
            if name not in seen:
                seen.add(name)
                names.append(name)
    elif style == "modern":
        surnames = _MODERN_SURNAMES
        if gender == "女":
            given = _MODERN_FEMALE_GIVEN
        elif gender == "男":
            given = _MODERN_MALE_GIVEN
        else:
            given = _MODERN_MALE_GIVEN + _MODERN_FEMALE_GIVEN
        while len(names) < count:
            name = rng.choice(surnames) + rng.choice(given)
            if name not in seen:
                seen.add(name)
                names.append(name)
    else:  # western
        if gender == "女":
            first = _WESTERN_FIRST_FEMALE
        elif gender == "男":
            first = _WESTERN_FIRST_MALE
        else:
            first = _WESTERN_FIRST_MALE + _WESTERN_FIRST_FEMALE
        while len(names) < count:
            name = rng.choice(first)
            if rng.random() < 0.3:
                name += " " + rng.choice(_WESTERN_TITLES)
            if name not in seen:
                seen.add(name)
                names.append(name)

    return names


def _gen_location_names(style: str, count: int, rng: random.Random) -> list[str]:
    """生成地点名。"""
    names: list[str] = []
    seen: set[str] = set()

    if style == "ancient":
        while len(names) < count:
            name = rng.choice(_ANCIENT_LOCATION_PREFIX) + rng.choice(_ANCIENT_LOCATION_SUFFIX)
            if name not in seen:
                seen.add(name)
                names.append(name)
    elif style == "modern":
        while len(names) < count:
            name = rng.choice(_MODERN_LOCATIONS)
            if name not in seen:
                seen.add(name)
                names.append(name)
    else:
        while len(names) < count:
            name = rng.choice(_WESTERN_LOCATIONS)
            if name not in seen:
                seen.add(name)
                names.append(name)

    return names


def _gen_item_names(style: str, count: int, rng: random.Random) -> list[str]:
    """生成物品名。"""
    names: list[str] = []
    seen: set[str] = set()

    if style == "ancient":
        while len(names) < count:
            name = rng.choice(_ANCIENT_ITEM_PREFIX) + rng.choice(_ANCIENT_ITEM_SUFFIX)
            if name not in seen:
                seen.add(name)
                names.append(name)
    elif style == "modern":
        while len(names) < count:
            name = rng.choice(_MODERN_ITEMS)
            if name not in seen:
                seen.add(name)
                names.append(name)
    else:
        while len(names) < count:
            name = rng.choice(_WESTERN_ITEMS)
            if name not in seen:
                seen.add(name)
                names.append(name)

    return names


def _gen_technique_names(style: str, count: int, rng: random.Random) -> list[str]:
    """生成功法名。"""
    names: list[str] = []
    seen: set[str] = set()

    if style == "ancient":
        while len(names) < count:
            name = rng.choice(_TECHNIQUE_PREFIX) + rng.choice(_TECHNIQUE_SUFFIX)
            if name not in seen:
                seen.add(name)
                names.append(name)
    elif style == "modern":
        modern_tech = [
            "量子呼吸法",
            "基因强化术",
            "神经同步训练",
            "能量循环体系",
            "意识扩展法",
            "纳米修复术",
            "时空感知训练",
            "反重力体术",
        ]
        while len(names) < count:
            name = rng.choice(modern_tech)
            if name not in seen:
                seen.add(name)
                names.append(name)
    else:
        western_tech = [
            "Arcane Artes",
            "Battle Meditation",
            "Chi Flow",
            "Elemental Mastery",
            "Shadow Step",
            "Holy Light",
            "Dark Ritual",
            "Dragon Style",
        ]
        while len(names) < count:
            name = rng.choice(western_tech)
            if name not in seen:
                seen.add(name)
                names.append(name)

    return names


def generate_names(request: NameGenerateRequest) -> NameResult:
    """
    生成名字列表。

    策略：
    1. 根据类型选择对应的词库
    2. 根据风格选择前缀/后缀组合方式
    3. 随机组合并去重
    """
    rng = random.Random(hash(f"{request.name_type}:{request.style}:{request.gender}") & 0xFFFFFFFF)

    if request.name_type == "character":
        names = _gen_character_names(request.style, request.gender, request.count, rng)
    elif request.name_type == "location":
        names = _gen_location_names(request.style, request.count, rng)
    elif request.name_type == "item":
        names = _gen_item_names(request.style, request.count, rng)
    else:  # technique
        names = _gen_technique_names(request.style, request.count, rng)

    return NameResult(names=names)
