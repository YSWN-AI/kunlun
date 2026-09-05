"""
写作内容包内置预设 — 男频网文场景

包含 5 个 Rule、3 个 Workflow、3 个 Skill，覆盖男频玄幻爽文的核心写作需求。
所有预设 builtin=True，用户可启用/禁用但不可删除。
"""

from kunlun.writing_packs.models import (
    PackType,
    RulePack,
    SkillPack,
    WorkflowPack,
    WorkflowStep,
)

# ─── 5 个 Rule 预设 ───────────────────────────────────────

BUILTIN_RULES: list[RulePack] = [
    RulePack(
        id="builtin_rule_colloquial_dialogue",
        name="对话口语化",
        description="保持角色对话自然随意，避免书面语和翻译腔",
        type=PackType.RULE,
        content=(
            "【对话口语化规则】\n"
            "1. 角色对话必须使用日常口语，避免书面语、文言文和翻译腔。\n"
            "2. 多用短句、语气词（啊、吧、呢、嘛），符合人物身份和情绪。\n"
            "3. 不同角色要有 distinct 的说话方式：主角干脆利落，反派阴恻恻，长辈沉稳。\n"
            "4. 禁止角色说出不符合其身份/年龄/性格的话。\n"
            "5. 对话中可适当加入口头禅、方言词汇增加真实感。"
        ),
        category="dialogue",
        enabled=True,
        builtin=True,
    ),
    RulePack(
        id="builtin_rule_tight_pacing",
        name="节奏紧凑",
        description="删减不必要的过渡描写，每章至少一个冲突点",
        type=PackType.RULE,
        content=(
            "【节奏紧凑规则】\n"
            "1. 每章必须包含至少一个冲突点（矛盾、危机、反转、对决）。\n"
            "2. 删减不必要的环境描写和心理独白，超过3句的纯描写必须服务于情节。\n"
            "3. 场景切换要干脆，禁止用'与此同时'、'画面一转'等生硬过渡。\n"
            "4. 信息密度要高，每段都应推进剧情或揭示人物。\n"
            "5. 战斗/对峙场景用短句加快节奏，日常场景可适当放缓但不超过半章。"
        ),
        category="pace",
        enabled=True,
        builtin=True,
    ),
    RulePack(
        id="builtin_rule_decisive_protagonist",
        name="主角杀伐果断",
        description="主角不优柔寡断，有仇当场报，不圣母",
        type=PackType.RULE,
        content=(
            "【主角杀伐果断规则】\n"
            "1. 主角面对敌人绝不心慈手软，该杀就杀，该废就废。\n"
            "2. 有仇当场报，不搞'君子报仇十年不晚'的拖延。\n"
            "3. 禁止主角圣母心发作放过反派，除非有明确的利益算计。\n"
            "4. 主角做决策要干脆利落，不反复纠结、不内心挣扎超过一段。\n"
            "5. 对朋友讲义气，对敌人如寒冬，界限分明。\n"
            "6. 主角可以有算计和城府，但不能表现出懦弱和犹豫。"
        ),
        category="plot",
        enabled=True,
        builtin=True,
    ),
    RulePack(
        id="builtin_rule_plain_language",
        name="避免华丽辞藻",
        description="不用过多形容词和比喻，直白有力",
        type=PackType.RULE,
        content=(
            "【避免华丽辞藻规则】\n"
            "1. 禁止堆砌形容词，一句话最多一个修饰性形容词。\n"
            "2. 少用比喻和拟人，除非是关键场景的点睛之笔。\n"
            "3. 用动词驱动句子，而非形容词。"
            "'他一拳打飞敌人'优于'他猛地一拳狠狠地打飞了可恶的敌人'。\n"
            "4. 禁止使用'宛如'、'仿佛'、'犹如'开头的冗长比喻句。\n"
            "5. 环境描写点到为止，用一两个标志性细节代替全景式铺陈。\n"
            "6. 语言风格要像古龙/烽火戏诸侯，干脆、有力、留白。"
        ),
        category="style",
        enabled=False,
        builtin=True,
    ),
    RulePack(
        id="builtin_rule_chapter_hook",
        name="章节末钩子",
        description="每章结尾留悬念或反转，吸引读者追读",
        type=PackType.RULE,
        content=(
            "【章节末钩子规则】\n"
            "1. 每章结尾必须留下悬念、反转或危机，禁止平稳收尾。\n"
            "2. 钩子类型：强敌出现、秘密揭露、身份暴露、危机降临、反转打脸。\n"
            "3. 最后一段要短，最好一句话制造冲击。\n"
            "4. 可以用'就在这时'、'然而'、'他不知道的是'等转折，但不要滥用。\n"
            "5. 钩子必须与下一章内容衔接，不能是无意义的悬念。\n"
            "6. 高潮章可以用大反转收尾，过渡章用小悬念即可。"
        ),
        category="plot",
        enabled=True,
        builtin=True,
    ),
]

