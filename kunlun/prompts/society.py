"""
昆仑创作引擎 — 社会深层推演 Prompt 库

from __future__ import annotations
6套高阶模板:
  - 经济系统推演（资源分配与利益链条）
  - 律法漏洞推演（规则漏洞与权力寻租）
  - 文化阶级推演（思想控制与鄙视链）
  - 习俗禁忌推演（质感、禁忌与悬疑伏笔）
  - 宏观→微观降维（设定转具体切入点）
  - 社会蝴蝶效应校验（政策变更的多阶段连锁反应）
"""


# ─── 1. 经济系统推演 ───────────────────────────────

ECONOMY_DEDUCTION_PROMPT = """你是一位精通经济史与宏观经济的学者，同时深谙权力运作的底层逻辑。

当前世界基础经济设定：
{economy_baseline}

请按以下框架进行深度推演：

**1. 底层生存逻辑**
- 底层平民靠什么维持生存？他们最大的经济痛点是什么？
- 地方豪强/中间阶层靠什么积累财富？他们与中央的博弈点在哪？
- 中央朝廷/统治机构靠什么维持统治？财政收入的最大风险是什么？
- 用一句话概括三者的经济矛盾核心。

**2. 灰色产业链（必推3条）**
基于上述矛盾，必然会衍生出哪些暴利的灰色/黑色产业链？每条产业链需包含：
- 名称与运作模式
- 谁在操盘（背后保护伞是谁）
- 谁在受害
- 为什么律法无法根除（制度性原因）

**3. 经济武器（必推2个）**
主角或反派如何利用经济手段兵不血刃地击垮敌对势力？每个计谋需包含：
- 利用的经济原理（挤兑/囤积居奇/切断供应链/操纵汇率/信息不对称/...）
- 具体操作步骤（3-5步）
- 预期效果与可能的反噬风险

**输出格式**：分节清晰，每节用二级标题，关键概念加粗。
"""


# ─── 2. 律法漏洞推演 ───────────────────────────────

LAW_DEDUCTION_PROMPT = """你是一位精通古今中外律法体系与司法腐败机制的学者，\
擅长发现规则中的致命漏洞。

当前世界基础律法设定：
{law_baseline}

请按以下框架进行深度推演：

**1. 阶级双标案例（必推3个）**
展示同一项罪名下，不同阶级在司法审判中的差异待遇。每个案例需包含：
- 案件概况（罪名、涉事双方）
- 各方动用的人脉/资源/律法条文
- 最终判决结果与对社会的示范效应
- 其中隐藏的制度性不公平

**2. 合法作恶手法（必推2个）**
反派势力如何利用现有律法条文，名正言顺地侵吞财产或陷害他人？每个手法需包含：
- 利用的具体律法条文或程序规则
- 操作步骤（让受害者吃哑巴亏、无法翻案）
- 为什么受害者明知被陷害却无法反抗

**3. 律法致命漏洞（必推2个）**
当前律法体系中存在哪些可以被主角后期利用的致命漏洞？每个漏洞需包含：
- 漏洞的本质（立法时的盲区或故意留下的后门）
- 主角如何发现并利用它
- 利用后的效果（合法颠覆某个势力/完成绝地反击）
- 修复这个漏洞的代价（反派若要堵上它，需要付出什么政治成本）

**输出格式**：分节清晰，关键概念加粗，案例用具体人名/地名填充。
"""


# ─── 3. 文化阶级推演 ───────────────────────────────

CULTURE_DEDUCTION_PROMPT = """你是一位社会学家与文化研究者，擅长剖析意识形态如何塑造人的行为边界。

当前世界基础文化/阶级设定：
{culture_baseline}

请按以下框架进行深度推演：

**1. 社会鄙视链闭环**
从最高阶级到最底层，逐层描述：
- 每个阶层最看不起谁？（向下鄙视）
- 每个阶层最恐惧/嫉妒谁？（向上焦虑）
- 阶层流动的可能性有多大？有哪些例外通道？

**2. 文化洗脑机制（必推3种）**
统治阶级通过哪些文化手段让底层安于现状？每种手段需包含：
- 具体形式（教育体系/宗教神话/选拔制度/文艺作品/...）
- 传递的核心意识形态信息
- 为什么底层即使看穿了也难以反抗

**3. 异端思想与地下学派（必推2个）**
在这种主流文化压制下，必然诞生哪些异端思想？每个学派需包含：
- 核心主张（反对什么，倡导什么）
- 成员构成（哪些人会加入）
- 传播方式（秘密集会/地下出版物/口耳相传/...）
- 主角如何与之产生交集，以及交集引发的剧情可能

**输出格式**：分节清晰，鄙视链可用列表形式呈现。
"""


