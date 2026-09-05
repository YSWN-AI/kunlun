"""
大纲生成器 — 纯模板+规则，离线可用

生成卷级大纲（5-10卷），支持三幕式和英雄之旅两种结构。
每卷包含：标题、核心事件、结局转折。
"""
# mypy: ignore-errors

from __future__ import annotations

from kunlun.toolbox.models import OutlineGenerateRequest, OutlineResult, VolumeOutline

# ── 三幕式卷阶段模板 ─────────────────────────────────────

_THREE_ACT_PHASES: list[dict[str, str]] = [
    # 第一幕：开局（1-2卷）
    {
        "phase": "开局",
        "title_pattern": "{keyword}初显",
        "events": [
            "主角在{starting_point}过着{status}的生活",
            "一场{inciting_event}打破了平静",
            "主角意外获得{cheat}，命运开始转折",
            "初次展露锋芒，引起{first_rival}注意",
        ],
        "twist": "主角发现{secret}，意识到一切并非偶然",
    },
    {
        "phase": "入局",
        "title_pattern": "风起{location}",
        "events": [
            "主角进入{new_location}，面对全新挑战",
            "结识{ally}，组建初步班底",
            "与{rival}发生正面冲突，惨胜",
            "实力突破至{milestone}，获得{resource}",
        ],
        "twist": "{ally}身份存疑，背后似乎另有图谋",
    },
    # 第二幕：发展（3-6卷）
    {
        "phase": "成长",
        "title_pattern": "{keyword}之路",
        "events": [
            "主角深入{domain}探索，揭开{world_secret}",
            "遭遇{strong_enemy}，陷入绝境",
            "{cheat}进化，解锁{new_ability}",
            "反败为胜，名震{region}",
        ],
        "twist": "{strong_enemy}只是棋子，真正的幕后黑手浮现",
    },
    {
        "phase": "扬名",
        "title_pattern": "名动{region}",
        "events": [
            "主角参加{competition}，一路过关斩将",
            "揭露{conspiracy}，拯救{group}",
            "实力达到{milestone2}，获得{title}",
            "与{love_interest}感情升温",
        ],
        "twist": "{competition}的主办方与{enemy}暗中勾结",
    },
    {
        "phase": "危机",
        "title_pattern": "风雨欲来",
        "events": [
            "{enemy}发动总攻，{location}陷入危机",
            "主角力战不敌，身受重伤",
            "{ally}为掩护主角牺牲/背叛",
            "主角被迫退守{safe_place}",
        ],
        "twist": "主角在绝境中觉醒{ultimate_ability}",
    },
    {
        "phase": "反击",
        "title_pattern": "绝地反击",
        "events": [
            "主角在{safe_place}闭关修炼，实力暴涨",
            "联合{alliance}，组建反击力量",
            "逐一拔除{enemy}的势力据点",
            "与{enemy}的先锋展开决战",
        ],
        "twist": "{enemy}的真正目的是{ultimate_goal}",
    },
    # 第三幕：高潮+结局（7-8卷）
    {
        "phase": "决战",
        "title_pattern": "终局之战",
        "events": [
            "主角率军攻入{enemy_base}",
            "层层突破，与{enemy}的核心战力对决",
            "{love_interest}陷入险境，主角爆发",
            "最终与{enemy}正面交锋",
        ],
        "twist": "{enemy}与主角有着{connection}的渊源",
    },
    {
        "phase": "新篇",
        "title_pattern": "{keyword}永恒",
        "events": [
            "主角击败{enemy}，{world}恢复和平",
            "整顿秩序，建立{new_order}",
            "与{love_interest}修成正果",
            "远方传来{new_threat}的消息，故事未完待续",
        ],
        "twist": "{new_threat}的实力远超{enemy}，新的征程即将开始",
    },
]

# ── 英雄之旅阶段 ─────────────────────────────────────────