# ─── 3 个 Workflow 预设 ───────────────────────────────────

BUILTIN_WORKFLOWS: list[WorkflowPack] = [
    WorkflowPack(
        id="builtin_workflow_chapter_review",
        name="章节审稿流程",
        description="AI率检测→六维质量→连续性检查→去AI味，全流程审稿",
        type=PackType.WORKFLOW,
        trigger_command="/revise",
        steps=[
            WorkflowStep(
                name="AI率检测",
                description="检测文本AI痕迹，标记高风险段落",
                prompt=(
                    "你是AI文本检测专家。请分析以下章节文本，检测AI生成痕迹。\n"
                    "检测维度：句式重复度、用词模式化、情感平淡度、逻辑过度完美。\n"
                    "输出：AI率评分(0-100)、高风险段落位置、具体问题描述。\n\n"
                    "待检测文本：\n{chapter_text}"
                ),
                input_required=["chapter_text"],
            ),
            WorkflowStep(
                name="六维质量评估",
                description="从节奏、人物、对话、冲突、设定、文笔六个维度评分",
                prompt=(
                    "你是网文编辑。请从以下六个维度评估章节质量：\n"
                    "1. 节奏：是否紧凑，有无注水\n2. 人物：是否立体，行为是否合理\n"
                    "3. 对话：是否自然，是否推动剧情\n4. 冲突：是否有张力，是否解决\n"
                    "5. 设定：是否自洽，有无bug\n6. 文笔：是否流畅，有无语病\n\n"
                    "每维0-10分，给出具体改进建议。\n\n"
                    "待评估文本：\n{chapter_text}"
                ),
                input_required=["chapter_text"],
            ),
            WorkflowStep(
                name="连续性检查",
                description="检查与前文的人物、设定、情节连续性",
                prompt=(
                    "你是连续性审校员。请对比以下章节与前文摘要，检查：\n"
                    "1. 人物状态是否一致（伤势、位置、情绪）\n"
                    "2. 设定是否矛盾（修为、物品、时间线）\n"
                    "3. 情节是否衔接（上一章结尾→本章开头）\n"
                    "4. 伏笔是否被遗忘或矛盾\n\n"
                    "前文摘要：\n{previous_summary}\n\n本章文本：\n{chapter_text}"
                ),
                input_required=["chapter_text", "previous_summary"],
            ),
            WorkflowStep(
                name="去AI味改写",
                description="根据检测结果对高风险段落进行人性化改写",
                prompt=(
                    "你是去AI味改写专家。根据以下检测报告，对高风险段落进行改写。\n"
                    "改写原则：增加口语化表达、打破句式重复、加入人物个性、删减过度解释。\n"
                    "保持原意和情节不变，只改表达方式。\n\n"
                    "检测报告：\n{ai_detection_report}\n\n原始文本：\n{chapter_text}\n\n"
                    "输出改写后的完整文本。"
                ),
                input_required=["chapter_text", "ai_detection_report"],
            ),
        ],
        enabled=True,
        builtin=True,
    ),
    WorkflowPack(
        id="builtin_workflow_outline_generation",
        name="大纲生成流程",
        description="核心冲突→人物弧光→分卷结构→章节大纲，系统化生成",
        type=PackType.WORKFLOW,
        trigger_command="/outline",
        steps=[
            WorkflowStep(
                name="核心冲突设计",
                description="确定故事的核心矛盾和主线冲突",
                prompt=(
                    "你是网文策划。基于以下故事创意，设计核心冲突体系：\n"
                    "1. 主线冲突（主角 vs 终极反派/命运）\n2. 阶段性冲突（每卷的主要矛盾）\n"
                    "3. 内部冲突（主角内心挣扎）\n4. 冲突升级路径（如何逐步加码）\n\n"
                    "故事创意：\n{story_idea}\n\n输出冲突体系结构图。"
                ),
                input_required=["story_idea"],
            ),
            WorkflowStep(
                name="人物弧光设计",
                description="设计主角及主要角色的成长曲线",
                prompt=(
                    "你是人物设计师。基于核心冲突，设计主要角色的人物弧光：\n"
                    "1. 主角：起点状态→关键转变→终点状态，标注每个转变的触发事件\n"
                    "2. 主要反派：动机、手段、弱点、结局\n3. 重要配角：功能定位、与主角关系、结局\n"
                    "4. 人物关系网络图谱\n\n核心冲突：\n{core_conflict}"
                ),
                input_required=["core_conflict"],
            ),
            WorkflowStep(
                name="分卷结构规划",
                description="将故事拆分为若干卷，每卷有独立的起承转合",
                prompt=(
                    "你是结构编辑。基于人物弧光，规划分卷结构：\n"
                    "1. 确定总卷数和每卷主题\n2. 每卷的起承转合节点\n"
                    "3. 每卷的核心事件和高潮\n4. 卷间衔接和悬念设置\n5. 每卷预估章数\n\n"
                    "人物弧光：\n{character_arcs}"
                ),
                input_required=["character_arcs"],
            ),
            WorkflowStep(
                name="章节大纲细化",
                description="将分卷结构细化为逐章大纲",
                prompt=(
                    "你是大纲编辑。基于分卷结构，生成第{volume}卷的逐章大纲：\n"
                    "每章包含：章节标题、核心事件、出场人物、冲突点、章末钩子。\n"
                    "确保每章都有推进，节奏张弛有度。\n\n"
                    "分卷结构：\n{volume_structure}\n\n目标卷数：{volume}"
                ),
                input_required=["volume_structure", "volume"],
            ),
        ],
        enabled=True,
        builtin=True,
    ),
    WorkflowPack(
        id="builtin_workflow_cool_enhancement",
        name="爽点强化流程",
        description="识别当前场景→添加打脸/反转/升级元素→节奏优化",
        type=PackType.WORKFLOW,
        trigger_command="/cool",
        steps=[
            WorkflowStep(
                name="场景识别与爽点诊断",
                description="分析当前场景类型，诊断爽点不足",
                prompt=(
                    "你是爽文分析师。请分析以下场景：\n"
                    "1. 场景类型（打脸/升级/对决/揭秘/收小弟/获宝物）\n"
                    "2. 当前爽点强度评分(0-10)\n3. 爽点不足的具体原因\n"
                    "4. 可强化的方向建议\n\n场景文本：\n{scene_text}"
                ),
                input_required=["scene_text"],
            ),
            WorkflowStep(
                name="爽点元素添加",
                description="针对性添加打脸、反转、升级等爽点元素",
                prompt=(
                    "你是爽文写手。根据诊断报告，为场景添加爽点元素：\n"
                    "1. 打脸：让反派嚣张后被狠狠打脸，反差越大越好\n"
                    "2. 反转：在读者以为结局已定的时候翻转\n3. 升级：主角获得新能力/突破/宝物\n"
                    "4. 装逼：主角低调后亮明身份/实力，震惊全场\n"
                    "5. 收小弟/获美人：主角魅力征服他人\n\n"
                    "诊断报告：\n{diagnosis}\n\n原始场景：\n{scene_text}\n\n"
                    "输出强化后的完整场景。"
                ),
                input_required=["scene_text", "diagnosis"],
            ),
            WorkflowStep(
                name="节奏优化",
                description="优化场景节奏，确保爽点爆发到位",
                prompt=(
                    "你是节奏编辑。对以下爽文场景进行节奏优化：\n"
                    "1. 铺垫部分要短，快速进入冲突\n2. 反派嚣张要充分，激起读者愤怒\n"
                    "3. 主角反击要干脆利落，一击致命\n4.  aftermath 要写众人反应，放大爽感\n"
                    "5. 用短句加快战斗节奏，用留白制造冲击\n\n"
                    "待优化文本：\n{enhanced_scene}\n\n输出优化后的最终文本。"
                ),
                input_required=["enhanced_scene"],
            ),
        ],
        enabled=True,
        builtin=True,
    ),
]