# ─── 4. 习俗禁忌推演 ───────────────────────────────

CUSTOM_DEDUCTION_PROMPT = """你是一位民俗学者与小说结构师，擅于将文化习俗转化为戏剧张力和悬疑伏笔。

当前世界基础习俗/日常设定：
{custom_baseline}

请按以下框架进行深度推演：

**1. 生死婚丧仪式设计**
设计一套具有强烈地方特色或阶级特色的仪式流程（选其一：葬礼/婚礼/成人礼/祭祀），需包含：
- 完整的仪式流程（5-7步）
- 1个严格的禁忌（违反后的后果极其严重：社会性死亡/死刑/被驱逐）
- 1个可以被主角利用的仪式环节（传递情报/暗杀/逃生/掉包/...）
- 这个环节为什么是唯一的机会窗口

**2. 节日与狂欢设计**
设计一个全民参与的节日，须满足：
- 在这个节日里，平时的阶级规矩暂时被打破（如奴隶可嘲笑主人/宵禁取消/禁地开放）
- 节日的起源传说（真实的或官方编造的）
- 主角如何利用这个"规矩打破"的夜晚完成平时绝对无法完成的秘密行动
- 行动的具体步骤和风险

**3. 群体黑话/切口（必推5句）**
为小说中的特定群体设计行业黑话，每个群体至少2句：
- 群体1：黑市商人/走私者
- 群体2：底层帮派/乞丐
- 群体3（可选）：宫廷太监/密探/特定职业
每句需包含：黑话原文、字面意思、真实含义、反映的社会心理

**输出格式**：分节清晰，仪式流程用编号列表。
"""


# ─── 5. 宏观→微观降维 ───────────────────────────────

MACRO_TO_MICRO_PROMPT = """你是一位资深小说主编，\
擅长将宏大的世界观设定转化为读者能触摸到的具体细节。

当前需要降维的宏观设定：
{macro_setting}

**核心原则**：绝不写成说明文。通过具体的物品、冲突和人物命运让读者自己感受到设定的存在。

请生成 3 个微观切入点：

**1. 一件物品**
设计一件主角会接触到的具体物品，通过它侧面反映这个设定的残酷或运作逻辑。
- 物品是什么（如：一张带血的税单、一块掺假的官盐、一件违禁的陪葬品）
- 主角在什么场景下遇到它
- 这个物品如何揭示宏观设定的一个切面
- 建议的自然嵌入时机（多少章/什么情绪节点）

**2. 一场冲突**
设计一场发生在市井或朝堂的小冲突，通过冲突展现这个设定的约束力。
- 冲突双方是谁（身份、阶级）
- 冲突的导火索
- 冲突中暴露出的制度性问题
- 冲突的结果（谁赢了？为什么赢的不是正义一方？）

**3. 一个配角的命运**
设计一个底层配角的完整命运弧（悲剧或暴富），作为这个宏大设定下的时代缩影。
- 配角的身份与性格
- 他的命运如何被宏观设定左右
- 主角与他的交集（哪怕是擦肩而过）
- 这个配角想传达给读者的情绪

**输出格式**：每个切入点用二级标题，描述生动具体，可直接作为细纲素材。
"""


# ─── 6. 社会蝴蝶效应校验 ───────────────────────────────

