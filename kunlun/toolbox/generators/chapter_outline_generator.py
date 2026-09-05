"""
细纲生成器 — 纯模板+规则，离线可用

根据卷大纲生成章节级细纲，每章包含：标题、场景、冲突、钩子。
"""

from __future__ import annotations

import hashlib

from kunlun.toolbox.models import (
    ChapterOutlineGenerateRequest,
    ChapterOutlineItem,
    ChapterOutlineResult,
)

# ── 章节节奏模式 ─────────────────────────────────────────

# 每5章一个小循环：铺垫→发展→冲突→高潮→转折
_RHYTHM_PATTERNS: list[dict[str, str]] = [
    {
        "rhythm": "铺垫",
        "title_tpl": "{prefix}{suffix}",
        "scene_tpl": "{location}中，{protagonist}{action}，气氛{atmosphere}。",
        "conflict_tpl": "{minor_conflict}，看似平静实则暗流涌动。",
        "hook_tpl": "就在这时，{unexpected}发生了。",
    },
    {
        "rhythm": "发展",
        "title_tpl": "{prefix}之{suffix}",
        "scene_tpl": "{protagonist}来到{new_location}，{discovery}。",
        "conflict_tpl": "{rival}出现，双方{interaction}。",
        "hook_tpl": "更令人震惊的是，{reveal}。",
    },
    {
        "rhythm": "冲突",
        "title_tpl": "激战{suffix}",
        "scene_tpl": "{battle_location}，{protagonist}与{enemy}正面交锋。",
        "conflict_tpl": "{enemy}使出{killer_move}，{protagonist}{reaction}。",
        "hook_tpl": "千钧一发之际，{turning_point}。",
    },
    {
        "rhythm": "高潮",
        "title_tpl": "{prefix}爆发",
        "scene_tpl": "{climax_location}，{protagonist}{breakthrough}。",
        "conflict_tpl": "面对{overwhelming_odds}，{protagonist}{ultimate_action}。",
        "hook_tpl": "然而，{aftermath}。",
    },
    {
        "rhythm": "转折",
        "title_tpl": "{suffix}之后",
        "scene_tpl": "{aftermath_location}，{protagonist}{reflection}。",
        "conflict_tpl": "{new_threat}悄然逼近，{protagonist}{preparation}。",
        "hook_tpl": "远处，{foreshadow}。",
    },
]