_HERO_JOURNEY_PHASES: list[dict[str, str]] = [
    {
        "phase": "平凡世界",
        "title_pattern": "寻常{location}",
        "events": [
            "主角在{starting_point}过着平凡生活",
            "展示主角的{personality}特质",
            "内心深处渴望{desire}",
            "日常中埋下{foreshadow}伏笔",
        ],
        "twist": "{inciting_event}的征兆悄然出现",
    },
    {
        "phase": "冒险召唤",
        "title_pattern": "命运召唤",
        "events": [
            "{inciting_event}发生，打破平静",
            "主角获得{cheat}或发现{secret}",
            "导师{mentor}出现，指引方向",
            "主角犹豫是否踏上旅程",
        ],
        "twist": "{mentor}隐瞒了关键信息",
    },
    {
        "phase": "跨越门槛",
        "title_pattern": "踏入{new_world}",
        "events": [
            "主角下定决心，进入{new_world}",
            "遭遇第一道考验{first_test}",
            "结识{ally}，获得帮助",
            "初步了解{new_world}的规则",
        ],
        "twist": "{first_test}背后隐藏着{hidden_agenda}",
    },
    {
        "phase": "试炼之路",
        "title_pattern": "荆棘满途",
        "events": [
            "主角面临{trials}的连续考验",
            "与{rival}亦敌亦友",
            "{cheat}逐渐成长，能力提升",
            "发现{world_truth}的碎片",
        ],
        "twist": "{ally}竟是{enemy}安插的眼线",
    },
    {
        "phase": "最深洞穴",
        "title_pattern": "至暗时刻",
        "events": [
            "主角进入{danger_zone}，面对最大恐惧",
            "{mentor}牺牲，主角痛失指引",
            "信念动摇，几乎放弃",
            "在{inner_struggle}中重新找到方向",
        ],
        "twist": "{mentor}的牺牲另有深意",
    },
    {
        "phase": "终极考验",
        "title_pattern": "浴火重生",
        "events": [
            "主角与{enemy}展开决战",
            "经历{death_and_rebirth}的蜕变",
            "获得{ultimate_reward}",
            "实力达到前所未有的高度",
        ],
        "twist": "{ultimate_reward}需要付出{price}",
    },
    {
        "phase": "回归之路",
        "title_pattern": "归途漫漫",
        "events": [
            "主角带着{ultimate_reward}踏上归途",
            "{enemy}的残余势力追击",
            "最终的{final_challenge}等待着他",
            "将所学融会贯通",
        ],
        "twist": "{final_challenge}的对手竟是{old_face}",
    },
    {
        "phase": "满载而归",
        "title_pattern": "英雄归来",
        "events": [
            "主角回到{starting_point}，物是人非",
            "用{ultimate_reward}拯救{homeland}",
            "完成{character_growth}的蜕变",
            "成为{legend}，但新的冒险已在酝酿",
        ],
        "twist": "{legend}的代价是{final_price}",
    },
]

# 题材填充词
_GENRE_WORDS: dict[str, dict[str, str]] = {
    "玄幻": {
        "starting_point": "边陲小镇",
        "status": "默默无闻",
        "inciting_event": "宗门大比",
        "cheat": "上古传承",
        "first_rival": "宗门天才",
        "secret": "自己的身世之谜",
        "new_location": "大宗门",
        "ally": "神秘少女",
        "rival": "天骄弟子",
        "milestone": "筑基期",
        "resource": "灵脉矿洞",
        "domain": "秘境",
        "world_secret": "上古神魔之战的真相",
        "strong_enemy": "魔道巨擘",
        "new_ability": "吞噬之力",
        "region": "东荒",
        "competition": "百宗大会",
        "conspiracy": "魔道渗透",
        "group": "无辜弟子",
        "milestone2": "金丹期",
        "title": "东荒第一人",
        "love_interest": "圣女",
        "enemy": "天魔教主",
        "location": "宗门",
        "safe_place": "禁地深处",
        "ultimate_ability": "混沌神体",
        "alliance": "正道联盟",
        "enemy_base": "天魔殿",
        "connection": "同源",
        "world": "九州",
        "new_order": "新的修真秩序",
        "new_threat": "天外魔族",
        "keyword": "逆天",
        "personality": "坚韧不拔",
        "desire": "变强守护家人",
        "foreshadow": "玉佩异动",
        "mentor": "邋遢老者",
        "new_world": "修真界",
        "first_test": "妖兽森林",
        "trials": "九死一生",
        "world_truth": "天道有缺",
        "danger_zone": "神魔战场",
        "inner_struggle": "心魔",
        "death_and_rebirth": "涅槃",
        "ultimate_reward": "神格",
        "price": "斩断七情",
        "final_challenge": "天道考验",
        "old_face": "已故的师兄",
        "homeland": "小镇",
        "character_growth": "从凡人到神帝",
        "legend": "传说",
        "final_price": "永生孤独",
        "hidden_agenda": "某个大势力的阴谋",
        "ultimate_goal": "颠覆天道",
    },
    "都市": {
        "starting_point": "城中村",
        "status": "底层打拼",
        "inciting_event": "被公司辞退",
        "cheat": "神秘医术传承",
        "first_rival": "公司主管",
        "secret": "亲生父母的下落",
        "new_location": "市中心医院",
        "ally": "富家千金",
        "rival": "医界天才",
        "milestone": "主治医师",
        "resource": "古方药典",
        "domain": "上流社会",
        "world_secret": "古老医道传承的秘密",
        "strong_enemy": "医药集团巨头",
        "new_ability": "望气术",
        "region": "江南市",
        "competition": "全国医学大赛",
        "conspiracy": "假药黑幕",
        "group": "患者",
        "milestone2": "名医",
        "title": "神医圣手",
        "love_interest": "总裁",
        "enemy": "地下势力头目",
        "location": "医院",
        "safe_place": "老宅",
        "ultimate_ability": "生死人肉白骨",
        "alliance": "商界联盟",
        "enemy_base": "集团总部",
        "connection": "世交",
        "world": "都市",
        "new_order": "新的医疗格局",
        "new_threat": "国际医药巨头",
        "keyword": "神医",
        "personality": "外冷内热",
        "desire": "证明自己",
        "foreshadow": "旧玉佩发烫",
        "mentor": "退休老中医",
        "new_world": "上流社会",
        "first_test": "急救病人",
        "trials": "接连不断的医闹",
        "world_truth": "古医道的断层",
        "danger_zone": "地下黑市",
        "inner_struggle": "医者仁心与现实的冲突",
        "death_and_rebirth": "假死脱身",
        "ultimate_reward": "医道真经",
        "price": "暴露身份",
        "final_challenge": "全球瘟疫",
        "old_face": "曾经的恩师",
        "homeland": "城中村",
        "character_growth": "从草根到国医",
        "legend": "都市传说",
        "final_price": "永无宁日",
        "hidden_agenda": "财团的布局",
        "ultimate_goal": "垄断医药市场",
    },
}


