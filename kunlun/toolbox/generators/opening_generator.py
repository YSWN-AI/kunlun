"""
黄金开篇生成器 — 纯模板+规则，离线可用

生成3种开篇方案：冲突前置型、悬念设置型、场景代入型。
每种约500字。
"""

from __future__ import annotations

from kunlun.toolbox.models import OpeningGenerateRequest, OpeningResult, OpeningScheme

# ── 冲突前置型模板 ───────────────────────────────────────

_CONFLICT_FIRST_TPL = (
    "{opening_line}\n\n"
    "{protagonist}死死盯着眼前的{enemy}，指甲深深嵌入掌心。\n"
    '"{taunt}" {enemy}冷笑一声，{enemy_action}。\n\n'
    "就在一刻钟前，{inciting_event}。{protagonist}怎么也想不到，"
    "{betrayal}。\n\n"
    '"为什么？" {protagonist}的声音沙哑得不像自己。\n'
    '"为什么？" {enemy}像是听到了天大的笑话，"{reason}"\n\n'
    "{protagonist}闭上眼，脑海中闪过{memory}。\n"
    "再睁开时，眼中已没有半分犹豫——\n"
    "{cheat_activation}\n\n"
    '"既然你们{provocation}，" {protagonist}缓缓抬起手，'
    '"那就{threat}。"\n\n'
    "{closing_line}"
)

# ── 悬念设置型模板 ───────────────────────────────────────

_MYSTERY_TPL = (
    "{opening_line}\n\n"
    "{protagonist}是被{sound}惊醒的。\n\n"
    "窗外，{environment}。这本该是{normal_time}，但{abnormal}。\n\n"
    "{protagonist}翻身下床，脚刚触地就僵住了——\n"
    "{discovery}\n\n"
    '"不可能……" {protagonist}喃喃自语，{reaction}。\n'
    "这已经是第{count}次了。每一次，{pattern}。\n\n"
    "就在这时，{trigger}。\n"
    "{protagonist}猛地回头，{sight}。\n\n"
    '"你终于发现了。"一个{voice_desc}的声音从{voice_source}传来。\n'
    '{protagonist}瞳孔骤缩："{exclamation}"\n\n'
    '"{reveal_hint}" 那声音说，"{choice_hint}"\n\n'
    "{closing_line}"
)

# ── 场景代入型模板 ───────────────────────────────────────

_SCENE_TPL = (
    "{opening_line}\n\n"
    "{scene_description}\n\n"
    "{protagonist}站在{location}，{sensory_detail}。\n"
    "今天是{special_day}，按照{tradition}，{expected_event}。\n\n"
    "人群中，{crowd_detail}。{protagonist}的目光扫过众人，"
    "最终落在{focus_target}身上。\n\n"
    '"{dialogue_1}" 有人在旁边说。\n'
    "{protagonist}没有回答，只是{action}。\n\n"
    "就在{expected_event}即将开始的瞬间——\n"
    "{disruption}\n\n"
    "全场寂静。\n"
    "{protagonist}{protagonist_reaction}，{protagonist_action}。\n\n"
    '"{dialogue_2}" {protagonist}轻声说，声音不大，却让所有人都听清了。\n\n'
    "{closing_line}"
)

