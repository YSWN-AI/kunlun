"""
昆仑创作引擎 — 文本精炼引擎

职责: 检测并替换网文中的高频套路词、过度描写、冗余表达。
零LLM成本，纯规则替换。

词库来源: 网文编辑经验 + 读者反馈 + AI生成文本特征分析

使用方式:
    refiner = TextRefiner()
    refined = refiner.refine(text)
    report = refiner.analyze(text)  # 仅分析不修改
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RefinementRule:
    """精炼规则"""

    pattern: str  # 匹配模式（支持正则）
    replacement: str  # 替换文本 (""=删除)
    category: str = ""  # 分类
    description: str = ""  # 说明
    severity: float = 0.5  # 0-1 严重程度


@dataclass
class RefinementReport:
    """精炼报告"""

    total_fixes: int = 0
    fixes_by_category: dict = field(default_factory=dict)
    original_length: int = 0
    refined_length: int = 0
    savings: int = 0
    details: list[dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════
# 精炼规则库
# 按分类组织: 感官/程度/表情/动作/声音/心理/时间/转折/套路句式
# ═══════════════════════════════════════════════════════

REFINEMENT_RULES: list[RefinementRule] = [
    # ── 感官类过度使用词 ──────────────────────────
    RefinementRule("冰冷", "冷", "感官", "用'冷'代替'冰冷'"),
    RefinementRule("冰凉", "凉", "感官", "用'凉'代替'冰凉'"),
    RefinementRule("漆黑", "黑", "感官", "用'黑'代替'漆黑'"),
    RefinementRule("滚烫", "烫", "感官", "用'烫'代替'滚烫'"),
    RefinementRule("炙热", "灼热", "感官", "减少热度描写堆砌"),
    RefinementRule("甜腻", "甜", "感官", "用'甜'代替'甜腻'"),
    # ── 程度副词过度使用 ──────────────────────────
    RefinementRule("十分", "很", "程度副词", "用'很'或删除"),
    RefinementRule("非常", "", "程度副词", "直接删除，用更强动词"),
    RefinementRule("极其", "极", "程度副词", "减少使用"),
    RefinementRule("无比", "", "程度副词", "直接删除"),
    RefinementRule("绝对", "", "程度副词", "直接删除或换具体表述"),
    RefinementRule("确实", "", "程度副词", "删除，AI感强"),
    RefinementRule("几乎", "", "程度副词", "删除或换具体数字"),
    RefinementRule("略微|稍稍|微微", "", "程度副词", "删除或换具体动作"),
    RefinementRule("一定程度", "", "程度副词", "删除，AI感强"),
    RefinementRule("相当", "", "程度副词", "删除或换'很'"),
    RefinementRule("颇[为有]", "", "程度副词", "删除"),
    # ── 表情/神态过度描写 ────────────────────────
    RefinementRule("淡淡地?说", "说", "表情", "直接用'说'"),
    RefinementRule("缓缓地说", "说", "表情", "直接用'说'"),
    RefinementRule("声音平静", "", "表情", "通过对话内容体现，不直接说明"),
    RefinementRule("声音坚定", "", "表情", "通过对话内容体现"),
    RefinementRule("声音轻细", "低声道", "表情", "更简洁"),
    RefinementRule("眼神坚定", "", "表情", "删除或换具体动作"),
    RefinementRule("眼神锐利", "", "表情", "过度描写，换具体表现"),
    RefinementRule("眼神深邃", "", "表情", "过度描写，换具体表现"),
    RefinementRule("眼神热切", "", "表情", "过度描写"),
    RefinementRule("嘴角勾起一抹", "嘴角一勾", "表情", "简化"),
    RefinementRule("嘴角勾起", "笑了", "表情", "简化"),
    RefinementRule("脸上带着笑意", "笑道", "表情", "简化"),
    RefinementRule("脸上堆满了笑", "赔笑", "表情", "简化"),
    RefinementRule("不卑不亢", "", "表情", "删除，用具体态度描写"),
    RefinementRule("不动声色", "没吭声", "表情", "口语化"),
    RefinementRule("面无表情", "", "表情", "直接描写动作"),
    RefinementRule("脸色一变", "脸色变了", "表情", "简化"),
    RefinementRule("脸色一沉", "沉下脸", "表情", "简化"),
    RefinementRule("眼中闪过一丝", "眼中闪过", "表情", "简化"),
    # ── 动作词精炼 ──────────────────────────────
    RefinementRule("点了点头", "点头", "动作", "简化"),
    RefinementRule("摇了摇头", "摇头", "动作", "简化"),
    RefinementRule("微微(一)?(怔|愣|顿)", "怔住", "动作", "简化"),
    RefinementRule("猛地站起", "站起", "动作", "去掉副词"),
    RefinementRule("连忙", "", "动作", "删除或换'赶紧'"),
    RefinementRule("迅速", "", "动作", "删除或换具体时间"),
    RefinementRule("立刻", "", "动作", "删除或换'当即'"),
    RefinementRule("瞬间", "", "动作", "删除"),
    RefinementRule("顿时", "", "动作", "删除"),
    RefinementRule("[一]?咬牙", "咬牙", "动作", "简化"),
    RefinementRule("咬了咬牙", "咬牙", "动作", "简化"),
    RefinementRule("[一]?跺脚", "跺脚", "动作", "简化"),
    RefinementRule("深吸一口气", "吸了口气", "动作", "简化"),
    RefinementRule("小心翼翼", "小心", "动作", "简化"),
    RefinementRule("行云流水", "", "动作", "删除，换具体描写"),
    RefinementRule("抖如筛糠", "发抖", "动作", "减少夸张成语"),
    # ── 声音描写精炼 ────────────────────────────
    RefinementRule("轰", "砰", "声音", "用更具体的拟声词"),
    RefinementRule("闷响", "", "声音", "用具体拟声词"),
    RefinementRule("炸雷", "", "声音", "过度夸张"),
    RefinementRule("电弧", "", "声音", "减少玄幻感"),
    RefinementRule("风箱般的?破风声", "风声", "声音", "简化"),
    RefinementRule("骨骼发出脆响", "骨节响", "声音", "简化"),
    RefinementRule("刺入.*?心脏", "", "声音", "减少血腥描写"),
    RefinementRule("耳膜生疼", "", "声音", "删除或换"),
    # ── 心理描写精炼 ────────────────────────────
    RefinementRule("心中", "", "心理", "删除或换'心里'"),
    RefinementRule("他知道", "", "心理", "删除，通过行动体现"),
    RefinementRule("他不知道", "", "心理", "删除或换疑问"),
    RefinementRule("他觉得", "", "心理", "删除或换'感觉'"),
    RefinementRule("心中了然", "", "心理", "冗余"),
    RefinementRule("心下了然", "", "心理", "冗余"),
    RefinementRule("心中?一[动凛沉]", "", "心理", "删除或简化"),
    RefinementRule("意识到", "", "心理", "删除或换'发现'"),
    RefinementRule("[我你他她]知道[了]?", "", "心理", "减少'×知道(了)'告知式，用行动体现"),
    RefinementRule("认为", "", "心理", "删除或换'觉得'"),
    RefinementRule("觉得", "", "心理", "减少使用"),
    RefinementRule("忍不住", "", "心理", "删除"),
    RefinementRule("不禁", "", "心理", "删除"),
    # ── 时间词精炼 ──────────────────────────────
    RefinementRule("此刻", "这时", "时间", "口语化"),
    RefinementRule("一时间", "", "时间", "删除"),
    RefinementRule("一时之间", "", "时间", "删除"),
    RefinementRule("再次", "又", "时间", "简化"),
    RefinementRule("终于", "", "时间", "删除"),
    RefinementRule("突然", "", "时间", "删除或换'猛地'"),
    RefinementRule("忽然", "", "时间", "删除"),
    RefinementRule("渐渐的?", "", "时间", "删除"),
    RefinementRule("即将", "", "时间", "删除或换'就要'"),
    RefinementRule("即将到来", "", "时间", "删除"),
    RefinementRule("在此之前", "", "时间", "删除"),
    # ── 转折/连词精炼 ────────────────────────────
    RefinementRule("然而", "但", "转折", "简化"),
    RefinementRule("虽然", "", "转折", "删除或调整语序"),
    RefinementRule("但是", "但", "转折", "简化"),
    RefinementRule("却[不没]", "", "转折", "删除"),
    RefinementRule("不过", "", "转折", "删除或换'但'"),
    RefinementRule("可是", "可", "转折", "简化"),
    RefinementRule("以及", "和", "转折", "简化"),
    RefinementRule("而且", "", "转折", "删除"),
    RefinementRule("此外", "", "转折", "删除"),
    RefinementRule("总而言之", "", "转折", "删除"),
    # ── 套路句式 ────────────────────────────────
    RefinementRule("空气[仿佛凝?]滞", "", "套路句式", "删除套话"),
    RefinementRule("气氛凝固", "", "套路句式", "用具体描写替代"),
    RefinementRule("死寂", "", "套路句式", "用具体场景替代"),
    RefinementRule("[窒沉]寂", "", "套路句式", "减少使用"),
    RefinementRule("冷寂", "", "套路句式", "减少使用"),
    RefinementRule("凝固", "", "套路句式", "减少抽象描写"),
    RefinementRule("炸开", "", "套路句式", "用具体动词替代"),
    RefinementRule("撕裂", "", "套路句式", "减少夸张描写"),
    RefinementRule("波涛汹涌", "", "套路句式", "减少夸张"),
    RefinementRule("无法想象", "", "套路句式", "直接描写"),
    RefinementRule("无法用言语形容", "", "套路句式", "直接描写"),
    RefinementRule("不可置信", "不敢相信", "套路句式", "口语化"),
    RefinementRule("不可估量", "", "套路句式", "换具体数字/程度"),
    RefinementRule("不可置疑", "", "套路句式", "删除"),
    RefinementRule("不容置疑", "", "套路句式", "删除"),
    RefinementRule("至关重要", "重要", "套路句式", "简化"),
    RefinementRule("取而代之的是", "取而代之", "套路句式", "简化"),
    RefinementRule("这[不]?不是.*?而是", "", "套路句式", "简化对比句式"),
    # ── 过渡/铺垫套话 ──────────────────────────
    RefinementRule("接下来", "", "过渡套话", "直接推进剧情"),
    RefinementRule("这一次", "", "过渡套话", "删除"),
    RefinementRule("这一刻", "", "过渡套话", "删除"),
    RefinementRule("不过", "", "过渡套话", "删除或换'但'"),
    RefinementRule("话锋一转", "", "过渡套话", "用具体对话替代"),
    RefinementRule("就在这时", "", "过渡套话", "删除或换'突然'"),
    RefinementRule("正在这时", "", "过渡套话", "删除"),
    RefinementRule("不知过了多久", "", "过渡套话", "用具体时间点替代"),
    # ── 修饰词精炼 ──────────────────────────────
    RefinementRule("巨大的?", "", "修饰词", "用具体尺寸或删除"),
    RefinementRule("剧烈的?", "", "修饰词", "用具体动词"),
    RefinementRule("明显的?", "", "修饰词", "删除"),
    RefinementRule("显著的?", "", "修饰词", "删除"),
    RefinementRule("绝对的?", "", "修饰词", "删除"),
    RefinementRule("纯粹的?", "", "修饰词", "删除"),
    RefinementRule("某种[程度意义上]", "", "修饰词", "删除"),
    RefinementRule("一丝", "", "修饰词", "删除"),
    RefinementRule("一抹", "", "修饰词", "删除"),
    RefinementRule("一股", "", "修饰词", "删除或换具体感受"),
    RefinementRule("一阵", "", "修饰词", "删除"),
    RefinementRule("些许", "些", "修饰词", "口语化"),
    RefinementRule("显得异常", "很", "修饰词", "简化"),
    # ── 复合套路（多词组合） ─────────────────────
    RefinementRule("如被.*?扼住.*?咽喉", "", "复合套路", "删除浮夸比喻"),
    RefinementRule("像.*?淬了毒.*?", "", "复合套路", "删除"),
    RefinementRule("让空气的?温度都下降", "", "复合套路", "删除"),
    RefinementRule("嘴巴张得能塞下一个鸡蛋", "", "复合套路", "换'目瞪口呆'"),
    RefinementRule("像在看.*?人", "", "复合套路", "简化"),
    RefinementRule("时间仿佛被按下.*?暂停", "", "复合套路", "删除AI套话"),
    RefinementRule("空气凝滞如铁", "", "复合套路", "删除"),
    RefinementRule("力道大得惊人", "", "复合套路", "换具体表现"),
    RefinementRule("透露出的寒意", "", "复合套路", "删除"),
    RefinementRule("背在身后的手已经全是冷汗", "", "复合套路", "简化或删除"),
    RefinementRule("变得像西伯利亚的寒风一样", "", "复合套路", "删除浮夸比喻"),
    RefinementRule("像.*?寒冰.*?刺骨", "", "复合套路", "删除浮夸比喻"),
    RefinementRule("给人一种.*?感觉", "", "复合套路", "删除"),
    RefinementRule("有一种.*?错觉", "", "复合套路", "删除"),
    # ── 解释性话语（TextHumanize: AI倾向于过度解释） ────
    RefinementRule("也就是说", "", "解释性", "删除AI解释腔"),
    RefinementRule("换句话说", "", "解释性", "删除AI解释腔"),
    RefinementRule("这意味着", "", "解释性", "删除AI解释腔"),
    RefinementRule("其实就是", "", "解释性", "直接叙述"),
    RefinementRule("说白了", "", "解释性", "直接叙述"),
    RefinementRule("本质上", "", "解释性", "删除"),
    RefinementRule("说到底", "", "解释性", "删除"),
    RefinementRule("实际上", "", "解释性", "删除"),
    RefinementRule("事实上", "", "解释性", "删除"),
    RefinementRule("换言之", "", "解释性", "删除书面解释"),
    RefinementRule("如此看来", "", "解释性", "删除"),
    RefinementRule("由此可见", "", "解释性", "删除AI总结"),
    RefinementRule("正因如此", "", "解释性", "删除"),
    RefinementRule("不难看出", "", "解释性", "删除"),
    RefinementRule("也就是说", "", "解释性", "删除"),
    RefinementRule("这样一来", "", "解释性", "删除"),
    RefinementRule("这就意味着", "", "解释性", "删除"),
    # ── 被动/弱化表达（TextHumanize: 增强文字力度） ────
    RefinementRule("被[^。，]{2,10}击中", "", "弱化表达", "换主动式"),
    RefinementRule("遭到了", "", "弱化表达", "换'遭'或主动式"),
    RefinementRule("受到了", "", "弱化表达", "删除或换'被'"),
    RefinementRule("得到了", "", "弱化表达", "删除或换'获'"),
    RefinementRule("引起了", "", "弱化表达", "换具体动词"),
    RefinementRule("进行了", "", "弱化表达", "删除"),
    RefinementRule("做出了", "做出", "弱化表达", "简化"),
    RefinementRule("给予了", "给了", "弱化表达", "口语化"),
    # ── 对话标签简化（Humanizer: 废话对白标签） ────
    RefinementRule("开口说[道]", "说", "对话标签", "简化"),
    RefinementRule("出声说[道]", "说", "对话标签", "简化"),
    RefinementRule("缓缓说[道]", "说", "对话标签", "简化"),
    RefinementRule("轻声说[道]", "说", "对话标签", "简化"),
    RefinementRule("回答说[道]", "说", "对话标签", "简化"),
    RefinementRule("回答道", "说", "对话标签", "简化"),
    RefinementRule("开口问道", "问", "对话标签", "简化"),
    RefinementRule("出声问道", "问", "对话标签", "简化"),
    RefinementRule("回问道", "问", "对话标签", "简化"),
    # ── 过度逻辑连接（TextHumanize: 减少逻辑连词） ────
    RefinementRule("首先", "", "逻辑连接", "直接推进"),
    RefinementRule("其次", "", "逻辑连接", "直接推进"),
    RefinementRule("最后", "", "逻辑连接", "直接推进"),
    RefinementRule("第一[，、:]", "", "逻辑连接", "直接叙述"),
    RefinementRule("第二[，、:]", "", "逻辑连接", "直接叙述"),
    RefinementRule("第三[，、:]", "", "逻辑连接", "直接叙述"),
    RefinementRule("一方面", "", "逻辑连接", "删除"),
    RefinementRule("另一方面", "", "逻辑连接", "删除"),
    RefinementRule("不仅如此", "", "逻辑连接", "删除"),
    RefinementRule("与此同[一时]", "", "逻辑连接", "删除"),
    RefinementRule("此外", "", "逻辑连接", "删除"),
    RefinementRule("另外", "", "逻辑连接", "删除或换'还有'"),
    RefinementRule("再加上", "", "逻辑连接", "删除"),
    RefinementRule("与之相对应[的]?", "", "逻辑连接", "删除"),
    RefinementRule("基于此", "", "逻辑连接", "删除"),
    # ── 抽象叙述改具体（GankAIGC: 用感官描写替代抽象） ──
    RefinementRule("感觉[到了]?", "", "抽象叙事", "换感官描写"),
    RefinementRule("感到[了一种]?", "", "抽象叙事", "换具体表现"),
    RefinementRule("感受到[了]?", "", "抽象叙事", "换具体表现"),
    RefinementRule("让人感到", "", "抽象叙事", "直接描写"),
    RefinementRule("令人", "让人", "抽象叙事", "口语化"),
    RefinementRule("给人一种", "", "抽象叙事", "删除"),
    RefinementRule("充满[了]?", "", "抽象叙事", "换具体描写"),
    RefinementRule("弥漫着[一股]", "", "抽象叙事", "换具体描写"),
    RefinementRule("散发着", "", "抽象叙事", "换具体描写"),
    # ── 高频冗余词专项（用户反馈词库） ──────────────────
    RefinementRule("不断", "", "冗余词", "删除或换'不停'"),
    RefinementRule("扯出", "扯", "冗余词", "简化"),
    RefinementRule("沉寂", "", "冗余词", "用具体状态替代"),
    RefinementRule("沉吟", "", "冗余词", "换'想了想'或动作描写"),
    RefinementRule("沉重", "", "冗余词", "用具体感受替代"),
    RefinementRule("大致", "", "冗余词", "删除"),
    RefinementRule("沸腾", "", "冗余词", "换具体情绪表现"),
    RefinementRule("更是", "", "冗余词", "删除"),
    RefinementRule("果然", "", "冗余词", "删除或融入上下文"),
    RefinementRule("裹挟", "", "冗余词", "用具体动词替代"),
    RefinementRule("仿佛", "", "冗余词", "删除或换'像'"),
    RefinementRule("好像", "", "冗余词", "删除"),
    RefinementRule("似乎", "", "冗余词", "删除"),
    RefinementRule("或许", "", "冗余词", "删除或换'可能'"),
    RefinementRule("紧锁", "", "冗余词", "换'皱眉'或动作"),
    RefinementRule("就这", "", "冗余词", "口语化或删除"),
    RefinementRule("剧痛", "疼", "冗余词", "简化为'疼'"),
    RefinementRule("军靴", "靴子", "冗余词", "用'靴子'替代"),
    RefinementRule("看似", "", "冗余词", "删除或换'表面'"),
    RefinementRule("可能", "", "冗余词", "删除"),
    RefinementRule("恐怕", "", "冗余词", "删除"),
    RefinementRule("口吻", "", "冗余词", "用'语气'或动作替代"),
    RefinementRule("脸色", "", "冗余词", "用具体表情替代"),
    RefinementRule("扭曲", "", "冗余词", "用具体形态替代"),
    RefinementRule("清淡", "", "冗余词", "用具体味道替代"),
    RefinementRule("清冷", "冷清", "冗余词", "简化"),
    RefinementRule("如同", "", "冗余词", "删除或换'像'"),
    RefinementRule("闪烁", "", "冗余词", "用具体发光词替代"),
    RefinementRule("像是", "", "冗余词", "删除"),
    RefinementRule("随时", "", "冗余词", "删除或换具体时间"),
    RefinementRule("宣战", "", "冗余词", "删除夸张"),
    RefinementRule("有点", "", "冗余词", "删除或换'稍'"),
    RefinementRule("暂时", "", "冗余词", "删除"),
    RefinementRule("郑重", "", "冗余词", "用具体态度描写"),
    RefinementRule("窒息", "", "冗余词", "用呼吸描写替代"),
    RefinementRule("注定", "", "冗余词", "删除或具体化"),
    RefinementRule("诅咒", "", "冗余词", "具体化或换'骂'"),
    RefinementRule("似乎", "", "冗余词", "删除"),
    RefinementRule("显然", "", "冗余词", "删除，直接展示"),
    # ── 双字冗余组合 ──────────────────────────────
    RefinementRule("粗糙的?手", "粗手", "冗余组合", "简化"),
    RefinementRule("淡淡地[说看笑]", "", "冗余组合", "直接动作"),
    RefinementRule("[他她]的目光", "", "冗余组合", "删除'的目光'"),
    RefinementRule("激动地[说喊道]", "激动", "冗余组合", "删副词"),
    RefinementRule("[他她]僵住了", "", "冗余组合", "换具体反应"),
    RefinementRule("精准地", "", "冗余组合", "删除或具体化"),
    RefinementRule("平静地", "", "冗余组合", "删除"),
    RefinementRule("[他她]却没有", "", "冗余组合", "简化"),
    RefinementRule("以一种", "", "冗余组合", "删除"),
    RefinementRule("这一次", "", "冗余组合", "删除"),
    RefinementRule("这一刻", "", "冗余组合", "删除"),
    RefinementRule("[没有]什么", "没啥", "冗余组合", "口语化"),
    # ── AI 常见套路表达（用户反馈） ────────────────
    RefinementRule("带着一丝", "", "AI套话", "删除"),
    RefinementRule("带着几分", "", "AI套话", "删除"),
    RefinementRule("微微挑眉", "挑眉", "AI套话", "简化"),
    RefinementRule("目光扫过", "扫过", "AI套话", "简化"),
    RefinementRule("近乎偏执", "", "AI套话", "删除或具体化"),
    RefinementRule("洗得发[白亮]", "旧", "AI套话", "简化"),
    RefinementRule("指节泛白", "", "AI套话", "删除过度描写"),
    RefinementRule("[他她]的心一跳", "", "AI套话", "换具体反应"),
    RefinementRule("[他她]的脸变了", "", "AI套话", "具体化"),
    RefinementRule("隐隐有了猜测", "", "AI套话", "删除或具体化"),
    RefinementRule("心里隐隐有了猜测", "", "AI套话", "删除"),
    RefinementRule("心中一片平静", "", "AI套话", "换动作描写"),
    RefinementRule("显得有些兴奋", "", "AI套话", "直接描写兴奋"),
    RefinementRule("显得异常[的]?", "很", "AI套话", "简化"),
    RefinementRule("显得异常清晰", "清晰", "AI套话", "简化"),
    RefinementRule("甚至没去看", "", "AI套话", "简化"),
    RefinementRule("我都要烦死了", "烦死了", "AI套话", "简化"),
    RefinementRule("锐利的?眼睛", "", "AI套话", "具体化"),
    RefinementRule("重叠和塌陷", "", "AI套话", "删除夸张"),
    RefinementRule("[他她]的?眼神", "", "AI套话", "换具体动作"),
    RefinementRule("带着不容置疑的?", "", "AI套话", "删除"),
    RefinementRule("令人牙酸的?", "", "AI套话", "换具体声音"),
    RefinementRule("生涩的?摩擦声", "摩擦声", "AI套话", "简化"),
    RefinementRule("[他她]的表情变暗", "", "AI套话", "换具体表情"),
    RefinementRule("淡淡地应[了]?一句", "", "AI套话", "简化"),
    RefinementRule("骨灰盒批发部", "", "AI套话", "删除浮夸"),
    RefinementRule("我赢了", "", "AI套话", "融入对话"),
    # ── 超长 AI 套话（用户反馈 + TextHumanize） ───
    RefinementRule("[他她]的嘴角微微上扬", "", "超长套话", "换'笑了'或'勾起嘴角'"),
    RefinementRule("眼中流露出.*?表情", "", "超长套话", "直接描写眼神"),
    RefinementRule("像是要看穿[他她]的?灵魂", "", "超长套话", "简化"),
    RefinementRule("嘴角勾起一个.*?的弧度", "", "超长套话", "换'笑了'"),
    RefinementRule("让空气都凝固了", "", "超长套话", "删除"),
    RefinementRule("语气平淡得像是在谈论今天的天气", "", "超长套话", "换'平淡地说'"),
    RefinementRule("没有狂风呼啸，亦无雷霆万钧", "", "超长套话", "直接描写"),
    RefinementRule("表面稳得一批", "", "超长套话", "换具体状态"),
    RefinementRule("水银泻地般", "", "超长套话", "换具体描写"),
    RefinementRule("针尖般", "", "超长套话", "换'尖锐'"),
    RefinementRule("化作漫天飞溅的木屑", "", "超长套话", "删除浮夸"),
    RefinementRule("却重重砸在.*?心头", "", "超长套话", "简化"),
    RefinementRule("[他她]看得目瞪口呆", "目瞪口呆", "超长套话", "简化"),
    RefinementRule("心里像是有.*?在翻涌", "", "超长套话", "删除"),
    RefinementRule("空气仿佛凝固了", "", "超长套话", "删除"),
    RefinementRule("像是被.*?扼住了喉咙", "", "超长套话", "删除浮夸比喻"),
    RefinementRule("[他她]的瞳孔猛[地一]缩", "", "超长套话", "简化或删除"),
    RefinementRule("一种说不出的.*?感觉", "", "超长套话", "直接描写"),
    RefinementRule("时间[仿佛]?在这一刻停止了", "", "超长套话", "删除"),
    RefinementRule("[他她]感觉自己的心脏[都]?要跳出来了", "", "超长套话", "简化"),
]


class TextRefiner:
    """
    文本精炼引擎

    纯规则替换，无LLM调用。用于写作管线的润色阶段。
    逐条规则替换，提供替换报告。
    """

    def __init__(self):
        self._compiled = [(re.compile(rule.pattern), rule) for rule in REFINEMENT_RULES]

    def analyze(self, text: str) -> RefinementReport:
        """仅分析不修改，返回命中报告"""
        report = RefinementReport(
            original_length=len(text),
        )
        for compiled, rule in self._compiled:
            matches = list(compiled.finditer(text))
            if matches:
                count = len(matches)
                report.total_fixes += count
                report.fixes_by_category[rule.category] = (
                    report.fixes_by_category.get(rule.category, 0) + count
                )
                report.details.append(
                    {
                        "pattern": rule.pattern,
                        "replacement": rule.replacement,
                        "category": rule.category,
                        "count": count,
                        "severity": rule.severity,
                    }
                )
                # 计算节省字数（使用完整匹配长度）
                for m in matches:
                    report.savings += len(m.group())
        return report

    def refine(self, text: str, max_passes: int = 2) -> tuple[str, RefinementReport]:
        """
        精炼文本

        Args:
            text: 输入文本
            max_passes: 最大替换轮次（防止死循环）

        Returns:
            (精炼后的文本, 精炼报告)
        """
        if not text:
            return text, RefinementReport()

        report = RefinementReport(original_length=len(text))
        result = text
        pass_num = 0

        while pass_num < max_passes:
            pass_num += 1
            changed = False

            for compiled, rule in self._compiled:
                # 空字符串替换表示"删除匹配文本"，继续执行替换
                # 仅当 replacement 为 None 时跳过（标记性规则不修改文本）
                if rule.replacement is None:
                    continue

                new_text, count = compiled.subn(rule.replacement, result)
                if count > 0:
                    result = new_text
                    changed = True
                    report.total_fixes += count
                    report.fixes_by_category[rule.category] = (
                        report.fixes_by_category.get(rule.category, 0) + count
                    )
                    report.details.append(
                        {
                            "pattern": rule.pattern,
                            "replacement": rule.replacement,
                            "category": rule.category,
                            "count": count,
                        }
                    )

            if not changed:
                break

        # 清理多余空格和重复标点
        result = re.sub(r"\s{2,}", " ", result)
        result = re.sub(r"([。！？，、])[。！？，、]+", r"\1", result)

        report.refined_length = len(result)
        report.savings = report.original_length - report.refined_length
        return result, report

    def get_stats(self, text: str) -> dict:
        """获取文本质量统计"""
        report = self.analyze(text)
        issues_per_1000 = report.total_fixes / max(len(text), 1) * 1000
        return {
            "total_issues": report.total_fixes,
            "issues_per_1000_chars": round(issues_per_1000, 1),
            "categories": dict(report.fixes_by_category),
            "estimated_savings": report.savings,
            "quality_rating": self._rate_quality(issues_per_1000),
        }

    @staticmethod
    def _rate_quality(issues_per_1000: float) -> str:
        if issues_per_1000 < 3:
            return "优秀"
        if issues_per_1000 < 8:
            return "良好"
        if issues_per_1000 < 15:
            return "一般—建议润色"
        return "较差—需要精炼"


# 全局单例
text_refiner = TextRefiner()


# 便捷函数
def refine_text(text: str) -> tuple[str, RefinementReport]:
    """一键精炼"""
    return text_refiner.refine(text)


def analyze_text(text: str) -> RefinementReport:
    """一键分析"""
    return text_refiner.analyze(text)