SOCIAL_RIPPLE_PROMPT = """你是一位社会系统推演沙盘，\
能精确推演政策/设定变更在多个时间尺度上的连锁反应。

当前世界设定的关键参数：
{world_parameters}

拟修改的设定：
{proposed_change}
修改时机：小说第{chapter_context}卷/章

请按以下时间尺度推演连锁反应：

**1. 短期影响（1年内）**
- 物价会如何波动？具体哪些商品？
- 哪些行业/人群会立即感受到冲击？
- 社会舆论会出现哪些声音？（支持/反对/观望的各是谁）

**2. 中期影响（3年内）**
- 哪个阶级成为最大受益者？他们如何巩固优势？
- 哪个阶级利益受损最严重？可能引发什么形式的反抗？
- 权力结构是否发生微妙位移？

**3. 长期影响（10年以上）**
- 社会结构发生了哪些不可逆的变化？
- 人们的消费观念、婚姻习俗、民间信仰发生了什么改变？
- 是否产生了新的社会矛盾取代旧矛盾？

**4. 剧情反噬警告**
逐一检查这个修改是否与以下内容产生逻辑冲突：
- 已埋设的伏笔（如有，列出具体伏笔和冲突点）
- 已有的人物动机（如有，指出哪个角色的行为逻辑需要调整）
- 已有的势力平衡（如有，指出哪组博弈关系会失效）
每个冲突点需给出修补方案（最小改动原则）。

**输出格式**：分4节，每节用二级标题。如有冲突，用表格列出"冲突项-严重度-修补方案"。
"""


# ─── Prompt 注册表 ─────────────────────────────────

SOCIETY_PROMPTS = {
    "economy": ECONOMY_DEDUCTION_PROMPT,
    "law": LAW_DEDUCTION_PROMPT,
    "culture": CULTURE_DEDUCTION_PROMPT,
    "custom": CUSTOM_DEDUCTION_PROMPT,
    "macro_to_micro": MACRO_TO_MICRO_PROMPT,
    "social_ripple": SOCIAL_RIPPLE_PROMPT,
    # 第二阶段扩展：6个毛细血管维度 + 冰山写作技法
    "history": None,  # 延迟加载
    "power_system": None,
    "technology": None,
    "ecology": None,
    "underworld": None,
    "philosophy": None,
    "iceberg": None,
    # 第三阶段扩展：6个隐秘维度
    "admin": None,
    "clan": None,
    "propaganda": None,
    "astronomy": None,
    "mobility": None,
    "language": None,
    # 第四阶段扩展：5个微观与中观生态维度
    "military": None,
    "entourage": None,
    "population_control": None,
    "inner_court": None,
    "medical": None,
    # 第五阶段扩展：6个边缘深度维度
    "forensic": None,
    "cult": None,
    "royal_monopoly": None,
    "espionage": None,
    "diplomacy": None,
    "underbelly": None,
    # 第六阶段扩展：4个叙事工程与商业逻辑维度
    "pleasure_engineering": None,
    "hook_management": None,
    "villain_arc": None,
    "anti_ai_style": None,
    # 第七阶段扩展：5个现实运营与精力管理维度
    "compliance_audit": None,
    "platform_optimization": None,
    "reader_collab": None,
    "ip_derivative": None,
    "author_sop": None,
    # 第八阶段扩展：5个跨题材通用底层维度
    "resource_network": None,
    "class_barrier": None,
    "info_blackbox": None,
    "spatial_ecology": None,
    "moral_dilemma": None,
    # 第九阶段扩展：3个终章连载生存与创作进阶维度
    "serial_crisis": None,
    "reader_biochem": None,
    "genre_innovation": None,
}