# 题材填充
_GENRE_OPENING: dict[str, dict[str, str]] = {
    "玄幻": {
        "opening_line": "血，顺着剑锋滴落，在青石板上绽开一朵朵暗红的花。",
        "enemy": "宗门大师兄",
        "taunt": "废物就是废物，连一招都接不住。",
        "enemy_action": "长剑斜指，剑气撕裂了{protagonist}的衣袖",
        "inciting_event": "宗门大比的擂台上，他被人当众废掉了灵根",
        "betrayal": "那个他视若亲兄的人，会在背后捅他一刀",
        "reason": "在这个弱肉强食的世界，善良本身就是一种罪。",
        "memory": "十年前，那个人跪在雪地里求他收留的模样",
        "cheat_activation": "丹田深处，一缕被封印了十八年的气息，悄然苏醒。",
        "provocation": "要赶尽杀绝",
        "threat": "别怪我血洗此山",
        "closing_line": "那一天，整个宗门都记住了这个名字。",
        "sound": "一阵急促的敲门声",
        "environment": "月光惨白，远处传来妖兽的嘶吼",
        "normal_time": "丑时三刻",
        "abnormal": "整个宗门的护山大阵，正在以肉眼可见的速度崩塌",
        "discovery": "墙上的影子，在没有光源的情况下，正在自己动。",
        "reaction": "后背瞬间被冷汗浸透",
        "count": "七",
        "pattern": "醒来后，他都会发现自己多了一段不属于自己的记忆",
        "trigger": "桌上的铜镜，映出了一张陌生的脸",
        "sight": "镜中人正对着他微笑，而他自己，分明面无表情",
        "voice_desc": "苍老而疲惫",
        "voice_source": "铜镜深处",
        "exclamation": "你是谁？！",
        "reveal_hint": "我是谁不重要，重要的是——你已经死了三次了。",
        "choice_hint": "这一次，你还要重蹈覆辙吗？",
        "scene_description": (
            "青云宗山门之前，万人空巷。\n"
            "九十九级白玉台阶从山脚绵延至山顶，每一级都刻着上古符文，"
            "在晨光中流转着淡淡的光晕。台阶两侧，各宗弟子肃然而立，"
            "衣袂飘飘，剑气冲天。"
        ),
        "location": "山门前的广场上",
        "sensory_detail": "微风中夹杂着灵药的清香和淡淡的血腥气",
        "special_day": "百年一度的宗门大比",
        "tradition": "惯例",
        "expected_event": "新任宗主的接任大典",
        "crowd_detail": "议论声此起彼伏，所有人都在猜测今年的黑马会是谁",
        "focus_target": "广场中央那个孤零零的身影",
        "dialogue_1": "听说那小子灵根尽毁，还来凑什么热闹？",
        "action": "微微攥紧了拳头",
        "disruption": "一道血色剑光从天而降，直直劈向新任宗主的宝座！",
        "protagonist_reaction": "眼神一凛",
        "protagonist_action": "身形如电般掠出",
        "dialogue_2": "这宗主之位，你们谁想要，就来拿。",
    },
    "都市": {
        "opening_line": "雨水砸在挡风玻璃上，模糊了霓虹，也模糊了前方的路。",
        "enemy": "昔日最好的兄弟",
        "taunt": "你以为你赢了？从一开始，你就是枚棋子。",
        "enemy_action": "将一份文件甩在{protagonist}脸上",
        "inciting_event": "公司上市前夜，他被董事会联合踢出了局",
        "betrayal": "那个他一手提拔起来的人，会联合外人夺走他的一切",
        "reason": "这个世界只看结果，不看过程。你太天真了。",
        "memory": "十年前，两个人在地下室里分吃一碗泡面的夜晚",
        "cheat_activation": "口袋里的手机突然震动，一条匿名短信只有四个字：『按我说的做。』",
        "provocation": "要把我踩在脚下",
        "threat": "就准备好承受我的报复",
        "closing_line": "他发动了汽车，驶入雨幕。属于他的战争，才刚刚开始。",
        "sound": "手机铃声",
        "environment": "城市的灯火在雨中晕开，像一幅褪色的油画",
        "normal_time": "凌晨两点",
        "abnormal": "他明明记得自己把手机关了机",
        "discovery": "手机屏幕上显示着一条未读短信，发送时间是——明天。",
        "reaction": "手指微微颤抖",
        "count": "三",
        "pattern": "他都会收到一条来自『未来』的短信",
        "trigger": "窗外，一辆黑色轿车无声地停在了楼下",
        "sight": "车窗缓缓降下，驾驶座上空无一人",
        "voice_desc": "机械而冰冷",
        "voice_source": "手机听筒里",
        "exclamation": "这到底是怎么回事？！",
        "reveal_hint": "你已经死了。现在的你，是第无数次重启。",
        "choice_hint": "这一次，你想改变结局吗？",
        "scene_description": (
            "国际会议中心，水晶吊灯将大厅映照得如同白昼。\n"
            "衣香鬓影，觥筹交错。城中名流汇聚于此，"
            "等待着年度经济人物的揭晓。"
        ),
        "location": "大厅的角落",
        "sensory_detail": "香槟的气泡在杯中升腾，远处传来爵士乐的旋律",
        "special_day": "年度经济论坛",
        "tradition": "惯例",
        "expected_event": "最年轻企业家的颁奖仪式",
        "crowd_detail": "闪光灯此起彼伏，记者们围在台前",
        "focus_target": "台上那个意气风发的年轻人",
        "dialogue_1": "听说他白手起家，三年就做到了行业第一。",
        "action": "端起酒杯，轻轻晃了晃",
        "disruption": "大屏幕突然黑屏，随后出现了一行触目惊心的字——『你们都被骗了。』",
        "protagonist_reaction": "嘴角勾起一抹弧度",
        "protagonist_action": "放下酒杯，缓步走向台前",
        "dialogue_2": "各位，好戏才刚刚开始。",
    },
}


def _get_text(genre: str, key: str) -> str:
    data = _GENRE_OPENING.get(genre)
    if data is None:
        for g, value in _GENRE_OPENING.items():
            if g in genre:
                data = value
                break
    if data is None:
        data = _GENRE_OPENING["玄幻"]
    return data.get(key, key)


def _fill_template(template: str, genre: str, protagonist: str, core_conflict: str) -> str:
    """填充模板中的占位符。"""
    result = template.replace("{protagonist}", protagonist or "他")
    for key in _GENRE_OPENING.get(genre, _GENRE_OPENING["玄幻"]):
        result = result.replace("{" + key + "}", _get_text(genre, key))
    # 注入核心冲突
    if core_conflict:
        result = result.replace("核心冲突", core_conflict)
    return result


def generate_opening(request: OpeningGenerateRequest) -> OpeningResult:
    """
    生成3种黄金开篇方案。

    策略：
    1. 冲突前置型：直接从高潮场景切入，快速建立张力
    2. 悬念设置型：用异常现象和谜团吸引读者
    3. 场景代入型：先构建世界观和氛围，再打破平静
    """
    protagonist = request.protagonist or "少年"
    genre = request.genre

    schemes = [
        OpeningScheme(
            scheme_type="冲突前置型",
            content=_fill_template(_CONFLICT_FIRST_TPL, genre, protagonist, request.core_conflict),
        ),
        OpeningScheme(
            scheme_type="悬念设置型",
            content=_fill_template(_MYSTERY_TPL, genre, protagonist, request.core_conflict),
        ),
        OpeningScheme(
            scheme_type="场景代入型",
            content=_fill_template(_SCENE_TPL, genre, protagonist, request.core_conflict),
        ),
    ]

    return OpeningResult(schemes=schemes)
