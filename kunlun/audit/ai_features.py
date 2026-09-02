"""
昆仑创作引擎 — AI 特征检测库

灵感来源:
  - Humanizer (Siqi Chen): 24种AI写作特征库
  - Prosetheus: 3层检测（词→短语→结构）
  - InkOS: 4维AI痕迹检测
  - TextHumanize: 纯算法去AI化模式

本模块定义所有AI文本特征的模式，
供后写验证器（PostWriteValidator）和 G3 门禁共享使用。

每条特征包含:
  - name: 特征名
  - category: 分类 (词汇/句法/结构/修辞)
  - severity: 严重程度 (0.0-1.0)
  - patterns: 匹配模式列表
  - weight: 在综合评分中的权重
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AIFeature:
    """AI文本特征定义"""

    name: str  # 特征名
    category: str  # 词汇/句法/结构/修辞/格式
    severity: float  # 0.0-1.0
    patterns: list[str] = field(default_factory=list)
    description: str = ""
    weight: float = 1.0


# ═══════════════════════════════════════════════════════
# 24+ AI 写作特征
# 分类: A 词汇特征 / B 句法特征 / C 结构特征 / D 修辞特征 / E 格式特征
# ═══════════════════════════════════════════════════════

AI_FEATURES: list[AIFeature] = [
    # ── A组: 词汇特征（高频套话词） ─────────────────
    AIFeature(
        "A1_套话副词",
        "词汇",
        0.6,
        ["仿佛", "忽然", "竟然", "不禁", "宛如", "似乎", "好像", "顿时"],
        "过度使用'仿佛/忽然/竟然'等套话副词（排除日常叙事常用词）",
    ),
    AIFeature(
        "A2_因果连词",
        "词汇",
        0.5,
        ["因此", "所以", "于是", "故而", "因而", "为此"],
        "过度使用'因此/所以/于是'等因果连词",
    ),
    AIFeature(
        "A3_转折连词",
        "词汇",
        0.5,
        ["然而", "但是", "不过", "可是", "却", "只是"],
        "过度使用'然而/但是/不过'等转折连词",
    ),
    AIFeature(
        "A4_递进连词",
        "词汇",
        0.4,
        ["此外", "另外", "再者", "加之", "不仅如此", "与此同时"],
        "过度使用'此外/另外/再者'等递进连词",
    ),
    AIFeature(
        "A5_总结词",
        "词汇",
        0.7,
        ["综上所述", "总而言之", "总的来说", "总体而言", "总的来看"],
        "使用总结性词汇（AI最爱）",
    ),
    AIFeature(
        "A6_展望词",
        "词汇",
        0.6,
        ["接下来", "在接下来的", "未来的日子里", "在未来的", "今后"],
        "使用展望/预测式词汇",
    ),
    AIFeature(
        "A7_强调副词",
        "词汇",
        0.3,
        ["确实", "的确", "实际上", "事实上", "本质上", "从根本上说"],
        "过度使用强调副词",
    ),
    AIFeature(
        "A8_模糊限定词",
        "词汇",
        0.4,
        ["某种", "某种程度", "某种意义上", "某种程度上", "一定程度的"],
        "使用模糊限定词",
    ),
    # ── B组: 句法特征（句式模式） ─────────────────
    AIFeature(
        "B1_XX了句式",
        "句法",
        0.5,
        ["来到了", "走到了", "看到了", "听到了", "想到了", "来到了"],
        "流水账式'XX了'句群",
    ),
    AIFeature(
        "B2_被字句过度",
        "句法",
        0.4,
        ["被", "遭到", "受到", "遭受"],
        "被字句过度使用（使叙述被动化）",
    ),
    AIFeature(
        "B3_让字句",
        "句法",
        0.3,
        ["让人", "令人", "使人", "叫人不禁"],
        "让字句过度（削弱直接表现力）",
    ),
    AIFeature(
        "B4_双字句首",
        "句法",
        0.3,
        [],
        "连续多句以相同单字主语开头（需结合句首检测，暂不启用简单词频匹配）",
    ),
    AIFeature(
        "B5_过度解释",
        "句法",
        0.6,
        ["也就是", "也就是", "换句话说", "也就是说", "这意味着"],
        "过度解释/翻译式表达",
    ),
    # ── C组: 结构特征（段落/文章结构） ──────────
    AIFeature("C1_段落等长", "结构", 0.5, [], "所有段落长度高度一致（AI典型特征）"),
    AIFeature("C2_三段式结构", "结构", 0.6, [], "严格的引入→分析→总结三段式"),
    AIFeature(
        "C3_列表式段落",
        "结构",
        0.5,
        ["第一", "第二", "第三", "首先", "其次", "最后", "一是", "二是"],
        "使用列表式结构组织内容",
    ),
    AIFeature(
        "C4_模板化结尾",
        "结构",
        0.7,
        ["接下来", "这一切才刚开始", "真正的考验", "未知的", "新的篇章"],
        "使用AI模板化结尾",
    ),
    AIFeature("C5_事事交代", "结构", 0.5, [], "每件事都交代起因经过结果，缺乏留白"),
    # ── D组: 修辞特征 ───────────────────────────
    AIFeature("D1_排比过度", "修辞", 0.4, [], "过度使用排比句式（AI修辞偏好）"),
    AIFeature(
        "D2_比喻模板化",
        "修辞",
        0.5,
        ["像", "仿佛", "宛如", "犹如", "如同", "好比"],
        "过度使用'像/仿佛/宛如'等比喻词",
    ),
    AIFeature(
        "D3_情感直白",
        "修辞",
        0.4,
        ["感到", "感觉到", "感受到", "心中充满", "内心充满"],
        "情感直白陈述而非通过动作/对话展现",
    ),
    AIFeature(
        "D4_心理描述过度",
        "修辞",
        0.5,
        ["心想", "心里想", "暗自想", "暗暗想", "寻思", "思忖"],
        "过度使用直接心理描述",
    ),
    # ── E组: 格式特征 ───────────────────────────
    AIFeature("E1_冒号解释", "格式", 0.5, [": ", "："], "过度使用冒号做解释说明（AI文档风格）"),
    AIFeature(
        "E2_引号对话标签",
        "格式",
        0.4,
        ["说道", "问道", "回答道", "开口说道", "出声道"],
        "使用'说道/问道'等废话对话标签",
    ),
    AIFeature("E3_括号注释", "格式", 0.5, ["（", "）", "(", ")"], "过度使用括号做注释说明"),
    AIFeature(
        "E4_数字编号",
        "格式",
        0.5,
        ["1.", "2.", "3.", "①", "②", "③"],
        "使用数字编号组织内容（AI文档风格）",
    ),
    # ── F组: 叙事特征（叙述方式/视角问题） ──────────────
    # 参考 Humanizer (Siqi Chen) 24种AI特征 + TextHumanize 纯算法
    AIFeature(
        "F1_过度解释腔",
        "叙事",
        0.6,
        [
            "也就是说",
            "换句话说",
            "这意味着",
            "其实就是",
            "说白了",
            "本质上",
            "实际上",
            "其实",
            "说到底",
        ],
        "过度解释/翻译式表达（AI最典型特征之一）",
    ),
    AIFeature(
        "F2_弱动词",
        "叙事",
        0.4,
        ["进行", "做出", "实施", "展开", "加以", "予以", "给予"],
        "使用'进行/做出'等弱动词代替具体动作",
    ),
    AIFeature(
        "F3_名词化过度",
        "叙事",
        0.5,
        ["有了", "带来了", "产生了", "发生了", "引起了", "造成了", "导致了", "促进了"],
        "使用'有了/带来了'等空泛变化描述",
    ),
    AIFeature(
        "F4_程度副词堆砌",
        "叙事",
        0.3,
        ["非常", "很", "十分", "极其", "特别", "相当", "颇为", "异常", "格外", "较为"],
        "过度使用程度副词（削弱文字力度）",
    ),
    AIFeature(
        "F5_视角标记词",
        "叙事",
        0.4,
        ["从...的角度", "从...来看", "在...看来", "以...的视角", "站在...立场"],
        "显式标记视角切换（AI避免视角混淆的习惯）",
    ),
    AIFeature(
        "F6_抽象描述代替具体",
        "叙事",
        0.5,
        ["某种说不出的", "一种莫名的", "难以言喻的", "无法形容的", "不可名状的", "难以描述的"],
        "使用抽象描述代替具体感官细节",
    ),
    # ── G组: 对话特征（对话写作质量） ─────────────────
    # AI 生成的对话往往过于完整/正式，缺乏口语化特征
    AIFeature(
        "G1_完美对话标签",
        "对话",
        0.5,
        ["说道", "回答道", "回答道", "开口道", "出声道", "言道", "话道", "问了一句", "答了一句"],
        "对话标签过于完整正式（真实对话常用动作替代）",
    ),
    AIFeature(
        "G2_对话过于完整",
        "对话",
        0.4,
        [],  # 由 scan_structural_features 检测长对白比例
        "对话过长且过于完整（AI对话缺乏中断/省略/语气词）",
    ),
    AIFeature(
        "G3_缺语气词",
        "对话",
        0.3,
        [],  # 由 scan_structural_features 检测语气词密度
        "对话中缺乏'嗯/啊/哦/嘛/啦'等自然语气词",
    ),
    AIFeature(
        "G4_独白式说明",
        "对话",
        0.5,
        ["我跟你说", "你要知道", "你要明白", "听我说", "是这样的", "事情是这样的"],
        "角色通过对话向另一个角色解释已知信息（信息倾销）",
    ),
    AIFeature(
        "G5_情感直白标签",
        "对话",
        0.4,
        ["生气地说", "愤怒地", "高兴地", "伤心地", "激动地", "不耐烦地", "冷冷地", "淡淡地"],
        "通过副词标签直接标注情感而非通过内容展现",
    ),
    # ── H组: 新增特征（借鉴oh-story-claudecode + Prosetheus）──
    # 参考: 24禁词 + 20模板 + 6维统计CV
    AIFeature(
        "H1_只见体",
        "词汇",
        0.6,
        ["只见", "只看见", "只见到"],
        "使用'只见'体（AI最典型的视觉引导词）",
    ),
    AIFeature(
        "H2_顿时体",
        "词汇",
        0.6,
        ["顿时", "当下", "立刻", "马上", "顷刻间", "霎时间"],
        "使用'顿时/立刻'等瞬时反应词（AI叙事习惯）",
    ),
    AIFeature(
        "H3_不由得",
        "词汇",
        0.5,
        ["不由得", "忍不住", "不由自主", "情不自禁"],
        "使用'不由得/忍不住'等被动反应描述",
    ),
    AIFeature(
        "H4_心中体",
        "词汇",
        0.5,
        ["心中", "心里", "心底", "内心深处", "骨子里"],
        "过度使用'心中/心里'等内心描述词",
    ),
    AIFeature(
        "H5_莫名体",
        "词汇",
        0.4,
        ["莫名的", "莫名的", "说不出的", "难以言喻的", "无法形容的", "不可名状的"],
        "使用'莫名的/说不出的'等模糊情感词（AI偷懒写法）",
    ),
    AIFeature(
        "H6_连连体",
        "词汇",
        0.3,
        ["连连", "频频", "不住地", "不停地", "不断地", "一个劲地", "使劲地"],
        "使用'连连/频频'等动作频率词（AI堆砌习惯）",
    ),
]


# ── 结构性特征的检测辅助 ──────────────────────────────

# B4: 常见双字句首模式（AI 写作偏好以这些词开头句子）
B4_DOUBLE_CHAR_STARTS = [
    "这就",
    "那是",
    "可以",
    "但是",
    "然而",
    "因此",
    "所以",
    "不过",
    "只见",
    "此刻",
    "此刻",
    "这时",
    "忽然",
    "突然",
    "只见",
    "看到",
    "听到",
    "想到",
    "感到",
]

# C5: 段落末尾总结标记
C5_SUMMARY_ENDINGS = [
    "就这样",
    "于是",
    "至此",
    "这样一来",
    "因此",
    "所以",
    "这才",
    "总算",
    "终究",
    "果然",
]

# D1: 排比句式标记（连续句子以相同结构开头）
D1_PARALLEL_STARTS = [
    "他",
    "她",
    "它",
    "这",
    "那",
    "不",
    "没",
    "就是",
    "那是",
    "这是",
    "可是",
    "但是",
]

# G2: 对话过长阈值（超过此字符数的对白视为"过于完整"）
G2_LONG_DIALOGUE_THRESHOLD = 100

# G3: 自然语气词（对话中应有的口语化成分）
G3_NATURE_PARTICLES = {
    "嗯",
    "啊",
    "哦",
    "嘛",
    "啦",
    "吧",
    "呢",
    "呀",
    "呵",
    "唉",
    "哟",
    "喂",
    "噢",
    "哼",
    "唔",
    "嘶",
}


def scan_structural_features(text: str, results: list[dict]) -> None:  # noqa: PLR0912
    """扫描结构性AI特征（非关键词匹配，需统计分析）

    逐一检查已声明的结构性特征:
    - B4_双字句首: 句子以双字模式开头的比例
    - C1_段落等长: 段落长度变异系数
    - C2_三段式: 3段结构相似度
    - C5_事事交代: 段落末尾总结模式
    - D1_排比过度: 连续相同句式开头
    """
    if len(text) < 200:
        return

    paragraphs = [p.strip() for p in text.replace("\r", "").split("\n\n") if p.strip()]
    sentences = [
        s.strip()
        for s in text.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n")
        if s.strip()
    ]

    # ── B4: 双字句首 ──
    if paragraphs and sentences:
        double_char_count = 0
        for s in sentences:
            for start in B4_DOUBLE_CHAR_STARTS:
                if s.startswith(start):
                    double_char_count += 1
                    break
        b4_ratio = double_char_count / max(len(sentences), 1)
        if b4_ratio > 0.25:  # >25% 的句子以双字模式开头
            score = min(1.0, (b4_ratio - 0.25) * 2)
            results.append(
                {
                    "name": "B4_双字句首",
                    "category": "句法",
                    "severity": 0.3,
                    "count": double_char_count,
                    "density": round(b4_ratio, 3),
                    "score": round(score, 2),
                    "description": f"连续多句以相同双字开头 ({b4_ratio:.1%})",
                }
            )

    # ── C1: 段落等长 ──
    if len(paragraphs) >= 3:
        para_lengths = [len(p) for p in paragraphs]
        mean_len = sum(para_lengths) / len(para_lengths)
        if mean_len > 0:
            std = (sum((v - mean_len) ** 2 for v in para_lengths) / len(para_lengths)) ** 0.5
            cv = std / mean_len
            if cv < 0.25:  # CV < 0.25 表示段落长度异常均匀
                score = min(1.0, (0.25 - cv) * 4)
                results.append(
                    {
                        "name": "C1_段落等长",
                        "category": "结构",
                        "severity": 0.5,
                        "count": len(paragraphs),
                        "density": round(cv, 3),
                        "score": round(score, 2),
                        "description": f"段落长度高度一致 (CV={cv:.2f})",
                    }
                )

    # ── C2: 三段式结构 ──
    if len(paragraphs) >= 6:
        third = max(1, len(paragraphs) // 3)
        p1_len = sum(len(p) for p in paragraphs[:third])
        p2_len = sum(len(p) for p in paragraphs[third : 2 * third])
        p3_len = sum(len(p) for p in paragraphs[2 * third :])
        total = p1_len + p2_len + p3_len
        if total > 0:
            # 检查3段比例是否过于均匀（AI倾向）
            ratios = [p1_len / total, p2_len / total, p3_len / total]
            max_deviation = max(abs(r - 1 / 3) for r in ratios)
            if max_deviation < 0.08:  # 每段都在 25%-41% 之间，过于均匀
                score = min(1.0, (0.08 - max_deviation) * 5)
                results.append(
                    {
                        "name": "C2_三段式结构",
                        "category": "结构",
                        "severity": 0.6,
                        "count": 3,
                        "density": round(max_deviation, 3),
                        "score": round(score, 2),
                        "description": f"严格的引入→分析→总结三段式 (偏差={max_deviation:.2f})",
                    }
                )

    # ── C5: 事事交代（每段末尾总结句） ──
    if paragraphs:
        summary_count = 0
        for p in paragraphs:
            last_sentence = p.split("。")[-1] if "。" in p else p
            for ending in C5_SUMMARY_ENDINGS:
                if last_sentence.startswith(ending):
                    summary_count += 1
                    break
        c5_ratio = summary_count / max(len(paragraphs), 1)
        if c5_ratio > 0.3:  # >30% 段落以总结句式结尾
            score = min(1.0, (c5_ratio - 0.3) * 2)
            results.append(
                {
                    "name": "C5_事事交代",
                    "category": "结构",
                    "severity": 0.5,
                    "count": summary_count,
                    "density": round(c5_ratio, 3),
                    "score": round(score, 2),
                    "description": f"每件事都交代起因经过结果 ({c5_ratio:.1%}段落以总结结尾)",
                }
            )

    # ── D1: 排比过度（连续句子以相同结构开头） ──
    if len(sentences) >= 6:
        max_run = 0
        current_run = 1
        prev_start = None
        for s in sentences:
            if not s:
                continue
            cur_start = s[:2] if len(s) >= 2 else s
            if cur_start == prev_start and cur_start.isalpha():
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1
            prev_start = cur_start
        if max_run >= 3:  # 连续3+句子以相同开头
            score = min(1.0, (max_run - 2) * 0.3)
            results.append(
                {
                    "name": "D1_排比过度",
                    "category": "修辞",
                    "severity": 0.4,
                    "count": max_run,
                    "density": float(max_run),
                    "score": round(score, 2),
                    "description": f"过度使用排比句式 (连续{max_run}句同结构开头)",
                }
            )

    # ── G2: 对话过于完整（长对白比例过高） ──
    dialogue_lines = [s for s in sentences if any(q in s for q in ["“", "」", '"'])]
    if len(dialogue_lines) >= 3:
        long_lines = sum(1 for d in dialogue_lines if len(d) > G2_LONG_DIALOGUE_THRESHOLD)
        long_ratio = long_lines / max(len(dialogue_lines), 1)
        if long_ratio > 0.4:  # >40% 的对白超过100字
            score = min(1.0, (long_ratio - 0.4) * 2)
            results.append(
                {
                    "name": "G2_对话过于完整",
                    "category": "对话",
                    "severity": 0.4,
                    "count": long_lines,
                    "density": round(long_ratio, 3),
                    "score": round(score, 2),
                    "description": f"对白过长 ({long_ratio:.0%}超过100字)，缺乏自然中断",
                }
            )

    # ── G3: 缺语气词（对话中自然语气词过少） ──
    if len(dialogue_lines) >= 3:
        total_chars = sum(len(d) for d in dialogue_lines)
        particle_count = sum(1 for d in dialogue_lines for p in G3_NATURE_PARTICLES if p in d)
        particle_density = particle_count / max(total_chars, 1) * 1000
        if particle_density < 1.0:  # 每千字少于1个语气词
            score = min(1.0, (1.0 - particle_density) * 0.5)
            results.append(
                {
                    "name": "G3_缺语气词",
                    "category": "对话",
                    "severity": 0.3,
                    "count": particle_count,
                    "density": round(particle_density, 2),
                    "score": round(score, 2),
                    "description": f"对话缺自然语气词 (密度{particle_density:.1f}/千字)",
                }
            )


# ── 按分类查询 ────────────────────────────────────────


def get_features_by_category(category: str) -> list[AIFeature]:
    """按分类获取特征列表"""
    return [f for f in AI_FEATURES if f.category == category]


def get_features_by_severity(min_severity: float = 0.5) -> list[AIFeature]:
    """按最低严重程度获取特征"""
    return [f for f in AI_FEATURES if f.severity >= min_severity]


def get_feature_names() -> list[str]:
    """获取所有特征名"""
    return [f.name for f in AI_FEATURES]


# ── 文本扫描 ──────────────────────────────────────────


def scan_text(text: str) -> list[dict]:
    """扫描文本，返回触发的所有AI特征（关键词 + 结构性分析）

    参考: Prosetheus 3层检测（词→短语→结构）
    - 词汇层: 关键词匹配（A组、部分B/E组）
    - 短语层: 句式模式（B组、E组）
    - 结构层: 段落CV/三段式/排比（C组、D组、B4/C1/C2/C5/D1）

    Returns:
        [{name, category, severity, count, score}, ...]
    """
    results = []
    for feat in AI_FEATURES:
        if not feat.patterns:
            continue  # 结构性特征由 scan_structural_features 处理
        count = sum(text.count(p) for p in feat.patterns)
        if count > 0:
            # 频率归一化: 每1000字的出现次数
            density = count / max(len(text), 1) * 1000
            # 动态阈值: 根据特征严重程度调整
            base_threshold = 8.0 - feat.severity * 8.0  # severity 0.2→6.4, 0.7→2.4
            threshold = max(1.0, base_threshold)
            raw_score = density / max(threshold, 0.1)
            score = max(0, (raw_score - 0.5))
            if score < 0.3:
                continue
            results.append(
                {
                    "name": feat.name,
                    "category": feat.category,
                    "severity": feat.severity,
                    "count": count,
                    "density": round(density, 2),
                    "score": round(score, 2),
                    "description": feat.description,
                }
            )

    # 结构性特征扫描（Prosetheus 3层检测的"结构层"）
    scan_structural_features(text, results)

    return sorted(results, key=lambda x: x["score"], reverse=True)


def calculate_ai_score(text: str) -> float:
    """计算文本的 AI 痕迹综合分数（0=纯AI，1=纯人类）

    算法: 对每个触发的特征，score × severity 加权求和后取补。
    - score=0: 特征未触发 → 不影响
    - score=1: 特征强烈触发 → 人类度 -= severity

    注意: 短文本（<200字）不执行检测，返回中立 0.5。
    """
    if len(text) < 200:
        return 0.5  # 短文本不判定
    hits = scan_text(text)
    if not hits:
        return 1.0
    # 加权: 特征强度 × 特征严重程度
    total_weight = sum(h["severity"] for h in hits)
    if total_weight == 0:
        return 1.0
    ai_score = sum(min(h["score"], 1.0) * h["severity"] for h in hits) / total_weight
    # 转换为人类分数（取补）
    human_score = 1.0 - ai_score
    return round(human_score, 4)