# ─── 3 个 Skill 预设 ──────────────────────────────────────

BUILTIN_SKILLS: list[SkillPack] = [
    SkillPack(
        id="builtin_skill_xuanhuan_worldbuilding",
        name="玄幻世界观构建",
        description="修炼体系/境界划分/势力分布/资源体系专业知识",
        type=PackType.SKILL,
        knowledge=(
            "【玄幻世界观构建知识库】\n\n"
            "一、修炼体系设计原则\n"
            "1. 境界划分：通常9-12个大境界，每境分初/中/后/巅峰或1-9重\n"
            "   常见模板：炼气→筑基→金丹→元婴→化神→炼虚→合体→大乘→渡劫\n"
            "   男频爽文模板：淬体→聚气→灵武→元武→地武→天武→武王→武皇→武圣→武帝\n"
            "2. 每个境界要有明确的能力跃迁：飞天、遁地、寿元增加、领域等\n"
            "3. 境界差距要明显：高一阶碾压低阶，跨阶战斗需特殊条件\n\n"
            "二、势力分布结构\n"
            "1. 金字塔结构：顶尖宗门/皇朝→一流势力→二流→三流→散修\n"
            "2. 每个势力有：镇派功法、禁地、传承、与主角的关系（敌/友/中立）\n"
            "3. 地域划分：东荒/西漠/南疆/北原/中州，或大陆/海域/秘境\n"
            "4. 势力间要有矛盾和博弈，为主角提供舞台\n\n"
            "三、资源体系\n"
            "1. 货币：灵石（下品/中品/上品/极品）或玄晶/元石\n"
            "2. 修炼资源：丹药（1-9品）、功法（天/地/玄/黄阶）、武器（凡/灵/宝/仙器）\n"
            "3. 天材地宝：有等级、有产地、有守护妖兽\n"
            "4. 秘境/遗迹：定期开启，是主角获得机缘的重要场景\n\n"
            "四、世界观自洽要点\n"
            "1. 力量体系不能崩：前期设定的上限后期不能随意突破\n"
            "2. 经济体系要合理：高阶资源稀缺，低阶资源充足\n"
            "3. 历史背景：有上古大战、种族兴衰等设定增加厚度\n"
            "4. 种族设定：人族/妖族/魔族/蛮族，各有特色和矛盾"
        ),
        trigger_scenes=["world_building"],
        enabled=True,
        builtin=True,
    ),
    SkillPack(
        id="builtin_skill_character_arc",
        name="人物弧光设计",
        description="主角成长曲线/反派塑造/配角功能/关系网络",
        type=PackType.SKILL,
        knowledge=(
            "【人物弧光设计知识库】\n\n"
            "一、主角成长曲线设计\n"
            "1. 经典男频主角模板：废柴逆袭/天才陨落/穿越者/重生者/系统持有者\n"
            "2. 成长三阶段：\n"
            "   - 初期（1-200章）：立足阶段，获得金手指，解决眼前危机\n"
            "   - 中期（200-800章）：崛起阶段，建立势力，跨区域征战\n"
            "   - 后期（800章+）：巅峰阶段，面对终极反派，拯救世界/位面\n"
            "3. 每次重大转变需要触发事件：亲人被害、爱人被掳、兄弟背叛、境界突破\n"
            "4. 主角性格可以进化但不能OOC：从青涩到成熟，从冲动到沉稳\n\n"
            "二、反派塑造要点\n"
            "1. 反派要有合理动机：不是单纯的坏，而是立场不同/理念冲突/利益矛盾\n"
            "2. 反派分层：小boss（每章/每几章）→中boss（每卷）→大boss（全书）\n"
            "3. 反派要足够强：给主角造成真实威胁，不能太弱\n"
            "4. 经典反派类型：\n"
            "   - 天才型：与主角竞争，亦正亦邪\n   - 阴谋型：幕后操纵，布局深远\n"
            "   - 霸道型：实力碾压，不讲道理\n   - 背叛型：曾经的朋友/师长\n\n"
            "三、配角功能定位\n"
            "1. 兄弟/伙伴：提供情感支持和战力补充，要有独立人格\n"
            "2. 导师/长辈：传授知识，提供资源，适时退场让主角独立\n"
            "3. 红颜/女主：不能是花瓶，要有自己的目标和成长线\n"
            "4. 对手/竞争者：亦敌亦友，推动主角进步\n"
            "5. 搞笑担当：调节气氛，但不能在关键时刻掉链子\n\n"
            "四、关系网络构建\n"
            "1. 每个重要角色与主角的关系要明确：恩/怨/情/仇/利\n"
            "2. 关系可以变化：从敌到友、从友到敌、从陌生到生死之交\n"
            "3. 避免工具人：每个配角至少有一个独立于主角的目标\n"
            "4. 群像戏要控制：同时活跃的重要角色不超过7个"
        ),
        trigger_scenes=["character_design"],
        enabled=True,
        builtin=True,
    ),
    SkillPack(
        id="builtin_skill_combat_writing",
        name="战斗场景写作",
        description="战斗节奏/招式描写/战力对比/胜负转折",
        type=PackType.SKILL,
        knowledge=(
            "【战斗场景写作知识库】\n\n"
            "一、战斗节奏控制\n"
            "1. 三段式结构：试探→激战→决胜\n"
            "2. 试探阶段：双方互相观察，用小招式试探底细，占15%\n"
            "3. 激战阶段：你来我往，招式升级，各有损伤，占60%\n"
            "4. 决胜阶段：一方放大招/突破/用计，一击定胜负，占25%\n"
            "5. 用短句和分段加快节奏，长句用于描写大招特效\n\n"
            "二、招式描写技巧\n"
            "1. 招式命名要有逼格：四字/七字，包含意象（龙、虎、雷、火、剑）\n"
            "   例：'苍龙破狱拳'、'九霄惊雷指'、'万剑归宗'\n"
            "2. 描写三要素：起手式→过程→效果\n"
            "3. 效果描写要具体：不是'威力巨大'，而是'地面炸裂三丈，碎石横飞'\n"
            "4. 同一场战斗不重复使用相同描写，每次出招要有变化\n"
            "5. 大招要蓄力：先写气势积累、环境变化，再写爆发\n\n"
            "三、战力对比与跨阶战斗\n"
            "1. 同阶战斗：五五开，靠技巧/意志/临场突破取胜\n"
            "2. 越阶战斗：必须有合理条件（特殊体质/神器/功法克制/对方轻敌）\n"
            "3. 碾压战斗：快速解决，重点写旁观者反应和反派震惊\n"
            "4. 群战：先写整体局势，再聚焦主角对决，穿插配角战况\n"
            "5. 战力不能崩：前期设定的境界差距后期要保持\n\n"
            "四、胜负转折设计\n"
            "1. 经典转折方式：\n"
            "   - 突破：战斗中突破境界，反败为胜\n   - 底牌：亮出隐藏的杀招/神器\n"
            "   - 用计：诱敌深入，设下陷阱\n   - 外援：关键时刻有人相助\n"
            "   - 意志：靠不屈意志撑到对方力竭\n"
            "2. 转折要有铺垫：不能凭空出现，前文要有伏笔\n"
            "3. 胜利后要有 aftermath：写主角状态、敌人结局、旁观者反应\n"
            "4. 失败也要有价值：获得经验/认清差距/激发斗志，不能白输\n\n"
            "五、战斗场景禁忌\n"
            "1. 禁止流水账：不能'他打了一拳，对方踢了一脚'无限循环\n"
            "2. 禁止解说员模式：不要让角色在战斗中长篇大论解释招式\n"
            "3. 禁止无限升级：一场战斗不能连续突破好几次\n"
            "4. 禁止忽略伤势：受了重伤不能跟没事人一样继续打"
        ),
        trigger_scenes=["combat"],
        enabled=True,
        builtin=True,
    ),
]


def get_all_builtin_packs() -> list[dict]:
    """获取所有内置包的 dict 表示（用于合并到列表）"""
    packs: list[dict] = [rule.model_dump() for rule in BUILTIN_RULES]
    packs.extend(wf.model_dump() for wf in BUILTIN_WORKFLOWS)
    packs.extend(skill.model_dump() for skill in BUILTIN_SKILLS)
    return packs


def get_builtin_pack_by_id(pack_id: str) -> dict | None:
    """按 ID 查找内置包"""
    for pack in get_all_builtin_packs():
        if pack["id"] == pack_id:
            return pack
    return None
