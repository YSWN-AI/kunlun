"""
文风指纹系统 — 统计指纹提取 + 风格注入

对应 inkos style analyze / style import 命令

核心流程:
  1. StyleAnalyzer.analyze(text) → StyleFingerprint (统计指纹)
  2. StyleAnalyzer.generate_style_guide(fp) → LLM 生成风格指南
  3. StyleInjector.build_style_prompt(fp) → 注入到 Writer prompt

使用方式:
    from kunlun.style.fingerprint import style_analyzer, style_injector

    # 分析参考文本
    fp = style_analyzer.analyze(reference_text, name="名家风格")
    await style_analyzer.generate_style_guide(fp)

    # 保存/加载
    style_analyzer.save_fingerprint(fp, "my_book")
    fp_loaded = style_analyzer.load_fingerprint("my_book")

    # 注入到创作
    style_prompt = style_injector.build_style_prompt(fp)
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field

from loguru import logger

from kunlun.config import settings

# ── 常用字表（简化版500字，用于生僻词比例计算）──
_COMMON_CHARS = set(
    "的一是了我不人在他有这个上们来到时大地为子中你说生国年着就那和要她出也得里后自以会家可下而过天去能对小多然于心学么之都好看起发当没成只如事把还用第样道想作种开美总从无情己面最女但现前些所同日手又行意动方期它头经长儿回位分爱老因很给名法间斯知世什两次使身者被高已亲其进此话常与活正感见明问力理尔点文几定本公特做外孩相西果走将月十实向声车全信重三机工物气每并别真打太新比才便夫再书部水像眼等体却加电主界门利海受听表德少克代员许稍口由死安写性马光白或住难望教命花结乐色更拉东神记处让母父应直字场平报友关放至张认接告入笑内英军候民岁往何度山觉路带万男边风解叫任金快原吃妈变通师立象数四失满战远格士音轻目条呢病始达深完今提求清王化空业思切怎非找片罗钱紶吗语元喜曾离飞科言干网早吧论功令圆柱六"
)

# ── 动词关键词表（近似，不依赖jieba词性标注）──
_VERB_KEYWORDS = set(
    "看听说读写走跑跳飞游泳吃喝睡坐站躺拿放推拉拉打踢抱握抓扔捡举放提扛背搬运买卖送收借还租雇雇佣开关闭锁启动停止开始结束继续暂停继续进行完成实现达到获得得到失去丢失寻找发现出现消失存在生存死亡灭亡生长发展变化改变转变转化成为变成好像似乎仿佛犹如如同宛如好似像如同是在有没无存在拥有具有缺乏缺少需要想要希望愿望计划打算准备决定选择挑选判断认为以为觉得感到感觉意识体会体验经历经受承受承担负责担任管理治理统治控制操纵操作使用运用应用利用采用采取执行实行实施贯彻落实推行推广提倡倡导引导指导指示命令要求请求请示汇报报告通知通告公告宣告宣布发布发表出版发行播放演出表演展示展览显示显现呈现出现展现体现表示表达表明标明标注标记记录记载登记注册报名报到到达抵达离开出发起程起程动身返回回来回去出去进来进去上下升降起落涨跌增减多少大小长短高低宽窄厚薄粗细轻重快慢远近深浅浓淡强弱软硬真假好坏善恶美丑新旧老幼生死"
)

# ── 形容词关键词表（近似）──
_ADJECTIVE_KEYWORDS = set(
    "大小多少长短高低宽窄厚薄粗细轻重快慢远近深浅浓淡强弱软硬真假好坏善恶美丑新旧老幼冷热温凉暖寒炎湿干燥潮湿明亮黑暗昏暗晴朗阴沉蔚蓝碧绿金黄银白银灰漆黑雪白白皙红润苍白清秀英俊美丽漂亮丑陋丑陋潇洒帅气可爱可憎可恨可恶讨厌喜欢高兴快乐悲伤痛苦愤怒恐惧惊慌害怕担忧忧虑紧张放松轻松沉重轻盈笨重灵巧笨拙聪明愚蠢机智迟钝勇敢懦弱坚强软弱脆弱顽强固执倔强温柔粗暴和蔼严厉慈祥凶恶善良邪恶纯洁肮脏高尚卑鄙伟大渺小平凡普通特别特殊一般独特奇异奇怪平常寻常异常非常极其十分非常最更较太挺好很非常极其十分最更较太挺真好极了太棒了太妙了太精彩了太出色了太优秀了太杰出了太卓越了太辉煌了太灿烂了太绚丽了太华丽了太华美了太富丽了太堂皇了太壮观了太雄伟了太宏伟了太宏大了太巨大了太庞大了太浩大了太浩瀚了太辽阔了太广阔了太宽广了太宽敞了太宽大了太宽松了太松弛了太松懈了太松散了太疏松了太稀松了太稀疏了太稀少了太稀有了太罕见了太少见了太稀奇了太珍奇了太珍贵了太宝贵了太贵重了太昂贵了太奢华了太奢侈了太奢靡了太浪费了太挥霍了太糟蹋了太破坏了太损坏了太毁坏了太摧毁了太毁灭了太消灭了太消除了太清除了太扫除了太扫除了太排除了太排斥了太拒绝了太谢绝了太推辞了太推脱了太推卸了太逃避了太躲避了太回避了太躲闪了太闪开了太躲开了太避开了太让开了太让路了太让位了太让座了太让贤了太谦让了太礼让了太恭敬了太尊敬了太尊重了太敬重了太敬爱了太爱戴了太拥护了太支持了太赞了太赞了"
)

# ── AI套话列表（用于ai_taste_score计算）──
_AI_CLICHES = [
    "突然", "仿佛", "似乎", "好像", "总的来说", "值得一提的是",
    "不仅如此", "与此同时", "综上所述", "由此可见", "显而易见",
    "毫无疑问", "不可否认", "众所周知", "不言而喻", "毋庸置疑",
    "总而言之", "概括来说", "简而言之", "换句话说", "也就是说",
    "正是因为", "正是由于", "正是这个", "正是这种", "正是这样",
    "不禁", "不由得", "忍不住", "情不自禁", "不由自主",
    "心中一紧", "心中一动", "心中一凛", "心中一惊", "心中一喜",
    "眼中闪过", "眼中露出", "眼中浮现", "眼中泛起", "眼中掠过",
    "嘴角微微", "嘴角勾起", "嘴角上扬", "嘴角露出", "嘴角浮现",
    "脸上露出", "脸上浮现", "脸上泛起", "脸上闪过", "脸上掠过",
]

# ── 比喻词列表 ──
_METAPHOR_WORDS = ["宛如", "仿佛", "犹如", "如同", "好似", "好像", "宛若", "犹若", "恍若"]

# ── 夸张词列表 ──
_EXAGGERATION_WORDS = [
    "万丈", "滔天", "无尽", "永恒", "不朽", "灭世", "毁天", "灭地",
    "惊天", "动地", "震天", "撼地", "吞天", "噬地", "开天", "辟地",
    "破碎", "崩裂", "崩塌", "毁灭", "湮灭", "消散", "灰飞", "烟灭",
]

# ── 心理描写触发词 ──
_PSYCH_WORDS = ["心想", "暗道", "觉得", "感到", "感觉", "认为", "以为", "暗自", "心中", "心里", "心底", "内心"]


@dataclass
class StyleFingerprint:
    """文风统计指纹

    包含全文的统计特征,用于:
    - 风格分析: 句长/词频/节奏/对话等维度的量化描述
    - 风格注入: 将特征转化为创作提示词
    - 风格对比: 两个指纹之间的相似度计算

    字段总数: 31（原有12 + 新增19）
    """

    name: str = ""
    source: str = ""  # 参考文本来源/作者

    # ── 句长分布 ──
    avg_sentence_length: float = 0.0
    sentence_length_std: float = 0.0
    sentence_length_histogram: list[int] = field(default_factory=lambda: [0] * 10)
    # 桶: 0-10, 10-20, 20-30, ..., 80-90, 90-100, 100+

    # ── 词频特征 ──
    top_words: list[tuple[str, int]] = field(default_factory=list)  # top-20词
    word_diversity: float = 0.0  # 独特词数 / 总词数

    # ── 节奏模式 ──
    paragraph_length_pattern: list[int] = field(default_factory=list)  # 连续段落长度序列
    avg_paragraph_length: float = 0.0
    paragraph_length_cv: float = 0.0  # 变异系数

    # ── 对话特征 ──
    dialogue_ratio: float = 0.0  # 对话字数 / 总字数
    avg_dialogue_length: float = 0.0  # 平均每句对话长度

    # ── 标点偏好 ──
    punctuation_distribution: dict = field(default_factory=dict)

    # ── LLM生成 ──
    style_guide: str = ""  # 由LLM生成的风格描述

    # ══════════════════════════════════════════════════
    # ── 新增字段：句法特征（4项）──
    # ══════════════════════════════════════════════════
    short_sentence_ratio: float = 0.0  # 短句比例（≤15字）
    long_sentence_ratio: float = 0.0  # 长句比例（≥40字）
    exclamation_ratio: float = 0.0  # 感叹号/句号比
    question_ratio: float = 0.0  # 问号/句号比

    # ══════════════════════════════════════════════════
    # ── 新增字段：词汇特征（5项）──
    # ══════════════════════════════════════════════════
    rare_word_ratio: float = 0.0  # 生僻词比例（非常用字占比）
    avg_word_length: float = 0.0  # 平均词长
    verb_density: float = 0.0  # 动词密度（/千字）
    adjective_density: float = 0.0  # 形容词密度（/千字）
    signature_words: list[str] = field(default_factory=list)  # 标志性词top20

    # ══════════════════════════════════════════════════
    # ── 新增字段：修辞特征（4项）──
    # ══════════════════════════════════════════════════
    metaphor_per_1k: float = 0.0  # 每千字比喻次数
    exaggeration_per_1k: float = 0.0  # 每千字夸张次数
    four_character_per_1k: float = 0.0  # 每千字四字格成语次数
    parallelism_per_1k: float = 0.0  # 每千字排比次数

    # ══════════════════════════════════════════════════
    # ── 新增字段：叙事特征（4项）──
    # ══════════════════════════════════════════════════
    action_desc_ratio: float = 0.0  # 动作描写占比
    env_desc_ratio: float = 0.0  # 环境描写占比
    psych_desc_ratio: float = 0.0  # 心理描写占比
    single_sentence_para_ratio: float = 0.0  # 单句成段比例

    # ══════════════════════════════════════════════════
    # ── 新增字段：综合（2项）──
    # ══════════════════════════════════════════════════
    feature_vector: list[float] = field(default_factory=list)  # 归一化特征向量
    ai_taste_score: float = 0.0  # AI味指数（0-1）

    # ── 方法 ──

    def to_prompt(self) -> str:
        """将指纹转换为Prompt描述（句法+词汇+修辞+叙事的量化约束）

        Returns:
            风格约束描述字符串
        """
        parts = ["【文风量化约束】"]

        # 句法
        if self.avg_sentence_length > 0:
            parts.append(
                f"- 句法: 平均句长{self.avg_sentence_length:.1f}字，"
                f"短句占比{self.short_sentence_ratio:.0%}，"
                f"长句占比{self.long_sentence_ratio:.0%}"
            )
            if self.exclamation_ratio > 0:
                parts.append(f"- 语气: 感叹号/句号比{self.exclamation_ratio:.2f}，问号/句号比{self.question_ratio:.2f}")

        # 词汇
        if self.word_diversity > 0:
            parts.append(
                f"- 词汇: 多样性{self.word_diversity:.2f}，"
                f"平均词长{self.avg_word_length:.1f}，"
                f"生僻词占比{self.rare_word_ratio:.1%}"
            )
            parts.append(f"- 词密度: 动词{self.verb_density:.1f}/千字，形容词{self.adjective_density:.1f}/千字")
            if self.signature_words:
                parts.append(f"- 标志性词: {', '.join(self.signature_words[:10])}")

        # 修辞
        if self.metaphor_per_1k > 0 or self.four_character_per_1k > 0:
            parts.append(
                f"- 修辞: 比喻{self.metaphor_per_1k:.1f}次/千字，"
                f"夸张{self.exaggeration_per_1k:.1f}次/千字，"
                f"四字格{self.four_character_per_1k:.1f}次/千字，"
                f"排比{self.parallelism_per_1k:.1f}次/千字"
            )

        # 叙事
        if self.action_desc_ratio > 0 or self.psych_desc_ratio > 0:
            parts.append(
                f"- 叙事: 动作描写{self.action_desc_ratio:.0%}，"
                f"环境描写{self.env_desc_ratio:.0%}，"
                f"心理描写{self.psych_desc_ratio:.0%}，"
                f"单句成段{self.single_sentence_para_ratio:.0%}"
            )

        # 对话
        if self.dialogue_ratio > 0:
            parts.append(f"- 对话: 占比{self.dialogue_ratio:.0%}，平均长度{self.avg_dialogue_length:.1f}字")

        # AI味
        if self.ai_taste_score > 0:
            parts.append(f"- AI味指数: {self.ai_taste_score:.2f}（越低越像人类写作）")

        return "\n".join(parts)

    def cosine_similarity(self, other: StyleFingerprint) -> float:
        """基于feature_vector的余弦相似度

        Args:
            other: 另一个指纹

        Returns:
            相似度（0.0 ~ 1.0），向量为空时返回0.0
        """
        v1 = self.feature_vector
        v2 = other.feature_vector
        if not v1 or not v2:
            return 0.0
        # 对齐长度
        min_len = min(len(v1), len(v2))
        v1 = v1[:min_len]
        v2 = v2[:min_len]
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return round(dot / (norm1 * norm2), 4)


class StyleAnalyzer:
    """文风分析器 — 从参考文本提取统计指纹

    分析维度:
    1. 句长分布 (平均、标准差、直方图)
    2. 词汇特征 (高频词、词汇多样性)
    3. 段落节奏 (平均长度、变异系数、序列模式)
    4. 对话特征 (占比、平均长度)
    5. 标点偏好 (逗号、句号、感叹号等的使用频率)
    6. 句法特征 (短句/长句比例、感叹/问号比)
    7. 词汇深度 (生僻词、词长、动词/形容词密度、标志性词)
    8. 修辞特征 (比喻、夸张、四字格、排比)
    9. 叙事特征 (动作/环境/心理描写占比、单句成段)
    10. 综合 (特征向量、AI味指数)
    """

    def analyze(self, text: str, name: str = "reference") -> StyleFingerprint:
        """分析文本,提取统计指纹

        Args:
            text: 参考文本
            name: 指纹名称

        Returns:
            StyleFingerprint 对象
        """
        fp = StyleFingerprint(name=name, source=text[:100])

        # ── 1. 句长分析 ──
        sentences = re.split(r"[。！？.!?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            lengths = [len(s) for s in sentences]
            fp.avg_sentence_length = sum(lengths) / len(lengths)
            if len(lengths) > 1:
                variance = sum((v - fp.avg_sentence_length) ** 2 for v in lengths) / len(lengths)
                fp.sentence_length_std = math.sqrt(variance)
            else:
                fp.sentence_length_std = 0.0

            # 直方图: 每10字一个桶
            for v in lengths:
                bucket = min(v // 10, 9)
                fp.sentence_length_histogram[bucket] += 1

            # ── 新增：短句/长句比例 ──
            total_s = len(lengths)
            fp.short_sentence_ratio = sum(1 for v in lengths if v <= 15) / total_s
            fp.long_sentence_ratio = sum(1 for v in lengths if v >= 40) / total_s

        # ── 2. 词汇特征 ──
        # 多字词（用于 top_words 和多样性计算）
        multi_words = re.findall(r"[一-鿿]{2,}", text)
        # 单字词（补充）
        single_words = re.findall(r"[一-鿿]", text)
        all_words = multi_words + single_words
        if all_words:
            word_counts = Counter(all_words)
            fp.top_words = word_counts.most_common(20)
            fp.word_diversity = len(word_counts) / max(len(all_words), 1)

            # ── 新增：平均词长 ──
            fp.avg_word_length = sum(len(w) for w in all_words) / len(all_words)

            # ── 新增：生僻词比例（非常用字占比，基于单字）──
            if single_words:
                rare_count = sum(1 for c in single_words if c not in _COMMON_CHARS)
                fp.rare_word_ratio = rare_count / len(single_words)

            # ── 新增：动词/形容词密度（/千字）──
            text_len_1k = max(len(text) / 1000.0, 0.001)
            verb_count = sum(1 for w in multi_words if w in _VERB_KEYWORDS)
            adj_count = sum(1 for w in multi_words if w in _ADJECTIVE_KEYWORDS)
            fp.verb_density = verb_count / text_len_1k
            fp.adjective_density = adj_count / text_len_1k

            # ── 新增：标志性词top20（高频且非通用词）──
            # 过滤掉单字通用词和极高频功能词
            stop_chars = set("的一是了我不人在他有这个上们来到时大地为子中你说生国年着就那和要她出也得里后自以会家可下而过天去能对小多然于心学么之都好看起发当没成只如事把还用第样道想作种开")
            signature = [
                w for w, c in word_counts.most_common(100)
                if len(w) >= 2 and w not in stop_chars and c >= 2
            ]
            fp.signature_words = signature[:20]

        # ── 3. 段落节奏 ──
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            para_lens = [len(p) for p in paragraphs]
            fp.paragraph_length_pattern = para_lens[:20]  # 前20段
            fp.avg_paragraph_length = sum(para_lens) / len(para_lens)
            if len(para_lens) > 1 and fp.avg_paragraph_length > 0:
                variance = sum((v - fp.avg_paragraph_length) ** 2 for v in para_lens) / len(
                    para_lens
                )
                fp.paragraph_length_cv = math.sqrt(variance) / fp.avg_paragraph_length
            else:
                fp.paragraph_length_cv = 0.0

            # ── 新增：单句成段比例 ──
            single_para_count = 0
            for p in paragraphs:
                p_sentences = re.split(r"[。！？.!?]", p)
                p_sentences = [s.strip() for s in p_sentences if s.strip()]
                if len(p_sentences) <= 1:
                    single_para_count += 1
            fp.single_sentence_para_ratio = single_para_count / len(paragraphs)

        # ── 4. 对话特征 ──
        dialogues = re.findall(r'[「「""]([^」」""]+)[」」""]', text)
        all_text_len = max(len(text), 1)
        dialogue_chars = sum(len(d) for d in dialogues)
        fp.dialogue_ratio = dialogue_chars / all_text_len
        fp.avg_dialogue_length = dialogue_chars / len(dialogues) if dialogues else 0

        # ── 5. 标点分布 ──
        puncts = [
            ",",
            "，",
            "。",
            "！",
            "？",
            "、",
            "…",
            "；",
            "：",
            '"',
            "「",
            "」",
            "——",
            "《",
            "》",
        ]
        fp.punctuation_distribution = {p: text.count(p) for p in puncts}

        # ── 新增：感叹号/问号与句号比 ──
        period_count = fp.punctuation_distribution.get("。", 0) + fp.punctuation_distribution.get(".", 0)
        exclam_count = fp.punctuation_distribution.get("！", 0) + fp.punctuation_distribution.get("!", 0)
        question_count = fp.punctuation_distribution.get("？", 0) + fp.punctuation_distribution.get("?", 0)
        if period_count > 0:
            fp.exclamation_ratio = exclam_count / period_count
            fp.question_ratio = question_count / period_count

        # ── 新增：修辞特征 ──
        text_len_1k = max(len(text) / 1000.0, 0.001)

        # 比喻
        metaphor_count = sum(text.count(w) for w in _METAPHOR_WORDS)
        fp.metaphor_per_1k = metaphor_count / text_len_1k

        # 夸张
        exaggeration_count = sum(text.count(w) for w in _EXAGGERATION_WORDS)
        fp.exaggeration_per_1k = exaggeration_count / text_len_1k

        # 四字格成语（匹配连续4个汉字的片段，近似）
        four_char_segments = re.findall(r"[一-鿿]{4}", text)
        fp.four_character_per_1k = len(four_char_segments) / text_len_1k

        # 排比（连续3个以上相似句式：匹配连续的"，...，...，"或"；...；...；"模式）
        parallelism_count = 0
        # 检测连续3个以上逗号分隔的相似长度片段
        comma_segments = re.split(r"[，,]", text)
        run_length = 0
        for seg in comma_segments:
            seg = seg.strip()
            if 3 <= len(seg) <= 20:
                run_length += 1
                if run_length >= 3:
                    parallelism_count += 1
            else:
                run_length = 0
        fp.parallelism_per_1k = parallelism_count / text_len_1k

        # ── 新增：叙事特征（动作/环境/心理描写占比）──
        if paragraphs:
            action_chars = 0
            env_chars = 0
            psych_chars = 0
            # 环境描写触发词
            env_words = ["天空", "大地", "山川", "河流", "森林", "草原", "沙漠", "海洋",
                         "山峰", "山谷", "悬崖", "峭壁", "瀑布", "湖泊", "月亮", "太阳",
                         "星辰", "云雾", "风雨", "雷电", "雪花", "阳光", "月光", "星光",
                         "景色", "风景", "景象", "景物", "氛围", "气氛", "环境", "四周",
                         "周围", "远处", "近处", "前方", "后方", "上方", "下方"]
            for p in paragraphs:
                p_len = len(p)
                # 动作描写：动词密集段
                p_verbs = sum(1 for w in re.findall(r"[一-鿿]{2,}", p) if w in _VERB_KEYWORDS)
                if p_len > 0 and p_verbs / max(p_len / 20.0, 1) >= 1:
                    action_chars += p_len
                # 环境描写
                if any(w in p for w in env_words):
                    env_chars += p_len
                # 心理描写
                if any(w in p for w in _PSYCH_WORDS):
                    psych_chars += p_len

            total_chars = sum(len(p) for p in paragraphs)
            if total_chars > 0:
                fp.action_desc_ratio = action_chars / total_chars
                fp.env_desc_ratio = env_chars / total_chars
                fp.psych_desc_ratio = psych_chars / total_chars

        # ── 新增：构建特征向量 ──
        fp.feature_vector = self._build_feature_vector(fp)

        # ── 新增：计算AI味指数 ──
        fp.ai_taste_score = self._calc_ai_taste(text, fp)

        logger.info(
            f'[StyleAnalyzer] 指纹"{name}"提取完成: '
            f"句长{int(fp.avg_sentence_length)}字, "
            f"段长{int(fp.avg_paragraph_length)}字, "
            f"对话{fp.dialogue_ratio:.0%}, "
            f"词多样性{fp.word_diversity:.2f}, "
            f"AI味{fp.ai_taste_score:.2f}"
        )
        return fp

    def analyze_and_vectorize(self, text: str, name: str = "reference") -> StyleFingerprint:
        """分析文本并确保feature_vector完整

        等价于analyze()，但显式保证特征向量已构建。

        Args:
            text: 参考文本
            name: 指纹名称

        Returns:
            StyleFingerprint 对象（feature_vector已填充）
        """
        fp = self.analyze(text, name=name)
        if not fp.feature_vector:
            fp.feature_vector = self._build_feature_vector(fp)
        return fp

    def _build_feature_vector(self, fp: StyleFingerprint) -> list[float]:
        """构建归一化特征向量（24维）

        将所有数值型字段归一化到[0,1]，组成向量用于余弦相似度计算。

        Args:
            fp: 风格指纹

        Returns:
            归一化特征向量
        """
        vector = [
            # 句长（归一化到[0,1]）
            min(fp.avg_sentence_length / 100.0, 1.0),
            min(fp.sentence_length_std / 50.0, 1.0),
            # 词汇
            min(fp.word_diversity, 1.0),
            # 段落
            min(fp.avg_paragraph_length / 200.0, 1.0),
            min(fp.paragraph_length_cv, 1.0),
            # 对话
            min(fp.dialogue_ratio, 1.0),
            min(fp.avg_dialogue_length / 100.0, 1.0),
            # 句法（新增）
            min(fp.short_sentence_ratio, 1.0),
            min(fp.long_sentence_ratio, 1.0),
            min(fp.exclamation_ratio, 1.0),
            min(fp.question_ratio, 1.0),
            # 词汇深度（新增）
            min(fp.rare_word_ratio, 1.0),
            min(fp.avg_word_length / 4.0, 1.0),
            min(fp.verb_density / 50.0, 1.0),
            min(fp.adjective_density / 50.0, 1.0),
            # 修辞（新增）
            min(fp.metaphor_per_1k / 5.0, 1.0),
            min(fp.exaggeration_per_1k / 5.0, 1.0),
            min(fp.four_character_per_1k / 10.0, 1.0),
            min(fp.parallelism_per_1k / 5.0, 1.0),
            # 叙事（新增）
            min(fp.action_desc_ratio, 1.0),
            min(fp.env_desc_ratio, 1.0),
            min(fp.psych_desc_ratio, 1.0),
            min(fp.single_sentence_para_ratio, 1.0),
        ]
        return vector

    def _calc_ai_taste(self, text: str, fp: StyleFingerprint) -> float:
        """计算AI味指数（0-1，越高越像AI写的）

        公式: 套话密度 * 0.4 + 句式均匀度(1-CV) * 0.3 + 段落均匀度(1-para_cv) * 0.3

        Args:
            text: 原始文本
            fp: 风格指纹

        Returns:
            AI味指数（0-1）
        """
        # 套话密度
        text_len = max(len(text), 1)
        cliche_count = sum(text.count(w) for w in _AI_CLICHES)
        cliche_density = min(1.0, cliche_count / max(text_len / 100.0, 1) * 0.5)

        # 句式均匀度（1 - 句长变异系数）
        if fp.avg_sentence_length > 0 and fp.sentence_length_std > 0:
            sentence_cv = fp.sentence_length_std / fp.avg_sentence_length
        else:
            sentence_cv = 0.0
        sentence_uniformity = max(0.0, 1.0 - min(sentence_cv, 1.0))

        # 段落均匀度（1 - 段落长度变异系数）
        paragraph_uniformity = max(0.0, 1.0 - min(fp.paragraph_length_cv, 1.0))

        ai_score = cliche_density * 0.4 + sentence_uniformity * 0.3 + paragraph_uniformity * 0.3
        return round(min(1.0, max(0.0, ai_score)), 4)

    async def generate_style_guide(self, fp: StyleFingerprint) -> str:
        """通过LLM生成风格指南

        将统计指纹发送给LLM,生成人类可读的写作风格描述。
        这个描述会被注入到Writer的prompt中,指导风格模仿。

        使用 gacha_engine.generate() 调用真实模型,不使用mock数据。

        Args:
            fp: 统计指纹

        Returns:
            风格指南文本
        """
        from kunlun.gacha.engine import gacha_engine

        stats = f"""文风统计:
- 平均句长: {fp.avg_sentence_length:.1f}字 (标准差: {fp.sentence_length_std:.1f})
- 句长直方图(10字桶): {fp.sentence_length_histogram}
- 平均段长: {fp.avg_paragraph_length:.1f}字 (变异系数: {fp.paragraph_length_cv:.2f})
- 对话占比: {fp.dialogue_ratio:.1%}
- 平均对话长度: {fp.avg_dialogue_length:.1f}字
- 词汇多样性: {fp.word_diversity:.2%}
- 高频词Top10: {dict(fp.top_words[:10])}
- 标点分布: {fp.punctuation_distribution}
- 短句比例: {fp.short_sentence_ratio:.1%}, 长句比例: {fp.long_sentence_ratio:.1%}
- 生僻词比例: {fp.rare_word_ratio:.1%}
- 比喻: {fp.metaphor_per_1k:.1f}/千字, 四字格: {fp.four_character_per_1k:.1f}/千字
- 动作描写: {fp.action_desc_ratio:.1%}, 心理描写: {fp.psych_desc_ratio:.1%}
- AI味指数: {fp.ai_taste_score:.2f}
"""

        prompt = f"""你是文风分析师。根据以下统计指纹,生成一份简洁的写作风格指南。

{stats}

请输出:
1. 风格定位（1句话概括）
2. 句式特点（2-3条建议，基于句长/标准差/直方图）
3. 段落节奏建议（基于变异系数）
4. 词汇倾向（基于高频词）
5. 对话风格（基于对话占比/平均长度）
6. 去AI味要点（对抗AI生成倾向的具体建议）

