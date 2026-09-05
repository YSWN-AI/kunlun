"""
金手指生成器 — 纯模板+规则，离线可用

生成5个金手指方案，覆盖系统/穿越/重生/异能/血脉等类别，
每个方案包含：名称、类别、能力描述、成长路径、限制条件。
"""

from __future__ import annotations

from kunlun.toolbox.models import CheatGenerateRequest, CheatResult, CheatScheme

# ── 金手指模板库 ─────────────────────────────────────────

_CHEAT_TEMPLATES: list[dict[str, str]] = [
    # 系统类
    {
        "category": "系统",
        "name_tpl": "{prefix}{system_name}系统",
        "ability_tpl": (
            "绑定宿主后，可通过完成{task_type}任务获得{resource}。"
            "系统提供{function1}、{function2}两大核心功能，"
            "可实时{real_time_ability}。"
        ),
        "growth_tpl": (
            "初始解锁{initial_func}，随等级提升依次开放{mid_func}、{high_func}。"
            "满级后可{ultimate_func}。"
        ),
        "limitation_tpl": (
            "任务失败将扣除{pentalty}；每日有{daily_limit}次使用上限；无法直接干预{interdiction}。"
        ),
    },
    # 穿越类
    {
        "category": "穿越",
        "name_tpl": "{prefix}穿越者",
        "ability_tpl": (
            "灵魂自{origin_world}穿越至{target_world}，携带{knowledge}。"
            "凭借{advantage}，可在{domain}中如鱼得水。"
        ),
        "growth_tpl": (
            "初期依靠{early_advantage}立足，中期融合{fusion}形成独特体系，后期{ultimate_state}。"
        ),
        "limitation_tpl": (
            "记忆会随时间{memory_decay}；身体{body_limit}；过度使用{knowledge}会引发{side_effect}。"
        ),
    },
    # 重生类
    {
        "category": "重生",
        "name_tpl": "{prefix}重生者",
        "ability_tpl": (
            "带着{years}年记忆回到{timepoint}，知晓{future_events}。"
            "可提前布局{layout}，规避{avoid}。"
        ),
        "growth_tpl": (
            "重生初期利用{early_info}快速积累，中期因{butterfly_effect}出现未知变量，"
            "后期突破{breakthrough}达到前世无法企及的高度。"
        ),
        "limitation_tpl": (
            "记忆并非全知，{unknown}仍会发生；改变重大事件会引发{butterfly}；"
            "重生次数{reborn_limit}。"
        ),
    },
    # 异能类
    {
        "category": "异能",
        "name_tpl": "{prefix}{power_name}之瞳",
        "ability_tpl": (
            "觉醒{power_type}异能，可{core_ability}。"
            "异能分为{stage1}、{stage2}、{stage3}三个阶段，"
            "每阶段能力呈指数级增长。"
        ),
        "growth_tpl": (
            "初觉时仅能{basic_use}，随熟练度提升可{advanced_use}，"
            "最终觉醒{ultimate_use}，触及{power_domain}法则。"
        ),
        "limitation_tpl": ("使用过度会{cost}；对{immunity}无效；异能觉醒有{awakening_risk}风险。"),
    },
    # 血脉类
    {
        "category": "血脉",
        "name_tpl": "{prefix}{blood_name}血脉",
        "ability_tpl": (
            "体内流淌着{ancestor}的血脉，可{blood_ability1}、{blood_ability2}。"
            "血脉浓度决定{power_scale}，浓度越高越接近{ultimate_form}。"
        ),
        "growth_tpl": (
            "初始血脉浓度{initial_concentration}，通过{cultivation_method}逐步提纯，"
            "最终可{blood_awakening}，觉醒{ancestor_ability}。"
        ),
        "limitation_tpl": (
            "血脉觉醒时会{awakening_pain}；高浓度血脉会引发{blood_rage}；血脉有{heredity}限制。"
        ),
    },
    # 随身空间类
    {
        "category": "随身空间",
        "name_tpl": "{prefix}玲珑空间",
        "ability_tpl": (
            "意识海中存在一方{space_size}的独立空间，内部{space_feature}。"
            "可存储{item_type}，时间流速为外界的{time_ratio}倍。"
        ),
        "growth_tpl": (
            "初始空间{initial_size}，随修为提升空间{expansion}，最终可演化出{evolved_feature}。"
        ),
        "limitation_tpl": (
            "无法收纳{forbidden}；空间内{environment_limit}；每日进出有{access_limit}限制。"
        ),
    },
    # 签到类
    {
        "category": "签到",
        "name_tpl": "{prefix}签到系统",
        "ability_tpl": (
            "在特定{signin_location}签到可获得{reward_type}。"
            "连续签到{days}天有{bonus}，特殊地点签到有{special_reward}。"
        ),
        "growth_tpl": (
            "初期签到获得{basic_reward}，中期解锁{advanced_reward}，后期签到可{ultimate_reward}。"
        ),
        "limitation_tpl": (
            "同一地点{signin_limit}天内只能签到一次；签到奖励{randomness}；错过签到{miss_penalty}。"
        ),
    },
]