def _get_word(genre: str, key: str) -> str:
    words = _GENRE_WORDS.get(genre)
    if words is None:
        for g, value in _GENRE_WORDS.items():
            if g in genre:
                words = value
                break
    if words is None:
        words = _GENRE_WORDS["玄幻"]
    return words.get(key, key)


def generate_outline(request: OutlineGenerateRequest) -> OutlineResult:
    """
    生成卷级大纲。

    策略：
    1. 根据结构类型选择阶段模板
    2. 根据卷数分配阶段（三幕式按1:3:1比例，英雄之旅均匀分布）
    3. 用题材词库填充占位符
    4. 结合用户主角和核心冲突定制
    """
    phases = _THREE_ACT_PHASES if request.structure_type == "three_act" else _HERO_JOURNEY_PHASES

    # 根据卷数选择阶段
    n = request.volume_count
    if n <= len(phases):
        # 均匀采样
        indices = [round(i * (len(phases) - 1) / (n - 1)) for i in range(n)] if n > 1 else [0]
        selected_phases = [phases[i] for i in indices]
    else:
        # 卷数超过阶段数，重复中间阶段并递增
        selected_phases = list(phases)
        extra = n - len(phases)
        mid = len(phases) // 2
        for i in range(extra):
            selected_phases.insert(mid + i, phases[mid])

    volumes: list[VolumeOutline] = []
    for idx, phase in enumerate(selected_phases, 1):
        # 填充标题
        title = phase["title_pattern"].format(
            keyword=_get_word(request.genre, "keyword"),
            location=_get_word(request.genre, "location"),
            region=_get_word(request.genre, "region"),
            new_world=_get_word(request.genre, "new_world"),
        )

        # 填充核心事件
        events = []
        for event_tpl in phase["events"]:
            event = event_tpl
            for key in [
                "starting_point",
                "status",
                "inciting_event",
                "cheat",
                "first_rival",
                "secret",
                "new_location",
                "ally",
                "rival",
                "milestone",
                "resource",
                "domain",
                "world_secret",
                "strong_enemy",
                "new_ability",
                "region",
                "competition",
                "conspiracy",
                "group",
                "milestone2",
                "title",
                "love_interest",
                "enemy",
                "location",
                "safe_place",
                "ultimate_ability",
                "alliance",
                "enemy_base",
                "connection",
                "world",
                "new_order",
                "new_threat",
                "keyword",
                "personality",
                "desire",
                "foreshadow",
                "mentor",
                "new_world",
                "first_test",
                "trials",
                "world_truth",
                "danger_zone",
                "inner_struggle",
                "death_and_rebirth",
                "ultimate_reward",
                "price",
                "final_challenge",
                "old_face",
                "homeland",
                "character_growth",
                "legend",
                "final_price",
                "hidden_agenda",
                "ultimate_goal",
            ]:
                event = event.replace("{" + key + "}", _get_word(request.genre, key))
            # 注入用户主角和冲突
            event = event.replace("主角", request.protagonist or "主角")
            events.append(event)

        # 填充转折
        twist = phase["twist"]
        for key in [
            "secret",
            "ally",
            "strong_enemy",
            "competition",
            "enemy",
            "mentor",
            "ultimate_reward",
            "price",
            "final_challenge",
            "old_face",
            "legend",
            "final_price",
            "ultimate_goal",
            "connection",
            "new_threat",
            "hidden_agenda",
        ]:
            twist = twist.replace("{" + key + "}", _get_word(request.genre, key))
        twist = twist.replace("主角", request.protagonist or "主角")

        # 注入核心冲突到第一卷
        if idx == 1 and request.core_conflict:
            events.append(f"核心矛盾浮现：{request.core_conflict}")

        volumes.append(
            VolumeOutline(
                volume_number=idx,
                title=f"第{idx}卷 {title}",
                core_events=events,
                ending_twist=twist,
            )
        )

    return OutlineResult(structure_type=request.structure_type, volumes=volumes)