格式：直接输出，每条一行，总字数不超过200字。"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            fp.style_guide = result.get("best_text", "")
            if not fp.style_guide:
                logger.warning("[StyleAnalyzer] LLM风格指南生成返回空")
            else:
                logger.info(f"[StyleAnalyzer] 风格指南生成完成: {fp.style_guide[:50]}...")
            return fp.style_guide
        except Exception as e:
            logger.error(f"[StyleAnalyzer] LLM风格指南生成失败: {e}")
            # 回退：基于统计数据生成简单的规则指南
            fp.style_guide = self._fallback_style_guide(fp)
            return fp.style_guide

    def _fallback_style_guide(self, fp: StyleFingerprint) -> str:
        """LLM不可用时的回退风格指南（基于统计规则生成）"""
        lines = ["风格指南(规则生成):"]

        # 句长
        if fp.avg_sentence_length < 20:
            lines.append("- 短句风格,简洁有力,适合快节奏叙事")
        elif fp.avg_sentence_length > 40:
            lines.append("- 长句风格,细腻丰富,适合深度描写")
        else:
            lines.append("- 长短结合,叙事节奏均衡")

        # 段落节奏
        if fp.paragraph_length_cv > 0.5:
            lines.append("- 段落长短交替,节奏感强")
        else:
            lines.append("- 段落结构稳定,适合平缓叙事")

        # 对话
        if fp.dialogue_ratio > 0.3:
            lines.append("- 对话驱动,角色互动丰富")
        elif fp.dialogue_ratio < 0.1:
            lines.append("- 叙述为主,对话精简")

        # 词汇
        if fp.word_diversity > 0.3:
            lines.append("- 词汇丰富,表达多元")
        else:
            lines.append("- 词汇集中,风格统一")

        return "\n".join(lines)

    def save_fingerprint(self, fp: StyleFingerprint, book_id: str):
        """保存指纹到 data/style/{book_id}/fingerprint.json

        Args:
            fp: 风格指纹
            book_id: 作品ID
        """
        path = settings.DATA_DIR / "style" / book_id
        path.mkdir(parents=True, exist_ok=True)

        data = {k: v for k, v in fp.__dict__.items() if not k.startswith("_")}
        # 序列化 tuple 为 list (JSON不支持tuple)
        if "top_words" in data:
            data["top_words"] = [[w, c] for w, c in data["top_words"]]

        (path / "fingerprint.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"[StyleAnalyzer] 指纹已保存: {path / 'fingerprint.json'}")

    def load_fingerprint(self, book_id: str) -> StyleFingerprint | None:
        """加载已保存的指纹

        Args:
            book_id: 作品ID

        Returns:
            StyleFingerprint 或 None
        """
        path = settings.DATA_DIR / "style" / book_id / "fingerprint.json"
        if not path.exists():
            logger.info(f"[StyleAnalyzer] 未找到已保存的指纹: {path}")
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fp = StyleFingerprint()
            for k, v in data.items():
                if hasattr(fp, k):
                    # 还原 tuple
                    if k == "top_words" and isinstance(v, list):
                        v = [(item[0], item[1]) for item in v if isinstance(item, list)]  # noqa: PLW2901
                    setattr(fp, k, v)
            logger.info(f"[StyleAnalyzer] 指纹已加载: {path}")
            return fp
        except Exception as e:
            logger.error(f"[StyleAnalyzer] 指纹加载失败: {e}")
            return None

    def compare(self, fp1: StyleFingerprint, fp2: StyleFingerprint) -> float:
        """比较两个指纹的相似度 (0.0 ~ 1.0)

        用于评估生成文本与参考风格的匹配程度。
        基于统计指标的加权相似度。

        Args:
            fp1: 指纹1
            fp2: 指纹2

        Returns:
            相似度分数
        """
        scores = []

        # 句长相似度
        if fp1.avg_sentence_length > 0 and fp2.avg_sentence_length > 0:
            ratio = min(fp1.avg_sentence_length, fp2.avg_sentence_length) / max(
                fp1.avg_sentence_length, fp2.avg_sentence_length
            )
            scores.append(ratio * 0.25)

        # 段长CV相似度
        cv_diff = abs(fp1.paragraph_length_cv - fp2.paragraph_length_cv)
        scores.append(max(0, 1 - cv_diff) * 0.15)

        # 对话占比相似度
        diag_diff = abs(fp1.dialogue_ratio - fp2.dialogue_ratio)
        scores.append(max(0, 1 - diag_diff * 2) * 0.25)

        # 词汇多样性相似度
        div_diff = abs(fp1.word_diversity - fp2.word_diversity)
        scores.append(max(0, 1 - div_diff * 3) * 0.15)

        # 句长标准差相似度
        if fp1.sentence_length_std > 0 and fp2.sentence_length_std > 0:
            std_ratio = min(fp1.sentence_length_std, fp2.sentence_length_std) / max(
                fp1.sentence_length_std, fp2.sentence_length_std
            )
            scores.append(std_ratio * 0.20)

        similarity = sum(scores) / sum([0.25, 0.15, 0.25, 0.15, 0.20])
        return round(min(1.0, max(0.0, similarity)), 3)


class StyleInjector:
    """风格注入器 — 将指纹注入到 Writer prompt 中

    将统计数据转化为自然语言创作约束,注入到 Writer 的系统提示中,
    使生成文本朝参考风格靠拢。
    """

    def build_style_prompt(self, fp: StyleFingerprint) -> str:
        """从指纹构建风格提示词

        生成的提示词可直接注入到 Writer 的 system prompt 中。

        Args:
            fp: 风格指纹

        Returns:
            风格提示词字符串
        """
        if not fp:
            return ""

        parts = ["## 文风要求\n"]

        # LLM生成的风格指南优先
        if fp.style_guide:
            parts.append(fp.style_guide + "\n")

        # 句式特征
        if fp.avg_sentence_length > 0:
            if fp.avg_sentence_length < 20:
                parts.append(
                    f"- 句式: 短句为主（平均{int(fp.avg_sentence_length)}字/句），"
                    f"简洁有力，避免冗长修饰"
                )
            elif fp.avg_sentence_length > 40:
                parts.append(
                    f"- 句式: 长句为主（平均{int(fp.avg_sentence_length)}字/句），"
                    f"细腻丰富，注重细节展开"
                )
            else:
                parts.append(
                    f"- 句式: 长短结合（平均{int(fp.avg_sentence_length)}字/句），"
                    f"根据场景需求灵活切换"
                )

            # 句长标准差
            if fp.sentence_length_std > 15:
                parts.append(
                    f"- 句长变化: 大（标准差{fp.sentence_length_std:.0f}），长短句交替使用"
                )
            elif fp.sentence_length_std < 5 and fp.avg_sentence_length > 10:
                parts.append(f"- 句长变化: 小（标准差{fp.sentence_length_std:.0f}），句长保持稳定")

        # 段落节奏
        if fp.paragraph_length_cv > 0.5:
            parts.append(
                f"- 段落: 长短交替（CV={fp.paragraph_length_cv:.2f}），避免均匀段落（AI特征）"
            )
        elif fp.paragraph_length_cv > 0.01 and fp.paragraph_length_cv <= 0.5:
            parts.append(f"- 段落: 结构稳定（CV={fp.paragraph_length_cv:.2f}），适合平缓叙事")

        # 对话特征
        if fp.dialogue_ratio > 0.3:
            parts.append(f"- 对话: 占比高({fp.dialogue_ratio:.0%})，用人物对话推动剧情和体现性格")
        elif fp.dialogue_ratio < 0.1:
            parts.append(
                f"- 对话: 精简({fp.dialogue_ratio:.0%})，以叙述为主，对话只用于关键信息传递"
            )
        else:
            parts.append(f"- 对话: 适中({fp.dialogue_ratio:.0%})，叙述与对话平衡")

        # 词汇倾向
        if fp.top_words:
            top_words_list = [w for w, _ in fp.top_words[:5]]
            parts.append(f"- 核心词汇倾向: {', '.join(top_words_list)}")

        if fp.word_diversity > 0.5:
            parts.append("- 词汇: 高度多样化,避免重复用词")
        elif fp.word_diversity < 0.2:
            parts.append("- 词汇: 集中统一,保持术语一致性")

        # 去AI味建议（通用，适用于所有风格）
        parts.append("\n## 反AI痕迹要求\n")
        parts.append("- 禁用AI高频套话: 突然、仿佛、似乎、总的来说、通过这件事")
        parts.append('- 变化句式开头，避免连续3句以上以"他/她/它"开头')
        parts.append('- 禁止总结性结尾（"从此以后""这次经历"等）')
        parts.append("- 段落长短交替，不得全部段落长度相近")
        parts.append("- 避免过度使用连接词（然而/因此/于是/随后）")
        parts.append("- 对话需有个性化差异，不同角色说话风格不同")

        return "\n".join(parts)


# ── 全局单例 ──
style_analyzer = StyleAnalyzer()
style_injector = StyleInjector()