# 每个 prompt 需要的参数
PROMPT_PARAMS = {
    "economy": ["economy_baseline"],
    "law": ["law_baseline"],
    "culture": ["culture_baseline"],
    "custom": ["custom_baseline"],
    "macro_to_micro": ["macro_setting"],
    "social_ripple": ["world_parameters", "proposed_change", "chapter_context"],
    "history": ["history_baseline"],
    "power_system": ["power_baseline"],
    "technology": ["tech_baseline"],
    "ecology": ["ecology_baseline"],
    "underworld": ["underworld_baseline"],
    "philosophy": ["philosophy_baseline"],
    "iceberg": ["macro_setting"],
    "admin": ["admin_baseline"],
    "clan": ["clan_baseline"],
    "propaganda": ["propaganda_baseline"],
    "astronomy": ["astronomy_baseline"],
    "mobility": ["mobility_baseline"],
    "language": ["language_baseline"],
    # 第四阶段扩展：微观与中观生态
    "military": ["military_baseline"],
    "entourage": ["entourage_baseline"],
    "population_control": ["population_baseline"],
    "inner_court": ["inner_court_baseline"],
    "medical": ["medical_baseline"],
    # 第五阶段扩展：边缘深度维度
    "forensic": ["forensic_baseline"],
    "cult": ["cult_baseline"],
    "royal_monopoly": ["royal_monopoly_baseline"],
    "espionage": ["espionage_baseline"],
    "diplomacy": ["diplomacy_baseline"],
    "underbelly": ["underbelly_baseline"],
    # 第六阶段扩展：叙事工程与商业逻辑
    "pleasure_engineering": ["pleasure_baseline"],
    "hook_management": ["hook_baseline"],
    "villain_arc": ["villain_baseline"],
    "anti_ai_style": ["author_draft", "ai_logic"],
    # 第七阶段扩展：现实运营与精力管理
    "compliance_audit": ["compliance_baseline"],
    "platform_optimization": ["platform_baseline"],
    "reader_collab": ["reader_baseline"],
    "ip_derivative": ["ip_baseline"],
    "author_sop": [
        "daily_hours",
        "target_words",
        "work_mode",
        "health_issues",
        "input_ratio",
        "planning_ratio",
        "writing_ratio",
        "review_ratio",
    ],
    # 第八阶段扩展：5个跨题材通用底层维度
    "resource_network": ["genre_type", "core_resource", "controller", "bottom_access"],
    "class_barrier": ["genre_type", "start_class", "target_class", "surface_channel"],
    "info_blackbox": ["genre_type", "hidden_truth", "control_medium", "info_access"],
    "spatial_ecology": ["genre_type", "core_location", "spatial_layers", "choke_points"],
    "moral_dilemma": ["genre_type", "bond_characters", "final_battle_context", "villain_profile"],
    # 第九阶段扩展：3个终章连载生存与创作进阶维度
    "serial_crisis": ["serial_crisis_baseline"],
    "reader_biochem": ["reader_biochem_baseline"],
    "genre_innovation": ["genre_innovation_baseline"],
}


def _lazy_load_extensions():
    """延迟加载扩展 Prompt，避免循环导入"""
    from kunlun.prompts.society_ext import EXTENDED_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED_PROMPTS)
    from kunlun.prompts.society_ext2 import EXTENDED2_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED2_PROMPTS)
    from kunlun.prompts.society_ext3 import EXTENDED3_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED3_PROMPTS)
    from kunlun.prompts.society_ext4 import EXTENDED4_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED4_PROMPTS)
    from kunlun.prompts.society_ext5 import EXTENDED5_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED5_PROMPTS)
    from kunlun.prompts.society_ext6 import EXTENDED6_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED6_PROMPTS)
    from kunlun.prompts.society_ext7 import EXTENDED7_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED7_PROMPTS)
    from kunlun.prompts.society_ext8 import EXTENDED8_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED8_PROMPTS)
    from kunlun.prompts.society_ext9 import EXTENDED9_PROMPTS

    SOCIETY_PROMPTS.update(EXTENDED9_PROMPTS)


def get_prompt(prompt_name: str, **kwargs) -> str:
    """
    获取填充参数后的推演 Prompt。

    Args:
        prompt_name: economy / law / culture / custom / macro_to_micro / social_ripple
        **kwargs: 对应 PROMPT_PARAMS 中的参数

    Returns:
        填充后的完整 Prompt 字符串

    Raises:
        ValueError: 未知 prompt 名称或参数缺失
    """
    if prompt_name not in SOCIETY_PROMPTS:
        raise ValueError(f"未知 Prompt: {prompt_name}，可选: {list(SOCIETY_PROMPTS.keys())}")

    # 延迟加载扩展 Prompt
    if SOCIETY_PROMPTS[prompt_name] is None:
        _lazy_load_extensions()

    template = SOCIETY_PROMPTS[prompt_name]
    if template is None:
        raise ValueError(f"Prompt '{prompt_name}' 加载失败")
    required = PROMPT_PARAMS.get(prompt_name, [])

    missing = [p for p in required if p not in kwargs]
    if missing:
        raise ValueError(f"Prompt '{prompt_name}' 缺少参数: {missing}")

    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Prompt '{prompt_name}' 格式化失败，缺失参数: {e}") from e