# 题材填充词
_GENRE_CHEAT_WORDS: dict[str, dict[str, list[str]]] = {
    "玄幻": {
        "prefix": ["万界", "太古", "混沌", "无上", "逆天", "神魔", "九天", "鸿蒙"],
        "system_name": ["吞噬", "签到", "选择", "复制", "炼丹", "炼器", "功法", "收徒"],
        "task_type": ["修炼", "战斗", "探索", "收徒", "炼丹", "炼器"],
        "resource": ["气运点", "功德值", "吞噬点", "灵石", "道果"],
        "function1": ["功法推演", "万物吞噬", "属性面板", "空间存储"],
        "function2": ["任务发布", "技能复制", "丹药合成", "弟子培养"],
        "real_time_ability": ["监测宿主状态", "分析敌人弱点", "推演功法路线", "预测危机"],
        "initial_func": ["基础属性面板", "简单任务系统"],
        "mid_func": ["技能融合", "时空穿梭"],
        "high_func": ["法则掌控", "世界创造"],
        "ultimate_func": ["证道成圣", "开辟大千世界"],
        "pentalty": ["修为倒退", "寿命削减", "气运流失"],
        "daily_limit": ["三", "五", "十"],
        "interdiction": ["天道法则", "他人意志", "生死轮回"],
        "origin_world": ["地球", "现代都市", "科技文明"],
        "target_world": ["修真界", "仙侠世界", "玄幻大陆"],
        "knowledge": ["现代科学知识", "网络小说剧情", "历史走向"],
        "advantage": ["超前的认知", "对剧情的了解", "跨维度的思维方式"],
        "domain": ["炼丹", "炼器", "阵法", "修炼"],
        "early_advantage": ["先知先觉", "知识碾压"],
        "fusion": ["科技与修真", "现代理念与传统修炼"],
        "ultimate_state": ["以科学证道", "创造全新修炼体系"],
        "memory_decay": ["模糊", "缺失", "失真"],
        "body_limit": ["需要重新修炼", "资质受限", "灵魂与身体磨合"],
        "side_effect": ["天道排斥", "时空紊乱", "因果缠身"],
        "years": ["五百", "一千", "三千"],
        "timepoint": ["少年时代", "宗门大比前", "家族覆灭前"],
        "future_events": ["重大机缘", "天灾人祸", "势力更迭"],
        "layout": ["人脉", "资源", "势力"],
        "avoid": ["杀身之祸", "错失机缘", "所爱之人惨死"],
        "early_info": ["彩票号码般的机缘信息", "未来大势走向"],
        "butterfly_effect": ["蝴蝶效应", "命运修正力"],
        "breakthrough": ["命运束缚", "前世极限"],
        "unknown": ["变数", "天机遮蔽之事"],
        "butterfly": ["命运反噬", "天道修正"],
        "reborn_limit": ["仅有一次", "不可逆转"],
        "power_name": ["写轮", "轮回", "破妄", "天道", "净世", "噬魂"],
        "power_type": ["精神", "空间", "时间", "因果", "元素"],
        "core_ability": ["看破虚妄", "操控空间", "预见未来", "操纵元素"],
        "stage1": ["觉醒", "初窥"],
        "stage2": ["掌控", "融合"],
        "stage3": ["化身", "法则"],
        "basic_use": ["短暂增幅", "基础感知"],
        "advanced_use": ["大范围操控", "多重能力叠加"],
        "ultimate_use": ["言出法随", "创造小世界"],
        "power_domain": ["空间", "时间", "因果"],
        "cost": ["精神力枯竭", "寿命燃烧", "经脉受损"],
        "immunity": ["同等级异能者", "特殊体质", "天道化身"],
        "awakening_risk": ["失控暴走", "精神分裂", "被异能吞噬"],
        "blood_name": ["真龙", "神凤", "麒麟", "太古神魔", "混沌"],
        "ancestor": ["远古神兽", "上古神祇", "混沌魔神"],
        "blood_ability1": ["肉身成圣", "呼风唤雨"],
        "blood_ability2": ["血脉威压", "天赋神通"],
        "power_scale": ["力量上限", "修炼速度", "神通威力"],
        "ultimate_form": ["神兽真身", "神祇降世"],
        "initial_concentration": ["稀薄", "百分之一", "微弱"],
        "cultivation_method": ["血脉觉醒仪式", "吞噬同族血脉", "神兽精血淬炼"],
        "blood_awakening": ["返祖归宗", "血脉提纯至圆满"],
        "ancestor_ability": ["先祖全部神通", "创世之力"],
        "awakening_pain": ["痛不欲生", "九死一生", "经历心魔劫"],
        "blood_rage": ["嗜血暴走", "失去理智", "被先祖意志侵蚀"],
        "heredity": ["传承衰减", "隔代遗传"],
        "space_size": ["丈许", "方圆十里", "无边无际"],
        "space_feature": ["灵气浓郁", "时间静止", "可生长灵植"],
        "item_type": ["无生命物品", "活物", "一切事物"],
        "time_ratio": ["十", "百", "千"],
        "initial_size": ["一丈见方", "小屋大小"],
        "expansion": ["不断扩大", "演化山川河流"],
        "evolved_feature": ["独立生态", "生命诞生", "小千世界"],
        "forbidden": ["活物", "有主之物", "天道法宝"],
        "environment_limit": ["无灵气", "时间静止", "无法修炼"],
        "access_limit": ["三次", "五次", "十次"],
        "signin_location": ["秘境", "禁地", "名山大川", "古迹"],
        "reward_type": ["功法", "丹药", "法宝", "体质"],
        "days": ["七", "三十", "三百六十五"],
        "bonus": ["额外奖励", "稀有物品", "特殊体质"],
        "special_reward": ["上古传承", "神兽精血", "天道碎片"],
        "basic_reward": ["低阶功法", "普通丹药"],
        "advanced_reward": ["天阶功法", "神器碎片"],
        "ultimate_reward": ["证道之基", "创世之力"],
        "signin_limit": ["一", "七", "三十"],
        "randomness": ["品质随机", "不可预测"],
        "miss_penalty": ["断签重置", "奖励降级"],
    },
}


