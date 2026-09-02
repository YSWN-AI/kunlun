"""
昆仑创作引擎 — 反向刹车机制

设计来源: novel-creator-skill 的反向刹车机制 (Reverse Brake Mechanism)

核心规则:
  1. 非最终章节不能解决核心冲突（必须留悬念）
  2. 每章必须引入至少1个新的未解决子问题
  3. 每章必须以悬念/问题/危机结尾（不能平淡收尾）
  4. 章节结尾检测：必须有 hook 信号（疑问/危机/转折）

与审计门禁的协作:
  - 作为 G4 (爽点间隔) 的补充，在蓝图中验证
  - 不作为独立门禁，而是注入 Architect 的 prompt
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ─── 悬念模式 ─────────────────────────────────────

CLIFFHANGER_PATTERNS = [
    # 疑问式结尾
    r"[？?]\s*$",  # 以问号结尾
    r"难道|莫非|难不成|究竟|到底",  # 疑问词
    # 危机/转折信号
    r"突然|就在这时|不料|谁也没想到",
    r"只见|眼看|正要|即将|就要",
    r"危险|危机|不妙|不好|糟糕",
    # 未知/悬念
    r"未知|谜团|秘密|真相|究竟是怎么回事",
    r"等待|审判|命运|何去何从|走向何方",
    # 中断/未完
    r"未完待续|欲知后事|下回分解",
]

# 核心冲突关键词
CORE_CONFLICT_KEYWORDS = [
    "最终决战",
    "终极对决",
    "最后之战",
    "宿命对决",
    "最终真相",
    "终极秘密",
    "一切的真相",
    "最终BOSS",
    "幕后黑手",
    "最终幕后",
    "结局",
    "终章",
    "尾声",
    "大结局",
]


@dataclass
class BrakeCheckResult:
    """反向刹车检查结果"""

    passed: bool  # 是否通过
    has_cliffhanger: bool  # 是否有悬念结尾
    new_problems: int  # 新引入的子问题数
    resolved_core_conflict: bool  # 是否解决了核心冲突
    warnings: list[str]  # 警告列表


class ReverseBrake:
    """
    反向刹车机制

    使用方式:
        brake = ReverseBrake()
        result = brake.check_chapter_end(draft, chapter, total_chapters)
        if not result.passed:
            print(result.warnings)
    """

    @staticmethod
    def check_chapter_end(
        draft: str, chapter: int, total_chapters: int = 0, is_final: bool = False
    ) -> BrakeCheckResult:
        """
        检查章节结尾是否符合反向刹车规则。

        Args:
            draft: 章节正文
            chapter: 当前章节号
            total_chapters: 总章节数（0=未知）
            is_final: 是否为最终章节

        Returns:
            BrakeCheckResult
        """
        warnings = []
        is_final = is_final or (total_chapters > 0 and chapter >= total_chapters)

        # 1. 悬念结尾检测
        has_cliffhanger = ReverseBrake._detect_cliffhanger(draft)
        if not has_cliffhanger and not is_final:
            warnings.append("章节结尾缺少悬念/钩子（建议以疑问/危机/转折结尾）")

        # 2. 新问题引入检测（检测"突然""不料""就在这时"等转折词）
        new_problems = ReverseBrake._count_new_problems(draft)
        if new_problems < 1 and not is_final:
            warnings.append(f"本章未引入新的未解决子问题（至少需要1个，检测到{new_problems}个）")

        # 3. 核心冲突解决检测（非最终章不得解决核心冲突）
        resolved_core = ReverseBrake._detect_core_conflict_resolution(draft)
        if resolved_core and not is_final:
            warnings.append("⚠️ 非最终章节解决了核心冲突！（建议保留悬念到终章）")

        passed = len(warnings) == 0
        return BrakeCheckResult(
            passed=passed,
            has_cliffhanger=has_cliffhanger,
            new_problems=new_problems,
            resolved_core_conflict=resolved_core,
            warnings=warnings,
        )

    @staticmethod
    def check_blueprint(blueprint: dict, chapter: int, total_chapters: int = 0) -> list[str]:
        """
        在蓝图阶段验证反向刹车规则。

        在 Architect 生成蓝图后调用，将警告注入 prompt 供 Writer 参考。
        """
        warnings = []
        scenes = blueprint.get("scenes", []) or []
        if not scenes:
            return warnings

        last_scene = scenes[-1]
        ending = (
            last_scene.get("description", "")
            + " "
            + last_scene.get("conflict", "")
            + " "
            + last_scene.get("outcome", "")
        )

        # 检查最后一个场景是否有悬念设计
        has_hook = any(kw in ending for kw in ["悬念", "未知", "危机", "转折", "悬念", "意外"])
        is_final = total_chapters > 0 and chapter >= total_chapters
        if not has_hook and not is_final:
            warnings.append("[反向刹车] 最后一幕缺少悬念设计，建议添加悬念/危机结尾")

        # 检查是否引入了新问题
        has_new_problem = any(
            kw in ending for kw in ["新问题", "新挑战", "新的危机", "难题", "困境"]
        )
        if not has_new_problem and not is_final:
            warnings.append("[反向刹车] 没有引入新的未解决子问题")

        return warnings

    @staticmethod
    def build_brake_prompt(chapter: int, total_chapters: int = 0) -> str:
        """
        生成反向刹车提示，注入 Writer prompt。

        让 LLM 知道：非终章要留悬念、引入新问题、不解核心冲突。
        """
        is_final = total_chapters > 0 and chapter >= total_chapters
        if is_final:
            return "【终章提示】这是最终章，请完结所有核心冲突和伏笔。"
        return (
            "【写作约束-反向刹车】\n"
            "1. 本章结尾必须留悬念（疑问/危机/转折），不能平淡结尾\n"
            "2. 必须引入至少1个新的未解决子问题\n"
            "3. 不能解决核心冲突（保留到终章）\n"
            "4. 每个场景结束时要有钩子，牵引读者继续阅读"
        )

    # ─── 内部检测方法 ──────────────────────────────

    @staticmethod
    def _detect_cliffhanger(text: str) -> bool:
        """检测文本末尾是否有悬念信号"""
        # 只看最后3段
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return False

        tail = "\n".join(paragraphs[-3:])
        return any(re.search(pattern, tail) for pattern in CLIFFHANGER_PATTERNS)

    @staticmethod
    def _count_new_problems(text: str) -> int:
        """统计新引入的子问题/挑战数量"""
        problem_signals = [
            "突然",
            "不料",
            "就在这时",
            "没想到",
            "谁知",
            "新的",
            "另一个",
            "还有",
            "更糟",
            "更可怕",
            "意外",
            "变故",
            "转折",
            "危机",
            "挑战",
        ]
        count = 0
        for signal in problem_signals:
            count += text.count(signal)
        return count

    @staticmethod
    def _detect_core_conflict_resolution(text: str) -> bool:
        """检测是否解决了核心冲突"""
        # 检查核心冲突关键词是否出现在"解决"上下文中
        for kw in CORE_CONFLICT_KEYWORDS:
            if kw in text:
                # 检查周围是否有"解决"语义
                idx = text.find(kw)
                context = text[max(0, idx - 50) : idx + len(kw) + 50]
                resolution_words = [
                    "解决",
                    "结束",
                    "打败",
                    "战胜",
                    "消灭",
                    "揭开",
                    "真相大白",
                    "尘埃落定",
                    "完结",
                ]
                if any(rw in context for rw in resolution_words):
                    return True
        return False


# 全局单例
reverse_brake = ReverseBrake()