# 题材词库
_GENRE_SCENE_WORDS: dict[str, dict[str, list[str]]] = {
    "玄幻": {
        "prefix": ["剑意", "刀芒", "雷霆", "烈焰", "寒冰", "星辰", "月影", "龙魂", "凤鸣", "混沌"],
        "suffix": ["惊变", "觉醒", "争锋", "破局", "逆袭", "封神", "渡劫", "证道", "镇杀", "崛起"],
        "location": ["宗门大殿", "藏经阁", "演武场", "灵药园", "后山禁地", "试炼塔"],
        "new_location": ["秘境入口", "上古遗迹", "妖兽森林", "魔道领地", "拍卖会"],
        "battle_location": ["演武场中央", "秘境深处", "宗门山门前", "万丈悬崖之上", "雷海之中"],
        "climax_location": ["九天之上", "神魔战场", "天道之下", "世界之巅", "混沌之中"],
        "aftermath_location": ["静室之中", "山巅之上", "洞府之内", "星空之下", "废墟之中"],
        "action": ["打坐修炼", "参悟功法", "炼制丹药", "锤炼法器", "推演阵法"],
        "atmosphere": ["肃穆", "紧张", "诡异", "压抑", "祥和"],
        "discovery": ["发现了一处隐秘的洞府", "感应到一股古老的气息", "找到了失传的功法残页"],
        "rival": ["宗门天骄", "魔道弟子", "散修强者", "上古凶兽", "异族王子"],
        "interaction": ["唇枪舌剑", "暗中较量", "剑拔弩张", "互相试探"],
        "enemy": ["魔道巨擘", "宗门叛徒", "上古凶兽", "天道化身", "域外天魔"],
        "killer_move": ["灭世一击", "禁术大招", "本命法宝", "血脉之力", "天道法则"],
        "reaction": ["瞳孔骤缩", "全力抵挡", "巧妙闪避", "以攻对攻"],
        "breakthrough": ["突破境界", "觉醒神体", "领悟大道", "融合法则"],
        "overwhelming_odds": ["十倍于己的敌人", "天道威压", "灭世之力", "远古禁制"],
        "ultimate_action": ["燃烧精血", "催动禁术", "召唤神兵", "融合道果"],
        "reflection": ["总结此战得失", "消化战斗感悟", "稳固新突破的境界"],
        "new_threat": ["更强大的敌人", "天道的注视", "远古封印的松动"],
        "preparation": ["加紧修炼", "联络盟友", "布置后手"],
        "unexpected": ["一道金光从天而降", "禁地传来异响", "玉佩突然发烫", "系统提示音响起"],
        "reveal": ["对方竟是上古种族后裔", "此地隐藏着惊天秘密", "自己的身世另有隐情"],
        "turning_point": ["{protagonist}体内的力量突然觉醒"],
        "aftermath": ["更大的危机正在酝酿"],
        "foreshadow": ["一道黑影悄然掠过"],
        "minor_conflict": ["同门挑衅", "资源争夺", "功法瓶颈", "心魔侵扰"],
    },
    "都市": {
        "prefix": ["都市", "职场", "商战", "医道", "异能", "暗涌", "风云", "霓虹", "钢铁"],
        "suffix": ["风云", "暗涌", "逆袭", "崛起", "争锋", "破局", "翻盘", "封神", "归来", "觉醒"],
        "location": ["写字楼", "医院病房", "高级会所", "咖啡厅", "地下车库", "总裁办公室"],
        "new_location": ["商业中心", "私人医院", "顶级会所", "拍卖会场", "地下拳场"],
        "battle_location": ["地下停车场", "废弃工厂", "高楼天台", "私人别墅", "码头仓库"],
        "climax_location": ["新闻发布会现场", "股东大会", "城市之巅", "手术台旁", "法庭之上"],
        "aftermath_location": ["办公室", "家中客厅", "医院走廊", "天台上", "车内"],
        "action": ["整理资料", "研究病例", "分析市场", "锻炼身体", "回忆过往"],
        "atmosphere": ["压抑", "紧张", "暧昧", "肃杀", "温馨"],
        "discovery": ["发现了一份关键文件", "察觉到被人跟踪", "找到了失踪的线索"],
        "rival": ["商业对手", "职场小人", "医界同僚", "富家子弟", "黑道人物"],
        "interaction": ["针锋相对", "暗中较劲", "虚与委蛇", "正面硬刚"],
        "enemy": ["商业巨头", "幕后黑手", "国际杀手", "腐败官员", "犯罪集团"],
        "killer_move": ["商业围剿", "舆论攻击", "暗杀行动", "法律陷阱"],
        "reaction": ["冷静应对", "将计就计", "果断反击", "暂避锋芒"],
        "breakthrough": ["掌握关键证据", "医术突破", "异能进化", "商业布局完成"],
        "overwhelming_odds": ["整个集团的打压", "舆论的围攻", "多方势力的围剿"],
        "ultimate_action": ["亮出底牌", "绝地反击", "釜底抽薪", "背水一战"],
        "reflection": ["复盘整个事件", "思考下一步计划", "调整心态"],
        "new_threat": ["更强大的对手", "国际势力的介入", "旧敌的报复"],
        "preparation": ["收集情报", "整合资源", "布局反击"],
        "unexpected": ["一个陌生电话打来", "有人推门而入", "手机收到一条匿名短信"],
        "reveal": ["对方的后台竟然是…", "这件事牵扯出更大的黑幕", "自己一直被人监视"],
        "turning_point": ["{protagonist}拿出了关键证据"],
        "aftermath": ["事情远没有结束"],
        "foreshadow": ["一辆黑色轿车悄然停在街角"],
        "minor_conflict": ["同事排挤", "客户刁难", "资金短缺", "技术难题"],
    },
}


def _get_words(genre: str) -> dict[str, list[str]]:
    words = _GENRE_SCENE_WORDS.get(genre)
    if words is None:
        for g, value in _GENRE_SCENE_WORDS.items():
            if g in genre:
                words = value
                break
    if words is None:
        words = _GENRE_SCENE_WORDS["玄幻"]
    return words


def _deterministic_pick(words: list[str], seed: str, index: int) -> str:
    """基于种子的确定性选择，确保相同输入产生相同输出。"""
    h = hashlib.md5(f"{seed}:{index}".encode()).hexdigest()
    idx = int(h[:8], 16) % len(words)
    return words[idx]