def _pick(words: dict[str, list[str]], key: str, idx: int) -> str:
    lst = words.get(key, [key])
    return lst[idx % len(lst)]


def generate_cheats(request: CheatGenerateRequest) -> CheatResult:
    """
    生成金手指方案。

    策略：
    1. 从7类金手指模板中循环选取
    2. 用题材词库填充占位符
    3. 确保每个方案的能力、成长、限制形成完整闭环
    """
    words = _GENRE_CHEAT_WORDS.get(request.genre)
    if words is None:
        for g, value in _GENRE_CHEAT_WORDS.items():
            if g in request.genre:
                words = value
                break
    if words is None:
        words = _GENRE_CHEAT_WORDS["玄幻"]

    cheats: list[CheatScheme] = []
    for i in range(request.count):
        tpl = _CHEAT_TEMPLATES[i % len(_CHEAT_TEMPLATES)]
        idx = i

        name = tpl["name_tpl"].format(
            prefix=_pick(words, "prefix", idx),
            system_name=_pick(words, "system_name", idx + 1),
            blood_name=_pick(words, "blood_name", idx + 2),
            power_name=_pick(words, "power_name", idx + 3),
        )

        ability = tpl["ability_tpl"].format(
            task_type=_pick(words, "task_type", idx),
            resource=_pick(words, "resource", idx + 1),
            function1=_pick(words, "function1", idx + 2),
            function2=_pick(words, "function2", idx + 3),
            real_time_ability=_pick(words, "real_time_ability", idx + 4),
            origin_world=_pick(words, "origin_world", idx),
            target_world=_pick(words, "target_world", idx + 1),
            knowledge=_pick(words, "knowledge", idx + 2),
            advantage=_pick(words, "advantage", idx + 3),
            domain=_pick(words, "domain", idx + 4),
            years=_pick(words, "years", idx),
            timepoint=_pick(words, "timepoint", idx + 1),
            future_events=_pick(words, "future_events", idx + 1),
            layout=_pick(words, "layout", idx + 2),
            avoid=_pick(words, "avoid", idx + 3),
            power_type=_pick(words, "power_type", idx),
            core_ability=_pick(words, "core_ability", idx + 1),
            stage1=_pick(words, "stage1", idx + 2),
            stage2=_pick(words, "stage2", idx + 3),
            stage3=_pick(words, "stage3", idx + 4),
            ancestor=_pick(words, "ancestor", idx),
            blood_ability1=_pick(words, "blood_ability1", idx + 1),
            blood_ability2=_pick(words, "blood_ability2", idx + 2),
            power_scale=_pick(words, "power_scale", idx + 3),
            ultimate_form=_pick(words, "ultimate_form", idx + 4),
            space_size=_pick(words, "space_size", idx),
            space_feature=_pick(words, "space_feature", idx + 1),
            item_type=_pick(words, "item_type", idx + 2),
            time_ratio=_pick(words, "time_ratio", idx + 3),
            signin_location=_pick(words, "signin_location", idx),
            reward_type=_pick(words, "reward_type", idx + 1),
            days=_pick(words, "days", idx + 2),
            bonus=_pick(words, "bonus", idx + 3),
            special_reward=_pick(words, "special_reward", idx + 4),
        )

        growth = tpl["growth_tpl"].format(
            initial_func=_pick(words, "initial_func", idx),
            mid_func=_pick(words, "mid_func", idx + 1),
            high_func=_pick(words, "high_func", idx + 2),
            ultimate_func=_pick(words, "ultimate_func", idx + 3),
            early_advantage=_pick(words, "early_advantage", idx),
            fusion=_pick(words, "fusion", idx + 1),
            ultimate_state=_pick(words, "ultimate_state", idx + 2),
            early_info=_pick(words, "early_info", idx),
            butterfly_effect=_pick(words, "butterfly_effect", idx + 1),
            breakthrough=_pick(words, "breakthrough", idx + 2),
            basic_use=_pick(words, "basic_use", idx),
            advanced_use=_pick(words, "advanced_use", idx + 1),
            ultimate_use=_pick(words, "ultimate_use", idx + 2),
            domain=_pick(words, "domain", idx + 3),
            power_domain=_pick(words, "power_domain", idx + 3),
            initial_concentration=_pick(words, "initial_concentration", idx),
            cultivation_method=_pick(words, "cultivation_method", idx + 1),
            blood_awakening=_pick(words, "blood_awakening", idx + 2),
            ancestor_ability=_pick(words, "ancestor_ability", idx + 3),
            initial_size=_pick(words, "initial_size", idx),
            expansion=_pick(words, "expansion", idx + 1),
            evolved_feature=_pick(words, "evolved_feature", idx + 2),
            basic_reward=_pick(words, "basic_reward", idx),
            advanced_reward=_pick(words, "advanced_reward", idx + 1),
            ultimate_reward=_pick(words, "ultimate_reward", idx + 2),
        )

        limitation = tpl["limitation_tpl"].format(
            pentalty=_pick(words, "pentalty", idx),
            daily_limit=_pick(words, "daily_limit", idx + 1),
            interdiction=_pick(words, "interdiction", idx + 2),
            memory_decay=_pick(words, "memory_decay", idx),
            body_limit=_pick(words, "body_limit", idx + 1),
            knowledge=_pick(words, "knowledge", idx + 2),
            side_effect=_pick(words, "side_effect", idx + 2),
            unknown=_pick(words, "unknown", idx),
            butterfly=_pick(words, "butterfly", idx + 1),
            reborn_limit=_pick(words, "reborn_limit", idx + 2),
            cost=_pick(words, "cost", idx),
            immunity=_pick(words, "immunity", idx + 1),
            awakening_risk=_pick(words, "awakening_risk", idx + 2),
            awakening_pain=_pick(words, "awakening_pain", idx),
            blood_rage=_pick(words, "blood_rage", idx + 1),
            heredity=_pick(words, "heredity", idx + 2),
            forbidden=_pick(words, "forbidden", idx),
            environment_limit=_pick(words, "environment_limit", idx + 1),
            access_limit=_pick(words, "access_limit", idx + 2),
            signin_limit=_pick(words, "signin_limit", idx),
            randomness=_pick(words, "randomness", idx + 1),
            miss_penalty=_pick(words, "miss_penalty", idx + 2),
        )

        cheats.append(
            CheatScheme(
                name=name,
                category=tpl["category"],
                ability_description=ability,
                growth_path=growth,
                limitation=limitation,
            )
        )

    return CheatResult(cheats=cheats)
