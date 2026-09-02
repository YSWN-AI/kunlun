"""
昆仑创作引擎 — 番茄平台流量优化门禁（2026年6月终极版）

基于番茄小说2026年6月流量机制全解，将平台算法规则转化为自动检查器。

核心设计:
  1. 潜力分精确计算（匹配番茄算法权重: 完读率30%/点击率25%/信用分20%/AI分15%/题材10%）
  2. 三级测试包预判（正常/死亡/微测试包 + 流量池分级 S/A/B/C/D）
  3. 黄金三章自动优化（首300字强制规则 + 章尾钩子 + 节奏控制）
  4. 全生命周期策略（冷启动→预验证→正式验证→首秀→稳定→书测）
  5. AI倾向分校准（匹配番茄标准，AI分≥70%触发纯AI标记）
  6. 反作弊规则检查（断更惩罚/频繁修改/更新节奏）

用法:
    from kunlun.audit.fanqie_gates import FanqieTrafficOptimizer
    report = FanqieTrafficOptimizer.check_chapter(draft, chapter=1, is_first_three=True)
    print(report.fanqie_ai_score)  # 番茄标准AI倾向分
    print(report.traffic_rating)   # 流量潜力评级（S/A/B/C/D）
    print(report.potential_score)  # 潜力分 (0-100)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ChapterTrafficReport:
    """单章流量优化报告（匹配番茄2026.6终极版规则）"""

    chapter: int = 0
    word_count: int = 0

    # 核心番茄指标
    fanqie_ai_score: float = 50.0  # 番茄标准AI倾向分 (0-100, 越低越好)
    has_cliffhanger: bool = False  # 是否有章尾钩子
    has_strong_opening: bool = False  # 首300字是否合格
    pacing_quality: float = 0.0  # 节奏质量 (0-1)
    hook_strength: str = "无"  # 钩子强度: 强/中/弱/无

    # 潜力分拆解（匹配番茄精确权重）
    predicted_completion_rate: float = 0.0  # 前3章完读率预判 (0-100) 权重30%
    predicted_ctr: float = 0.0  # 书名简介点击率预判 (0-100) 权重25%
    account_credit_score: float = 70.0  # 账号信用分 (0-100) 权重20%
    genre_heat: float = 50.0  # 题材热度 (0-100) 权重10%

    # 流量潜力
    traffic_rating: str = "未知"  # 流量评级: S/A/B/C/D
    potential_score: float = 0.0  # 潜力分 (0-100)
    suggestions: list[str] = field(default_factory=list)

    # 番茄全生命周期建议
    life_stage: str = ""  # 当前处于哪个阶段
    publish_advice: str = ""  # 发布策略建议

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "word_count": self.word_count,
            "fanqie_ai_score": self.fanqie_ai_score,
            "has_cliffhanger": self.has_cliffhanger,
            "has_strong_opening": self.has_strong_opening,
            "pacing_quality": self.pacing_quality,
            "hook_strength": self.hook_strength,
            "traffic_rating": self.traffic_rating,
            "potential_score": self.potential_score,
            "predicted_completion_rate": self.predicted_completion_rate,
            "predicted_ctr": self.predicted_ctr,
            "account_credit_score": self.account_credit_score,
            "genre_heat": self.genre_heat,
            "life_stage": self.life_stage,
            "publish_advice": self.publish_advice,
            "suggestions": self.suggestions,
        }


# ── 章尾钩子模式 ──────────────────────────────────

CLIFFHANGER_PATTERNS = {
    "strong": [
        r"[。！？\n].{0,10}(?:这时|突然|就在|没想到|谁知道|却发现|然而|但)",
        r"(?:什么|怎么|为什么|谁|哪).{0,10}[？?！!]",
        r"(?:你|我|他|她).{0,5}(?:是|竟然|难道).{0,10}$",
        r"(?:身份|秘密|真相|阴谋|陷阱|危机)",
    ],
    "medium": [
        r"(?:来了|到了|出现了|开始了|觉醒了)",
        r"(?:不妙|不好|糟糕|坏了)",
        r"(?:杀气|寒意|冷光|黑影|脚步)",
        r"(?:明天|接下来|下一章).{0,10}$",
    ],
    "weak": [
        r"(?:继续|期待|关注|下次)",
        r"(?:精彩|刺激|好看)",
        r"(?:未完待续)",
    ],
}

# ── 首300字必备元素 ──────────────────────────────

STRONG_OPENING_ELEMENTS = [
    r"(?:死|杀|血|尸|亡)",  # 死亡威胁
    r"(?:亏|输|败|毁|灭|破)",  # 重大损失
    r"(?:穿越|重生|绑定|系统|觉醒|获得)",  # 金手指
    r"(?:？\!|\!？|[？!])\s*",  # 反常识疑问/感叹
    r"(?:逃|追|躲|藏|跑|冲)",  # 紧迫行动
]

# ── 节奏段落关键词 ──────────────────────────────

PACING_KEYWORDS = {
    "高潮": [r"(?:轰|爆|杀|死|赢|败|破|碎)", r"(?:终于|最后|决战|爆发)"],
    "推进": [r"(?:然后|接着|继续|向前|走进)"],
    "铺垫": [r"(?:原来|这时|此刻|现在)", r"(?:平静|沉默|等待|看着)"],
    "悬念": [r"(?:突然|没想到|谁知道|却发现|然而)", r"(?:什么|怎么|为什么|谁)"],
}


class FanqieTrafficOptimizer:
    """
    番茄流量优化检查器

    每章生成后自动运行，确保内容符合番茄平台的流量机制要求。
    """

    @classmethod
    def check_chapter(
        cls, draft: str, chapter: int = 1, is_first_three: bool = False
    ) -> ChapterTrafficReport:
        """检查单章的番茄流量适配度"""
        report = ChapterTrafficReport(
            chapter=chapter,
            word_count=len(draft),
        )
        if not draft or len(draft) < 100:
            report.traffic_rating = "D"
            report.suggestions.append("章节过短，建议至少2000字")
            return report

        # 1. AI倾向分校准（匹配番茄标准）
        report.fanqie_ai_score = cls._calc_fanqie_ai_score(draft)

        # 2. 章尾钩子检测
        report.has_cliffhanger, report.hook_strength = cls._detect_cliffhanger(draft)
        if not report.has_cliffhanger:
            report.suggestions.append("章尾无钩子：每章最后一句必须留悬念，断在关键处")

        # 3. 首300字检测（前3章必须通过）
        report.has_strong_opening = cls._check_opening(draft[:300])
        if not report.has_strong_opening and is_first_three:
            report.suggestions.append("前300字不合格：必须出现死亡威胁/重大损失/反常识事件")

        # 4. 节奏质量
        report.pacing_quality = cls._check_pacing(draft)
        if report.pacing_quality < 0.5:
            report.suggestions.append("章节节奏偏平：每500字应有小爽点，避免连续平淡段落超过800字")

        # 5. 字数控制
        if len(draft) > 3500:
            report.suggestions.append(
                f"章节偏长({len(draft)}字)：番茄最佳字数2000-3000字，超过3500字完读率下降"
            )
        elif len(draft) < 1500:
            report.suggestions.append(f"章节偏短({len(draft)}字)：建议至少2000字，保证内容丰富度")

        # 6. 番茄全生命周期
        report.life_stage = cls.get_life_stage(report.word_count, chapter)
        stage_advice = cls.get_publish_advice(report.word_count)
        if stage_advice:
            report.publish_advice = (
                f"[{stage_advice.get('stage', '')}] "
                f"{stage_advice.get('daily_goal', '')}/天 "
                f"分{stage_advice.get('chapters_per_day', '?')}章发"
            )

        # 7. 综合流量潜力（精确匹配番茄权重算法）
        report.potential_score = cls._calc_potential(report)
        report.traffic_rating = cls._rate_traffic(report.potential_score)

        return report

    @classmethod
    def check_first_three(cls, chapters: list[str]) -> dict:
        """专门检查黄金三章"""
        results = {}
        for i, draft in enumerate(chapters[:3], 1):
            report = cls.check_chapter(draft, chapter=i, is_first_three=True)
            results[i] = report.to_dict()

        # 综合评分
        scores = [r.get("fanqie_ai_score", 100) for r in results.values()]
        hooks = [r.get("has_cliffhanger", False) for r in results.values()]
        openings = [r.get("has_strong_opening", False) for r in results.values()]

        avg_ai = sum(scores) / max(len(scores), 1)

        # 计算综合潜力分（上限100分，匹配番茄算法范围）
        potential = min(
            100,
            100 - avg_ai * 0.3 + (15 if sum(hooks) == 3 else 0) + (15 if sum(openings) == 3 else 0),
        )

        return {
            "chapters": results,
            "life_stage": cls.get_life_stage(sum(r.get("word_count", 0) for r in results.values())),
            "summary": {
                "平均AI倾向分": round(avg_ai, 1),
                "章尾钩子覆盖率": f"{sum(hooks)}/3",
                "首300字合格率": f"{sum(openings)}/3",
                "潜力分": round(potential, 1),
                "测试包预测": cls._rate_traffic(potential),
                "建议": cls._first_three_advice(avg_ai, sum(hooks), sum(openings)),
            },
        }

    @staticmethod
    def _calc_fanqie_ai_score(draft: str) -> float:
        """
        计算番茄标准AI倾向分 (0-100, 越低越好)

        匹配番茄平台标准：
        - AI倾向分 ≥ 70% → 纯AI批量创作账号标记
        - AI倾向分 越低 → 潜力分越高
        """
        try:
            from kunlun.audit.ai_features import calculate_ai_score, scan_text

            # 使用已有的 AI 特征检测
            human_score = calculate_ai_score(draft)
            # 反转：人类分数->AI分数 (番茄标准)
            ai_score = (1.0 - human_score) * 100

            # 加罚：检测到特定高权重特征时加重
            feature_hits = scan_text(draft)
            penalty = 0
            for h in feature_hits:
                if h["name"] in ("A2_因果连词", "A4_递进连词", "A5_总结词", "C4_模板化结尾"):
                    penalty += h["score"] * 5  # 每个高权重特征加5分
            return round(min(100, ai_score + penalty), 1)
        except Exception:
            return 50.0

    @staticmethod
    def _detect_cliffhanger(text: str) -> tuple[bool, str]:
        """检测章尾钩子"""
        # 取最后500字
        last_part = text[-500:] if len(text) > 500 else text

        for strength, patterns in CLIFFHANGER_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, last_part, re.MULTILINE):
                    return True, strength

        # 也检查是否以对话结尾（对话结尾也是一种钩子）
        if last_part.strip().endswith(('"', '"', "」", "』", "）", ")", "？", "！", "…")):
            return True, "weak"

        return False, "无"

    @staticmethod
    def _check_opening(text: str) -> bool:
        """检查首300字是否有强开元素"""
        if len(text) < 100:
            return False

        score = 0
        for elem in STRONG_OPENING_ELEMENTS:
            if re.search(elem, text):
                score += 1

        # 至少命中2个元素才算合格
        return score >= 2

    @staticmethod
    def _check_pacing(text: str) -> float:
        """检查章节节奏质量 (0-1)"""
        paragraphs = [p for p in text.split("\n\n") if len(p.strip()) > 10]
        if len(paragraphs) < 3:
            return 0.5

        # 检测高潮段落的分布
        peak_count = 0
        for p in paragraphs:
            for keywords in PACING_KEYWORDS["高潮"]:
                if re.search(keywords, p):
                    peak_count += 1
                    break

        # 每5-8段应有1个高潮点
        ideal_peaks = max(1, len(paragraphs) // 6)
        actual_peaks = min(peak_count, ideal_peaks)
        quality = actual_peaks / max(ideal_peaks, 1)

        # 检查是否太密集（全是高潮也不行）
        if peak_count > len(paragraphs) * 0.5:
            quality *= 0.8

        # 检查最长的平淡段落
        max_flat = 0
        current_flat = 0
        for p in paragraphs:
            is_peak = any(re.search(k, p) for k in PACING_KEYWORDS["高潮"])
            if is_peak:
                max_flat = max(max_flat, current_flat)
                current_flat = 0
            else:
                current_flat += len(p)

        max_flat = max(max_flat, current_flat)
        if max_flat > 800:
            quality *= 0.7  # 有超过800字的平淡段落

        return round(min(1.0, quality), 2)

    @classmethod
    def _calc_potential(cls, report: ChapterTrafficReport) -> float:
        """计算流量潜力分（精确匹配番茄2026.6算法）

        潜力分计算公式:
          (前3章完读率预判 × 30%) + (书名简介点击率预判 × 25%)
          + (账号信用分 × 20%) + ((100 - AI倾向分) × 15%)
          + (题材热度 × 10%)

        预验证期三级测试包:
          ≥70分 → 正常测试包 (1000-3000次)
          30-69分 → 死亡测试包 (50-200次)
          <30分 → 微测试包 (10-50次)
        """
        # 1. 完读率预判（基于文本特征）
        completion = cls._predict_completion_rate(report)

        # 2. 点击率预判（基于开头质量）
        ctr = cls._predict_ctr(report)

        # 3. 基础分
        credit = report.account_credit_score
        ai_factor = 100 - report.fanqie_ai_score

        # 4. 精确权重计算
        score = (
            completion * 0.30  # 前3章完读率预判 30%
            + ctr * 0.25  # 书名简介点击率预判 25%
            + credit * 0.20  # 账号信用分 20%
            + max(0, ai_factor) * 0.15  # AI倾向分 15%
            + report.genre_heat * 0.10  # 题材热度 10%
        )

        return round(max(0, min(100, score)), 1)

    @staticmethod
    def _predict_completion_rate(report: ChapterTrafficReport) -> float:
        """预判前3章完读率 (0-100)"""
        score = 50.0  # 基准分

        # 章尾钩子 -> 大幅提升完读率
        hook_bonus = {"强": 25, "中": 15, "弱": 5, "无": -20}
        score += hook_bonus.get(report.hook_strength, 0)

        # 强开头 -> 提升首章完读率
        if report.has_strong_opening:
            score += 15

        # 节奏质量
        score += report.pacing_quality * 15

        # 字数惩罚
        if report.word_count > 3500:
            score -= 10  # 长章完读率下降
        elif report.word_count < 1000:
            score -= 15  # 太短内容不足

        return round(max(0, min(100, score)), 1)

    @staticmethod
    def _predict_ctr(report: ChapterTrafficReport) -> float:
        """预判点击率 (0-100)"""
        score = 40.0  # 基准分

        # 强开头提升点击率
        if report.has_strong_opening:
            score += 25

        # 钩子强度影响
        hook_bonus = {"强": 15, "中": 10, "弱": 5, "无": -10}
        score += hook_bonus.get(report.hook_strength, 0)

        # AI倾向分高会降低点击率
        if report.fanqie_ai_score > 60:
            score -= 15

        return round(max(0, min(100, score)), 1)

    @staticmethod
    def _rate_traffic(score: float) -> str:
        """流量评级（匹配番茄三级测试包 + 流量池分级）"""
        if score >= 70:
            return "A (正常测试包→黄金池级)"
        if score >= 50:
            return "B (正常测试包→白银池级)"
        if score >= 30:
            return "C (死亡测试包→青铜池级)"
        return "D (微测试包级)"

    @classmethod
    def _first_three_advice(cls, avg_ai: float, hooks: int, openings: int) -> str:
        """黄金三章综合建议"""
        issues = []
        if avg_ai > 60:
            issues.append("AI倾向分偏高（≥60），建议手动修改前3章，加入个人风格")
        if avg_ai > 70:
            issues.insert(
                0, "⚠️ AI倾向分≥70%！系统判定为纯AI批量创作账号标记风险！必须人工重写前3章"
            )
        if hooks < 3:
            issues.append(
                f"仅{hooks}/3章有章尾钩子，每章结尾必须有悬念——番茄算法明确：每章结尾必须留悬念"
            )
        if openings < 3:
            issues.append(f"仅{openings}/3章首300字合格，前300字必须有死亡威胁/重大损失/反常识事件")
        if not issues:
            return "✅ 黄金三章质量良好，建议按此标准保持后续章节质量"
        return "；".join(issues)

    @classmethod
    def get_life_stage(cls, word_count: int, _chapter: int | None = None) -> str:
        """根据字数和章节判断处于番茄哪个生命周期"""
        if word_count < 3000:
            return "准备期（攒稿阶段）"
        if word_count < 80000:
            return "自然冷启动期（0-8万字）"
        if word_count < 100000:
            return "推荐评估与预验证期（8万字+）"
        if word_count < 130000:
            return "正式验证期（7天）"
        if word_count < 400000:
            return "首秀期（21天黄金窗口）"
        if word_count < 1000000:
            return "稳定期（13-100万字）"
        return "完结期与长尾期"

    @classmethod
    def get_publish_advice(cls, word_count: int, _total_chapters: int | None = None) -> dict:
        """获取全生命周期发布策略（匹配番茄时间表）

        发布时间:
          最佳: 周二、周三、周四 上午10:00 或 晚上8:00
          最差: 周五晚上、周六、周日
        更新节奏:
          冷启动期: 4000字/天, 分2章 (10:00 / 20:00)
          验证期: 4000-6000字/天, 分2-3章
          首秀期: 6000字以上/天, 分3章 (10:00 / 16:00 / 20:00)
        """
        advice = {}

        if word_count < 30000:
            advice = {
                "stage": "冷启动期",
                "stage_desc": "先写到3万字再发布，一次性发布前3万字。不要在周末发布。",
                "daily_goal": "4000字/天",
                "chapters_per_day": 2,
                "best_times": ["10:00", "20:00"],
                "best_days": ["周二", "周三", "周四"],
                "worst_days": ["周五晚", "周六", "周日"],
                "word_count_per_chapter": "2000字",
                "critical_actions": [
                    "先写好前3万字再发布",
                    "发布前打磨前3章到极致",
                    "选择精准标签组合",
                ],
                "forbidden_actions": [
                    "不要在周末发布",
                    "不要断更",
                    "不要修改书名/简介/封面",
                    "不要刷任何数据",
                ],
            }
        elif word_count < 100000:
            advice = {
                "stage": "验证期",
                "stage_desc": "每天稳定更新，观察自然数据。达标→继续；不达标→切书。",
                "daily_goal": "4000-6000字/天",
                "chapters_per_day": 2,
                "best_times": ["10:00", "16:00", "20:00(可选)"],
                "best_days": ["每天"],
                "critical_actions": [
                    "每天稳定更新，不能断更",
                    "观察首章完读率(≥25%)和书架比(≥3%)",
                    "如果自然数据不达标，直接切书",
                ],
                "forbidden_actions": [
                    "不要断更（断更1天-5信用分）",
                    "不要修改内容",
                    "不要刷数据",
                ],
            }
        else:
            advice = {
                "stage": "首秀期/稳定期",
                "stage_desc": (
                    "保持高频率更新，每3章一个小爽点，"
                    "每10章一个大爽点。20万字后可做书测。"
                ),
                "daily_goal": "6000字以上/天",
                "chapters_per_day": 3,
                "best_times": ["10:00", "16:00", "20:00"],
                "best_days": ["每天"],
                "book_test_at": "20万字（上传5个不同书名+封面测试点击率）",
                "critical_actions": [
                    "每天稳定更新6000+字",
                    "保持节奏：每3章小爽点，每10章大爽点",
                    "20万字做书测（5个书名+封面）",
                    "积极回复读者评论",
                ],
                "forbidden_actions": [
                    "不要断更（断更3天以上流量削减90%）",
                    "不要在首秀期做书测",
                    "不要刷任何数据",
                ],
            }

        # 添加反作弊警告
        advice["anti_cheat_warnings"] = [
            "番茄反作弊检测设备指纹、IP、行为模式、账号关联",
            "第一次作弊：警告+数据清除+流量减半",
            "第二次作弊：扣除收益+流量清零",
            "第三次作弊：永久封号",
        ]

        return advice


# 全局单例
fanqie_optimizer = FanqieTrafficOptimizer()
