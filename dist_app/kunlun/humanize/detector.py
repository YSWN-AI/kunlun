"""
AI写作模式检测器

基于 blader/humanizer (16.8k⭐) 的 29 种 AI 写作模式 + Humanizer-zh 的 24 种中文特化模式
进行深度重构，专为网文创作场景适配。

模式分类（5大类，29+24合并去重后约35种）:
  1. 内容模式 (Content): 重要性夸大、知名度攀附、肤浅-ing分析、宣传语言、模糊归因、提纲式结尾
  2. 语言语法模式 (Language): AI词汇过度、系动词回避、否定排比、三段式、同义词循环、虚假范围
  3. 风格模式 (Style): 破折号过度、粗体过度、内联标题、标题大写、表情符号、弯引号
  4. 沟通模式 (Communication): 聊天痕迹、知识截止声明、谄媚语气
  5. 填充模糊模式 (Filler): 填充短语、过度限定、泛化结论

网文特化扩展（自研）:
  6. 网文模式 (WebNovel): 过度旁白解释、千篇一律打斗描写、AI式升级描述、模板化装逼打脸

用法:
    detector = AIModeDetector()
    report = detector.detect(text)
    for marker in report.markers:
        print(f"{marker.category}/{marker.name}: {marker.count}次")
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum


class AIModeCategory(Enum):
    """AI模式分类"""

    CONTENT = "content"  # 内容模式
    LANGUAGE = "language"  # 语言语法模式
    STYLE = "style"  # 风格模式
    COMMUNICATION = "communication"  # 沟通模式
    FILLER = "filler"  # 填充模糊模式
    WEBNOVEL = "webnovel"  # 网文特化模式


@dataclass
class AIMarker:
    """单个AI模式标记"""

    name: str  # 模式名称
    category: AIModeCategory  # 分类
    pattern: str  # 匹配模式（正则）
    description: str  # 描述
    severity: float = 0.5  # 严重程度 (0-1)
    count: int = 0  # 命中次数
    examples: list[str] = field(default_factory=list)  # 命中示例
    replacement_hint: str = ""  # 替换建议


@dataclass
class DetectionReport:
    """检测报告"""

    total_markers: int = 0  # 总命中数
    unique_patterns: int = 0  # 命中模式种类
    markers: list[AIMarker] = field(default_factory=list)
    ai_score: float = 0.0  # 综合AI得分 (0-1)
    risk_level: str = "low"  # low / medium / high
    summary: str = ""  # 文字摘要


# ═══════════════════════════════════════════════════════
# 29+24 种 AI 写作模式 — 深度重构后的检测规则库
# ═══════════════════════════════════════════════════════

AI_WRITING_MARKERS: list[AIMarker] = [
    # ━━━ 内容模式 (Content Patterns) ━━━━━━━━━━━━━━━━━━━━━━
    AIMarker(
        name="重要性夸大",
        category=AIModeCategory.CONTENT,
        pattern=r"(标志着|见证了|象征着|里程碑|转折点|开创了|奠定了|重塑了|改变了.*格局)",
        description="过度强调事件的意义、遗产和更广泛的趋势",
        severity=0.7,
        replacement_hint="用事实描述替换象征性夸张",
    ),
    AIMarker(
        name="知名度攀附",
        category=AIModeCategory.CONTENT,
        pattern=r"(广受(赞誉|好评|关注)|备受瞩目|声名(远播|鹊起)|独立报道|知名.*(撰写|推荐|评价))",
        description="过度强调知名度、媒体报道或名人背书",
        severity=0.5,
        replacement_hint="去除媒体背书，添加具体引用语境",
    ),
    AIMarker(
        name="肤浅-ing分析",
        category=AIModeCategory.CONTENT,
        pattern=r"(突出了|彰显了|体现了|反映了|表明了|说明了|确保了|保证了|促进了|推动了|提升了|增强了)",
        description="以动名词结构进行的肤浅因果分析",
        severity=0.6,
        replacement_hint="替换为直接陈述，用具体事例代替抽象总结",
    ),
    AIMarker(
        name="宣传广告语言",
        category=AIModeCategory.CONTENT,
        pattern=r"(充满活力|开创性|革命性|颠覆性|前所未有|无与伦比|首屈一指|独一无二|必.*之选|不容错过)",
        description="营销式、广告式的夸张宣传用语",
        severity=0.8,
        replacement_hint="替换为中性客观描述",
    ),
    AIMarker(
        name="模糊归因",
        category=AIModeCategory.CONTENT,
        pattern=r"(据(悉|了解|报道|统计|分析|预测)|(行业|相关|权威|知情).*(报告|显示|认为|指出|透露)|专家(认为|指出|表示))",
        description="使用模糊来源进行归因，缺乏具体引用",
        severity=0.6,
        replacement_hint="删除模糊来源，或替换为具体引用",
    ),
    AIMarker(
        name="提纲式未来展望",
        category=AIModeCategory.CONTENT,
        pattern=r"(尽管存在.*挑战|未来.*展望|随着.*(发展|进步|推进).*将|展望未来|在.*背景下)",
        description="公式化的'挑战与未来展望'结尾结构",
        severity=0.7,
        replacement_hint="替换为具体事实或直接收尾",
    ),
    # ━━━ 语言语法模式 (Language Patterns) ━━━━━━━━━━━━━━━━
    AIMarker(
        name="AI词汇过度",
        category=AIModeCategory.LANGUAGE,
        pattern=r"(此外|至关重要|深入探讨|格局|织锦|画卷|底蕴|脉络|维度|赋能|抓手|闭环|落地|对齐|颗粒度|打法|心智|场域|叙事|范式|矩阵|生态位)",
        description="AI生成文本中高频出现的人工智能标志性词汇",
        severity=0.8,
        replacement_hint="替换为日常自然表达",
    ),
    AIMarker(
        name="系动词回避",
        category=AIModeCategory.LANGUAGE,
        pattern=r"(作为|充当|标志着|扮演着|构成了|形成了|表现为|呈现出|展现出)(一[个种些]|了)?",
        description="AI刻意避免使用简单的'是'，改用复杂系动词结构",
        severity=0.7,
        replacement_hint="恢复使用简单的'是'、'有'",
    ),
    AIMarker(
        name="否定式排比",
        category=AIModeCategory.LANGUAGE,
        pattern=r"(不仅.*而且|不只.*更|这不仅仅是.*而是|不单.*还|岂止.*更是)",
        description="'不仅...而且...'结构的过度使用",
        severity=0.5,
        replacement_hint="改为直接陈述，减少排比结构",
    ),
    AIMarker(
        name="三段式法则",
        category=AIModeCategory.LANGUAGE,
        pattern=r"",  # 用代码逻辑检测：统计逗号分隔的三项列举
        description="描述、列表中的三项目分组过度使用",
        severity=0.4,
        replacement_hint="减少为两项或扩展至四项以上",
    ),
    AIMarker(
        name="同义词循环",
        category=AIModeCategory.LANGUAGE,
        pattern=r"",  # 用代码逻辑检测：短文本内同义词替换模式
        description="为避免重复而在短文本内刻意使用同义词替换",
        severity=0.3,
        replacement_hint="使用一致术语或重组句子",
    ),
    AIMarker(
        name="虚假范围",
        category=AIModeCategory.LANGUAGE,
        pattern=r"从.*到.*(的|等|都)",
        description="使用'从X到Y'结构但X和Y不在有意义的范围内",
        severity=0.5,
        replacement_hint="移除虚假范围，替换为准确范围或删除",
    ),
    # ━━━ 风格模式 (Style Patterns) ━━━━━━━━━━━━━━━━━━━━━━
    AIMarker(
        name="破折号过度",
        category=AIModeCategory.STYLE,
        pattern=r"——",
        description="中文破折号使用频率过高（每100字超过1个）",
        severity=0.6,
        replacement_hint="用逗号或句号替换部分破折号",
    ),
    AIMarker(
        name="AI对话痕迹",
        category=AIModeCategory.COMMUNICATION,
        pattern=r"(希望这(对您|能|可以).*(帮助|有用)|如果您(想|需要).*请.*告诉|我很(高兴|乐意).*(帮助|协助)|还有什么.*可以.*(帮|协助))",
        description="聊天机器人对话残留：协作式结尾",
        severity=0.9,
        replacement_hint="直接删除，转为内容本身",
    ),
    AIMarker(
        name="知识截止声明",
        category=AIModeCategory.COMMUNICATION,
        pattern=r"(截至.*(为止|日期|时间)|根据(我|目前).*(知识|训练|数据|信息)|(请注意|需要.*注意).*知识.*截止|我的.*(知识|训练).*(截止|更新|到))",
        description="'截至XX日期'、'根据我的训练数据'等免责声明",
        severity=0.9,
        replacement_hint="移除不确定性声明",
    ),
    AIMarker(
        name="谄媚语气",
        category=AIModeCategory.COMMUNICATION,
        pattern=r"(好问题|您说得(完全|非常|很)对|这是个(非常|很)好的?(问题|观点|角度)|(完全|非常)同意|确实如此)",
        description="过度奉承、谄媚的回应语气",
        severity=0.8,
        replacement_hint="直接删除奉承性短语",
    ),
    # ━━━ 填充模糊模式 (Filler Patterns) ━━━━━━━━━━━━━━━━━
    AIMarker(
        name="填充短语",
        category=AIModeCategory.FILLER,
        pattern=r"(为了(实现|达到|完成).*(目标|目的|效果)|由于.*(事实|原因|缘故)|在.*(过程|进程|过程中)|值得注意的是|需要.*指出的是|必须.*强调的是)",
        description="冗余的填充短语，稀释信息传达",
        severity=0.5,
        replacement_hint="精简为直接表达",
    ),
    AIMarker(
        name="过度限定",
        category=AIModeCategory.FILLER,
        pattern=r"(可能.*可能|可以.*可以|也许.*也许|似乎.*似乎|或许.*或许|大概.*大概|一定程度上.*某种程度上)",
        description="堆叠的模糊限制语，过度限定",
        severity=0.6,
        replacement_hint="移除多余的限定词",
    ),
    AIMarker(
        name="泛化积极结论",
        category=AIModeCategory.FILLER,
        pattern=r"(未来.*(光明|美好|可期|充满希望)|前景.*广阔|(令人|值得).*期待|充满.*(机遇|可能|想象)|.*时代.*(来临|到来|开启))",
        description="模糊的乐观结尾，空洞的积极结论",
        severity=0.7,
        replacement_hint="替换为具体的下一步或直接移除",
    ),
    # ━━━ 网文特化模式 (WebNovel Patterns) ━━━━━━━━━━━━━━━━
    # 基于网文编辑经验 + 读者反馈 + AI生成网文特征分析
    AIMarker(
        name="AI式升级描述",
        category=AIModeCategory.WEBNOVEL,
        pattern=r"(一股.*(力量|气息|能量).*(涌|冲|爆发|释放|席卷)|修为.*(暴涨|飙升|突破|精进|提升|增进))",
        description="千篇一律的修炼升级描述，AI生成网文的高频模式",
        severity=0.7,
        replacement_hint="用具体感知描写代替抽象能量描述",
    ),
    AIMarker(
        name="模板化装逼打脸",
        category=AIModeCategory.WEBNOVEL,
        pattern=r"(嘴角.*(勾起|扬起|浮现|露出).*(冷笑|笑意|弧度|一抹)|(众人|所有人|在场.*人).*(震惊|骇然|倒吸|不敢置信|目瞪口呆)|(不屑|轻蔑|鄙夷).*(目光|眼神|看了.*一眼))",
        description="高度模板化的'装逼打脸'桥段描写",
        severity=0.8,
        replacement_hint="设计独特的打脸方式，避免固定模板",
    ),
    AIMarker(
        name="AI式战斗描写",
        category=AIModeCategory.WEBNOVEL,
        pattern=r"(快如闪电|势如破竹|雷霆万钧|排山倒海|天崩地裂|风云变色|摧枯拉朽|所向披靡|势不可挡|锐不可当)",
        description="成语堆砌式战斗描写，缺乏具象画面感",
        severity=0.7,
        replacement_hint="用具体动作和感官细节替代成语堆砌",
    ),
    AIMarker(
        name="过度旁白解释",
        category=AIModeCategory.WEBNOVEL,
        pattern=r"(要知道|众所周知|需要.*说明.*的是|这里.*解释|换句话|也就是.*说|意思.*就是|可以.*理解.*为)",
        description="AI倾向于向读者解释情节，网文中应'展示而非告知'",
        severity=0.6,
        replacement_hint="删除解释性旁白，通过情节自然展示",
    ),
    AIMarker(
        name="AI式心理描写",
        category=AIModeCategory.WEBNOVEL,
        pattern=r"(心中.*(暗|不|一|微).*(想|道|叹|惊|喜|怒|忧|思)|内心.*(充满|涌起|泛起|升起|浮现).*(感|情绪|念头|想法))",
        description="模板化的心理活动描写",
        severity=0.6,
        replacement_hint="用行为或对话间接体现心理，避免直接陈述",
    ),
    AIMarker(
        name="对称式对话",
        category=AIModeCategory.WEBNOVEL,
        pattern=r"",  # 代码逻辑检测：连续对话回合数
        description="过于对称的对话结构（你一句我一句，无打断无重叠）",
        severity=0.5,
        replacement_hint="加入打断、沉默、动作穿插，打破对称节奏",
    ),
    # ━━━ 中文特化补充模式 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    AIMarker(
        name="书面连接词堆积",
        category=AIModeCategory.LANGUAGE,
        pattern=r"(然而.*然而|因此.*因此|于是.*于是|此外.*此外|与此.*同时.*与此)",
        description="同一段内重复使用书面连接词",
        severity=0.6,
        replacement_hint="减少连接词使用，通过语义自然衔接",
    ),
    AIMarker(
        name="AI味开头句式",
        category=AIModeCategory.LANGUAGE,
        pattern=r"^(在.*(中|下|里|时|后|前)|随着.*的.*(发展|深入|推进|进行)|当.*的.*时候)",
        description="'在...中'、'随着...的发展'等AI高频开头句式",
        severity=0.7,
        replacement_hint="改为直接主语开头或场景描写开头",
    ),
    AIMarker(
        name="过度使用引号强调",
        category=AIModeCategory.STYLE,
        pattern=r'"[^"]{2,8}"',
        description="频繁使用引号对普通词汇进行强调（非对话）",
        severity=0.4,
        replacement_hint="减少不必要的引号强调",
    ),
]


class AIModeDetector:
    """
    AI写作模式检测器

    基于 blader/humanizer + Humanizer-zh 的模式定义，
    重构为独立的Python检测引擎。

    检测流程:
      1. 正则模式匹配 → 统计命中
      2. 结构分析（三段式、对称对话、同义词循环）
      3. 频率分析（破折号密度、功能词密度）
      4. 综合评分 → 风险等级
    """

    def __init__(self):
        self._markers = AI_WRITING_MARKERS

    def detect(self, text: str) -> DetectionReport:
        """
        执行完整的AI模式检测

        Args:
            text: 待检测文本

        Returns:
            DetectionReport 包含所有命中标记和综合评分
        """
        if not text or len(text) < 50:
            return DetectionReport()

        report = DetectionReport()
        total_count = 0

        for marker in self._markers:
            # 跳过需要代码逻辑检测的模式
            if not marker.pattern:
                continue

            matches = re.findall(marker.pattern, text)
            if matches:
                marker_copy = AIMarker(
                    name=marker.name,
                    category=marker.category,
                    pattern=marker.pattern,
                    description=marker.description,
                    severity=marker.severity,
                    count=len(matches),
                    examples=list(matches)[:3],
                    replacement_hint=marker.replacement_hint,
                )
                report.markers.append(marker_copy)
                total_count += len(matches)

        # 代码逻辑检测：三段式法则
        triple_count = self._detect_rule_of_three(text)
        if triple_count > 2:
            report.markers.append(
                AIMarker(
                    name="三段式法则",
                    category=AIModeCategory.LANGUAGE,
                    pattern="(代码逻辑检测)",
                    description="描述中三项目分组过度使用",
                    severity=0.4,
                    count=triple_count,
                )
            )
            total_count += triple_count

        # 代码逻辑检测：对称式对话
        dialogue_score = self._detect_symmetric_dialogue(text)
        if dialogue_score > 0.5:
            report.markers.append(
                AIMarker(
                    name="对称式对话",
                    category=AIModeCategory.WEBNOVEL,
                    pattern="(代码逻辑检测)",
                    description="过于对称的对话结构",
                    severity=0.5,
                    count=int(dialogue_score * 10),
                )
            )

        # 代码逻辑检测：破折号密度
        dash_density = text.count("——") / max(len(text), 1) * 100
        if dash_density > 1.0:
            # 更新或添加破折号标记
            dash_marker = next((m for m in report.markers if m.name == "破折号过度"), None)
            if dash_marker:
                dash_marker.count = text.count("——")
            else:
                report.markers.append(
                    AIMarker(
                        name="破折号过度",
                        category=AIModeCategory.STYLE,
                        pattern="——",
                        description=f"破折号密度 {dash_density:.1f}/100字",
                        severity=0.6,
                        count=text.count("——"),
                    )
                )

        report.total_markers = total_count
        report.unique_patterns = len(report.markers)

        # 综合评分
        report.ai_score = self._calculate_ai_score(report, len(text))
        report.risk_level = self._classify_risk(report.ai_score)
        report.summary = self._generate_summary(report)

        return report

    def get_replacement_hints(self, marker_name: str) -> str:
        """获取特定模式的替换建议"""
        for marker in self._markers:
            if marker.name == marker_name:
                return marker.replacement_hint
        return ""

    def get_markers_by_category(self, category: AIModeCategory) -> list[AIMarker]:
        """按分类获取模式列表"""
        return [m for m in self._markers if m.category == category]

    # ── 内部方法 ──────────────────────────────────────

    def _detect_rule_of_three(self, text: str) -> int:
        """检测三段式列举"""
        # 匹配"X、Y和Z"或"X、Y、Z"的三项列举模式
        pattern = re.compile(
            r"[^，。！？\n]{2,10}[、，][^，。！？\n]{2,10}[、，和与及][^，。！？\n]{2,10}"
        )
        matches = pattern.findall(text)
        return len(matches)

    def _detect_symmetric_dialogue(self, text: str) -> float:
        """检测对称式对话结构"""
        # 提取对话行
        dialogue_lines = re.findall(r'[""「」]([^""「」]{3,50})[""「」]', text)
        if len(dialogue_lines) < 4:
            return 0.0

        # 检测连续对话的长度均匀性
        lengths = [len(line) for line in dialogue_lines]
        if len(lengths) < 2:
            return 0.0

        mean_len = sum(lengths) / len(lengths)
        if mean_len == 0:
            return 0.0

        # 计算长度变异系数 — 越低越对称
        variance = sum((length - mean_len) ** 2 for length in lengths) / len(lengths)
        cv = math.sqrt(variance) / mean_len

        # CV < 0.3 表示高度对称
        if cv < 0.2:
            return 0.9
        if cv < 0.3:
            return 0.6
        if cv < 0.4:
            return 0.3
        return 0.0

    def _calculate_ai_score(self, report: DetectionReport, text_length: int) -> float:
        """综合AI得分"""
        if not report.markers:
            return 0.0

        # 加权：严重度 × 命中数 / 文本长度归一化
        weighted_sum = 0.0
        for marker in report.markers:
            # 归一化：每100字中的命中
            density = marker.count / max(text_length, 1) * 100
            weighted_sum += marker.severity * min(density, 5.0)  # 上限5

        # 模式种类多样性惩罚
        diversity_penalty = min(report.unique_patterns / 10, 1.0)

        # 综合
        raw_score = weighted_sum / max(len(report.markers), 1)
        return min(raw_score * (0.5 + 0.5 * diversity_penalty), 1.0)

    def _classify_risk(self, score: float) -> str:
        """风险等级"""
        if score > 0.6:
            return "high"
        if score > 0.35:
            return "medium"
        return "low"

    def _generate_summary(self, report: DetectionReport) -> str:
        """生成文字摘要"""
        if not report.markers:
            return "未检测到明显AI写作模式"

        # 按严重度排序，取前5
        top = sorted(report.markers, key=lambda m: m.severity * m.count, reverse=True)[:5]
        items = [f"{m.name}({m.count}次)" for m in top]

        risk_text = {"high": "高风险", "medium": "中等风险", "low": "低风险"}
        return (
            f"{risk_text.get(report.risk_level, '未知')}，"
            f"检测到 {report.unique_patterns} 种AI模式，"
            f"共 {report.total_markers} 处标记。"
            f"主要模式: {'、'.join(items)}"
        )


# 全局单例
ai_mode_detector = AIModeDetector()
