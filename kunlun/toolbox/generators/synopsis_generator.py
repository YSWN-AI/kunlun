"""
简介生成器 — 纯模板+规则，离线可用

生成黄金三章格式的小说简介（200-300字），包含：
- 主角身份与困境
- 金手指/转折点
- 核心冲突与目标
- 悬念收尾
"""

from __future__ import annotations

from kunlun.toolbox.models import SynopsisGenerateRequest, SynopsisResult

# ── 简介模板库 ────────────────────────────────────────────

_SYNOPSIS_TEMPLATES: list[str] = [
    # 模板1：逆袭流
    (
        "{protagonist}，本是{status}，却因{reason}陷入{predicament}。\n"
        "就在他万念俱灰之际，{cheat_hint}悄然觉醒——{cheat_desc}。\n"
        "从此，他踏上{path}之路。{conflict_hint}\n"
        "当{enemy}的阴影笼罩{world}，他能否{goal}？\n"
        "一切，尽在《{title}》。"
    ),
    # 模板2：重生流
    (
        "重生归来，{protagonist}回到了{timepoint}。\n"
        "上一世，他{regret}，最终{ending}。\n"
        "这一世，他誓要{resolve}！\n"
        "{cheat_hint}在手，{conflict_hint}\n"
        "且看他如何{goal}，改写《{title}》的命运。"
    ),
    # 模板3：系统流
    (
        "【叮——{system_name}已绑定宿主。】\n"
        "{protagonist}，{status}，意外获得{system_name}。\n"
        "任务一：{task}。奖励：{reward}。\n"
        "在{world}中，{conflict_hint}\n"
        "他将凭借系统，{goal}。\n"
        "《{title}》，一个{tag}的传奇就此展开。"
    ),
    # 模板4：悬念流
    (
        "{protagonist}从未想过，{inciting_incident}会改变他的一生。\n"
        "那一夜，{mystery}，他发现了{secret}。\n"
        "从那天起，{conflict_hint}\n"
        "有人要他死，有人要他活，而他要的是{goal}。\n"
        "《{title}》——当真相揭开，{world}将为之颤抖。"
    ),
    # 模板5：争霸流
    (
        "{world}，群雄并起，{chaos}。\n"
        "{protagonist}，{status}，于{starting_point}崛起。\n"
        "{cheat_hint}，让他拥有了{advantage}。\n"
        "{conflict_hint}\n"
        "他要{goal}，让{enemy}俯首称臣！\n"
        "《{title}》，且看{tag}如何登临绝巅。"
    ),
]

# 题材相关的填充词
_GENRE_FILLERS: dict[str, dict[str, str]] = {
    "玄幻": {
        "status": "一介废柴",
        "reason": "灵根尽毁",
        "predicament": "被宗门逐出、受尽白眼的境地",
        "cheat_hint": "上古传承",
        "cheat_desc": "可吞噬万物、推演功法、逆天改命",
        "path": "证道长生",
        "conflict_hint": "天骄林立、大道争锋，他以凡躯逆伐诸天！",
        "enemy": "天道",
        "world": "九州大地",
        "goal": "打破宿命、登临神帝之位",
        "timepoint": "百年之前",
        "regret": "错信他人、痛失挚爱",
        "ending": "身死道消、化为飞灰",
        "resolve": "逆天改命、护佑所爱",
        "system_name": "万界吞噬系统",
        "task": "在一个时辰内突破炼气期",
        "reward": "混沌灵体",
        "tag": "废柴逆袭",
        "inciting_incident": "一枚古朴的玉佩",
        "mystery": "宗门后山禁地发出异响",
        "secret": "自己竟是上古神族遗孤",
        "chaos": "万族争锋",
        "starting_point": "边陲小镇",
        "advantage": "越级挑战的资本",
    },
    "都市": {
        "status": "平凡的小人物",
        "reason": "一场意外",
        "predicament": "人生最低谷",
        "cheat_hint": "神秘传承",
        "cheat_desc": "通晓医术、透视万物、预知吉凶",
        "path": "逆袭人生",
        "conflict_hint": "豪门倾轧、商战暗涌，他以一己之力搅动风云！",
        "enemy": "幕后黑手",
        "world": "繁华都市",
        "goal": "站上巅峰、守护所爱之人",
        "timepoint": "十年之前",
        "regret": "家破人亡、一无所有",
        "ending": "含恨而终",
        "resolve": "复仇雪恨、重振家业",
        "system_name": "神级选择系统",
        "task": "三天内赚到第一个一百万",
        "reward": "商业天才光环",
        "tag": "草根逆袭",
        "inciting_incident": "一场突如其来的车祸",
        "mystery": "昏迷中听到神秘声音",
        "secret": "自己的身世远非表面那么简单",
        "chaos": "暗流涌动",
        "starting_point": "城中村出租屋",
        "advantage": "洞察人心的智慧",
    },
    "科幻": {
        "status": "底层机械师",
        "reason": "星际战争",
        "predicament": "被流放至废弃星球",
        "cheat_hint": "远古AI核心",
        "cheat_desc": "可解析科技、操控机械、进化意识",
        "path": "星际征途",
        "conflict_hint": "文明碰撞、种族存亡，他以智慧点燃银河烽火！",
        "enemy": "星际帝国",
        "world": "银河纪元",
        "goal": "重建文明、守护人类火种",
        "timepoint": "大灾变之前",
        "regret": "未能阻止文明陨落",
        "ending": "随舰队一同湮灭",
        "resolve": "拯救人类、改写历史",
        "system_name": "星际进化系统",
        "task": "修复一艘废弃星舰",
        "reward": "量子大脑",
        "tag": "废土崛起",
        "inciting_incident": "一段来自深空的信号",
        "mystery": "空间站全员失踪",
        "secret": "人类并非宇宙中唯一的智慧种族",
        "chaos": "文明更迭",
        "starting_point": "废弃空间站",
        "advantage": "超越时代的科技",
    },
}