def generate_chapter_outline(request: ChapterOutlineGenerateRequest) -> ChapterOutlineResult:
    """
    生成章节级细纲。

    策略：
    1. 每5章一个节奏循环（铺垫→发展→冲突→高潮→转折）
    2. 基于卷大纲关键词 + 题材词库生成每章内容
    3. 章末钩子承上启下
    """
    words = _get_words(request.genre)
    seed = request.volume_outline[:50] + request.volume_title
    protagonist = "主角"

    chapters: list[ChapterOutlineItem] = []
    for i in range(1, request.chapter_count + 1):
        rhythm = _RHYTHM_PATTERNS[(i - 1) % 5]

        # 标题
        prefix = _deterministic_pick(words["prefix"], seed, i * 3)
        suffix = _deterministic_pick(words["suffix"], seed, i * 3 + 1)
        title = rhythm["title_tpl"].format(prefix=prefix, suffix=suffix)

        # 场景
        location = _deterministic_pick(words["location"], seed, i * 5)
        new_location = _deterministic_pick(words["new_location"], seed, i * 5 + 1)
        battle_location = _deterministic_pick(words["battle_location"], seed, i * 5 + 2)
        climax_location = _deterministic_pick(words["climax_location"], seed, i * 5 + 3)
        aftermath_location = _deterministic_pick(words["aftermath_location"], seed, i * 5 + 4)
        action = _deterministic_pick(words["action"], seed, i * 7)
        atmosphere = _deterministic_pick(words["atmosphere"], seed, i * 7 + 1)
        discovery = _deterministic_pick(words["discovery"], seed, i * 7 + 2)

        # 冲突相关词（提前选取，场景模板可能用到）
        rival = _deterministic_pick(words["rival"], seed, i * 11)
        enemy = _deterministic_pick(words["enemy"], seed, i * 11 + 1)
        interaction = _deterministic_pick(words["interaction"], seed, i * 11 + 2)
        killer_move = _deterministic_pick(words["killer_move"], seed, i * 11 + 3)
        reaction = _deterministic_pick(words["reaction"], seed, i * 11 + 4)
        breakthrough = _deterministic_pick(words["breakthrough"], seed, i * 11 + 5)
        overwhelming_odds = _deterministic_pick(words["overwhelming_odds"], seed, i * 11 + 6)
        ultimate_action = _deterministic_pick(words["ultimate_action"], seed, i * 11 + 7)
        minor_conflict = _deterministic_pick(words["minor_conflict"], seed, i * 11 + 8)
        new_threat = _deterministic_pick(words["new_threat"], seed, i * 11 + 9)
        preparation = _deterministic_pick(words["preparation"], seed, i * 11 + 10)
        reflection = _deterministic_pick(words["reflection"], seed, i * 11 + 11)

        # 钩子相关词
        unexpected = _deterministic_pick(words["unexpected"], seed, i * 13)
        reveal = _deterministic_pick(words["reveal"], seed, i * 13 + 1)
        turning_point = _deterministic_pick(words["turning_point"], seed, i * 13 + 2).format(
            protagonist=protagonist
        )
        aftermath = _deterministic_pick(words["aftermath"], seed, i * 13 + 3)
        foreshadow = _deterministic_pick(words["foreshadow"], seed, i * 13 + 4)

        scene = rhythm["scene_tpl"].format(
            location=location,
            new_location=new_location,
            battle_location=battle_location,
            climax_location=climax_location,
            aftermath_location=aftermath_location,
            protagonist=protagonist,
            action=action,
            atmosphere=atmosphere,
            discovery=discovery,
            enemy=enemy,
            breakthrough=breakthrough,
            reflection=reflection,
        )

        conflict = rhythm["conflict_tpl"].format(
            protagonist=protagonist,
            rival=rival,
            enemy=enemy,
            interaction=interaction,
            killer_move=killer_move,
            reaction=reaction,
            breakthrough=breakthrough,
            overwhelming_odds=overwhelming_odds,
            ultimate_action=ultimate_action,
            minor_conflict=minor_conflict,
            new_threat=new_threat,
            preparation=preparation,
        )

        hook = rhythm["hook_tpl"].format(
            unexpected=unexpected,
            reveal=reveal,
            turning_point=turning_point,
            aftermath=aftermath,
            foreshadow=foreshadow,
        )

        chapters.append(
            ChapterOutlineItem(
                chapter_number=i,
                title=f"第{i}章 {title}",
                scene=scene,
                conflict=conflict,
                hook=hook,
            )
        )

    return ChapterOutlineResult(
        volume_title=request.volume_title or "未命名卷",
        chapters=chapters,
    )