def _get_filler(genre: str, key: str) -> str:
    """获取题材填充词，未知题材用玄幻兜底。"""
    fillers = _GENRE_FILLERS.get(genre)
    if fillers is None:
        for g, value in _GENRE_FILLERS.items():
            if g in genre:
                fillers = value
                break
    if fillers is None:
        fillers = _GENRE_FILLERS["玄幻"]
    return fillers.get(key, key)


def generate_synopsis(request: SynopsisGenerateRequest) -> SynopsisResult:
    """
    生成黄金三章格式简介。

    策略：
    1. 根据题材选择填充词
    2. 选择合适的模板（基于核心冲突关键词匹配）
    3. 填入用户提供的书名、主角、冲突
    4. 调整到目标字数范围
    """
    # 根据核心冲突选择模板
    conflict_lower = request.core_conflict.lower()
    template_idx = 0
    if "重生" in conflict_lower or "回到" in request.protagonist:
        template_idx = 1
    elif "系统" in conflict_lower or "任务" in conflict_lower:
        template_idx = 2
    elif "秘密" in conflict_lower or "真相" in conflict_lower or "谜" in conflict_lower:
        template_idx = 3
    elif "争霸" in conflict_lower or "天下" in conflict_lower or "帝" in conflict_lower:
        template_idx = 4

    template = _SYNOPSIS_TEMPLATES[template_idx]
    genre = request.genre

    # 构建填充字典
    fill = {
        "title": request.title,
        "protagonist": request.protagonist,
        "status": _get_filler(genre, "status"),
        "reason": _get_filler(genre, "reason"),
        "predicament": _get_filler(genre, "predicament"),
        "cheat_hint": _get_filler(genre, "cheat_hint"),
        "cheat_desc": _get_filler(genre, "cheat_desc"),
        "path": _get_filler(genre, "path"),
        "conflict_hint": request.core_conflict or _get_filler(genre, "conflict_hint"),
        "enemy": _get_filler(genre, "enemy"),
        "world": _get_filler(genre, "world"),
        "goal": _get_filler(genre, "goal"),
        "timepoint": _get_filler(genre, "timepoint"),
        "regret": _get_filler(genre, "regret"),
        "ending": _get_filler(genre, "ending"),
        "resolve": _get_filler(genre, "resolve"),
        "system_name": _get_filler(genre, "system_name"),
        "task": _get_filler(genre, "task"),
        "reward": _get_filler(genre, "reward"),
        "tag": _get_filler(genre, "tag"),
        "inciting_incident": _get_filler(genre, "inciting_incident"),
        "mystery": _get_filler(genre, "mystery"),
        "secret": _get_filler(genre, "secret"),
        "chaos": _get_filler(genre, "chaos"),
        "starting_point": _get_filler(genre, "starting_point"),
        "advantage": _get_filler(genre, "advantage"),
    }

    synopsis = template.format(**fill)
    word_count = len(synopsis.replace("\n", "").replace(" ", ""))

    return SynopsisResult(synopsis=synopsis, word_count=word_count)
