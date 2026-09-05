"""
昆仑创作引擎 — 智能学习偏好提取器

从用户反馈/修改中自动提取写作偏好，支持：
- 自然语言反馈提取（对话/风格/节奏/人物等分类）
- 用户修改对比提取（diff 分析）
- 批量提取

提取结果格式:
    {
        "type": "rule" | "positive" | "negative",
        "category": "dialogue" | "style" | "pace" | "character" | "plot" | "structure",
        "content": "具体偏好内容",
        "action": "add" | "reinforce" | "remove",
        "confidence": 0.0-1.0,
        "source": "feedback" | "edit",
    }
"""

from __future__ import annotations

from typing import Any

from loguru import logger

# ─── 反馈模式匹配规则 ─────────────────────────────────────
# 每条规则: (关键词列表, 分类, 生成的偏好内容, action, 置信度)

_FEEDBACK_PATTERNS: list[tuple[list[str], str, str, str, float]] = [
    # ── 对话类 ──
    (
        [
            "对话不正式",
            "对话太正式",
            "对话随意",
            "对话自然",
            "口语化",
            "对话像背书",
            "不那么正式",
            "对话不够自然",
        ],
        "dialogue",
        "保持对话随意自然，口语化表达",
        "add",
        0.85,
    ),
    (
        ["对话太多", "对话过少", "增加对话", "减少对话", "对话冗长"],
        "dialogue",
        "控制对话比例，避免过多或过少",
        "add",
        0.7,
    ),
    (
        ["对话生硬", "对话不自然", "对话别扭"],
        "dialogue",
        "对话要自然流畅，符合人物性格",
        "add",
        0.8,
    ),
    # ── 风格类 ──
    (
        ["删除过多描述", "描述太多", "描写过多", "太啰嗦", "太冗长", "水字数"],
        "style",
        "不要华丽辞藻或过度描述，精简语言",
        "add",
        0.85,
    ),
    (
        ["华丽辞藻", "辞藻堆砌", "太文艺", "文风华丽", "文风太雅"],
        "style",
        "避免华丽辞藻，用简洁有力的语言",
        "add",
        0.8,
    ),
    (
        ["文风太白", "太直白", "不够文艺", "增加描写", "描写不够"],
        "style",
        "适当增加文学性描写，提升文笔",
        "add",
        0.75,
    ),
    (
        ["第一人称", "用第一人称", "第三人称", "用第三人称"],
        "style",
        "保持一致的叙事视角",
        "add",
        0.7,
    ),
    # ── 节奏类 ──
    (
        ["节奏太慢", "节奏拖沓", "节奏太慢了", "加快节奏", "太拖了"],
        "pace",
        "紧凑节奏，删减不必要场景，加快推进",
        "add",
        0.9,
    ),
    (
        ["节奏太快", "节奏太赶", "放慢节奏", "节奏太急"],
        "pace",
        "适当放慢节奏，增加细节和过渡",
        "add",
        0.8,
    ),
    (
        ["节奏紧凑", "节奏好", "节奏不错"],
        "pace",
        "保持紧凑的叙事节奏",
        "reinforce",
        0.7,
    ),
    # ── 人物类 ──
    (
        ["角色写得好", "这个角色好", "人物塑造好", "角色不错", "人设好"],
        "character",
        "保持当前人物塑造方式",
        "reinforce",
        0.8,
    ),
    (
        ["角色崩了", "人设崩了", "人物OOC", "角色不像", "人物不一致"],
        "character",
        "严格保持人物设定一致性，避免OOC",
        "add",
        0.9,
    ),
    (
        ["主角太弱", "主角太圣母", "主角优柔寡断", "主角不够果断"],
        "character",
        "主角要杀伐果断，不优柔寡断",
        "add",
        0.85,
    ),
    (
        ["主角太强", "主角无敌", "龙傲天", "主角太顺"],
        "character",
        "给主角设置合理挑战和挫折",
        "add",
        0.75,
    ),
    (
        ["配角单薄", "配角没存在感", "工具人"],
        "character",
        "丰富配角形象，避免工具人化",
        "add",
        0.75,
    ),
    # ── 情节类 ──
    (
        ["剧情老套", "套路", "没新意", "剧情 predictable"],
        "plot",
        "增加剧情反转和新意，避免套路化",
        "add",
        0.8,
    ),
    (
        ["爽点不足", "不够爽", "爽点少", "不够打脸"],
        "plot",
        "强化爽点设计，增加打脸和逆袭情节",
        "add",
        0.85,
    ),
    (
        ["爽点够", "很爽", "打脸好", "爽点设计好"],
        "plot",
        "保持当前爽点设计节奏",
        "reinforce",
        0.75,
    ),
    (
        ["逻辑漏洞", "逻辑不通", "bug", "不合理", "说不通"],
        "plot",
        "严格检查逻辑自洽性，消除逻辑漏洞",
        "add",
        0.85,
    ),
    (
        ["伏笔好", "伏笔回收好", "铺垫好"],
        "plot",
        "保持伏笔和铺垫的设计方式",
        "reinforce",
        0.75,
    ),
    # ── 结构类 ──
    (
        ["章节末没钩子", "结尾平淡", "章末没悬念", "不想看下一章"],
        "structure",
        "每章结尾设置悬念钩子，吸引读者继续阅读",
        "add",
        0.85,
    ),
    (
        ["开头好", "开头吸引人", "开篇不错"],
        "structure",
        "保持当前开篇方式",
        "reinforce",
        0.7,
    ),
    (
        ["开头慢", "开篇拖沓", "黄金三章不行"],
        "structure",
        "优化开篇，前三章必须抓住读者",
        "add",
        0.8,
    ),
    (
        ["过渡好", "衔接自然", "转场好"],
        "structure",
        "保持当前场景过渡和转场方式",
        "reinforce",
        0.7,
    ),
]

# 正面反馈关键词（用于判断 reinforce）
_POSITIVE_KEYWORDS = [
    "好",
    "不错",
    "棒",
    "赞",
    "喜欢",
    "满意",
    "精彩",
    "到位",
    "自然",
    "流畅",
    "吸引人",
    "有感觉",
    "有那味",
    "对味",
]

# 负面反馈关键词
_NEGATIVE_KEYWORDS = [
    "不好",
    "不行",
    "差",
    "烂",
    "糟糕",
    "讨厌",
    "不喜欢",
    "太多",
    "太少",
    "太",
    "不够",
    "删除",
    "去掉",
    "别",
]


class PreferenceExtractor:
    """从用户反馈和修改中提取写作偏好

    用法:
        extractor = PreferenceExtractor()
        pref = extractor.extract_from_feedback("让对话不那么正式")
        # -> {"type": "rule", "category": "dialogue", ...}
    """

    def __init__(self) -> None:
        self._patterns = _FEEDBACK_PATTERNS

    def extract_from_feedback(self, feedback: str) -> dict[str, Any]:
        """从自然语言反馈中提取偏好

        Args:
            feedback: 用户反馈文本

        Returns:
            偏好字典，未匹配时返回 type="unknown"
        """
        if not feedback or not feedback.strip():
            return {
                "type": "unknown",
                "category": "general",
                "content": "",
                "action": "add",
                "confidence": 0.0,
                "source": "feedback",
                "raw": feedback,
            }

        text = feedback.strip()
        best_match: tuple[str, str, str, float] | None = None
        best_score = 0

        for keywords, category, content, action, confidence in self._patterns:
            score = 0
            for kw in keywords:
                if kw in text:
                    score += len(kw)  # 长关键词权重更高
            if score > best_score:
                best_score = score
                best_match = (category, content, action, confidence)

        if best_match:
            category, content, action, confidence = best_match
            pref_type = "positive" if action == "reinforce" else "rule"
            return {
                "type": pref_type,
                "category": category,
                "content": content,
                "action": action,
                "confidence": confidence,
                "source": "feedback",
                "raw": feedback,
            }

        # 未匹配到具体模式，做通用判断
        is_positive = any(kw in text for kw in _POSITIVE_KEYWORDS)
        is_negative = any(kw in text for kw in _NEGATIVE_KEYWORDS)

        if is_positive and not is_negative:
            return {
                "type": "positive",
                "category": "general",
                "content": feedback,
                "action": "reinforce",
                "confidence": 0.5,
                "source": "feedback",
                "raw": feedback,
            }

        if is_negative:
            return {
                "type": "rule",
                "category": "general",
                "content": f"注意：{feedback}",
                "action": "add",
                "confidence": 0.4,
                "source": "feedback",
                "raw": feedback,
            }

        return {
            "type": "unknown",
            "category": "general",
            "content": feedback,
            "action": "add",
            "confidence": 0.3,
            "source": "feedback",
            "raw": feedback,
        }

    def extract_from_edit(self, original: str, modified: str) -> dict[str, Any]:
        """从用户修改中提取偏好（对比差异）

        通过对比原文和修改后的文本，推断用户的写作偏好。

        Args:
            original: 原始文本
            modified: 修改后的文本

        Returns:
            偏好字典
        """
        if not original or not modified:
            return {
                "type": "unknown",
                "category": "general",
                "content": "",
                "action": "add",
                "confidence": 0.0,
                "source": "edit",
                "raw": "",
            }

        orig_len = len(original)
        mod_len = len(modified)
        len_ratio = mod_len / orig_len if orig_len > 0 else 1.0

        # 计算差异
        import difflib

        matcher = difflib.SequenceMatcher(None, original, modified)
        changes = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                changes.append(
                    {
                        "tag": tag,
                        "original": original[i1:i2],
                        "modified": modified[j1:j2],
                    }
                )

        if not changes:
            return {
                "type": "positive",
                "category": "general",
                "content": "文本无需修改，保持当前写法",
                "action": "reinforce",
                "confidence": 0.6,
                "source": "edit",
                "raw": "",
            }

        # 分析修改类型
        deleted_text = "".join(c["original"] for c in changes if c["tag"] in ("delete", "replace"))
        inserted_text = "".join(c["modified"] for c in changes if c["tag"] in ("insert", "replace"))

        category = "style"
        content = ""
        action = "add"
        confidence = 0.6

        # 大幅删减 → 偏好精简
        if len_ratio < 0.7:
            category = "style"
            content = "偏好精简表达，删除冗余描写"
            confidence = 0.8
        # 大幅增加 → 偏好详细
        elif len_ratio > 1.4:
            category = "style"
            content = "偏好详细描写，增加细节和铺垫"
            confidence = 0.75
        # 对话修改（包含引号变化）
        elif (
            '"' in deleted_text
            or '"' in inserted_text
            or "「" in deleted_text
            or "「" in inserted_text
        ):
            category = "dialogue"
            content = "调整对话表达方式"
            confidence = 0.65
        # 小幅度修改
        else:
            category = "style"
            content = "微调文字表达"
            confidence = 0.5

        return {
            "type": "rule",
            "category": category,
            "content": content,
            "action": action,
            "confidence": confidence,
            "source": "edit",
            "raw": f"修改了 {len(changes)} 处，长度比 {len_ratio:.2f}",
            "changes_count": len(changes),
            "length_ratio": round(len_ratio, 3),
        }

    def batch_extract(self, feedbacks: list[str]) -> list[dict[str, Any]]:
        """批量提取反馈偏好

        Args:
            feedbacks: 反馈文本列表

        Returns:
            偏好字典列表
        """
        results = []
        for fb in feedbacks:
            try:
                pref = self.extract_from_feedback(fb)
                results.append(pref)
            except Exception as e:
                logger.warning(f"[PreferenceExtractor] 批量提取失败: {e}")
                results.append(
                    {
                        "type": "error",
                        "category": "general",
                        "content": fb,
                        "action": "add",
                        "confidence": 0.0,
                        "source": "feedback",
                        "error": str(e),
                    }
                )
        return results

    def generate_kunlun_constraints(self, preferences: list[dict[str, Any]]) -> str:
        """将提取的偏好输出为 KUNLUN.md 约束格式

        Args:
            preferences: 偏好字典列表

        Returns:
            KUNLUN.md 格式的约束文本
        """
        if not preferences:
            return "# 写作约束\n\n（暂无提取到的偏好）\n"

        # 按分类分组
        groups: dict[str, list[dict[str, Any]]] = {}
        for pref in preferences:
            cat = pref.get("category", "general")
            groups.setdefault(cat, []).append(pref)

        category_names = {
            "dialogue": "对话约束",
            "style": "文风约束",
            "pace": "节奏约束",
            "character": "人物约束",
            "plot": "情节约束",
            "structure": "结构约束",
            "general": "通用约束",
        }

        lines = ["# 写作约束（自动提取）", ""]
        lines.append(f"> 共提取 {len(preferences)} 条偏好，来自用户反馈和修改。")
        lines.append("")

        for cat, items in groups.items():
            name = category_names.get(cat, cat)
            lines.append(f"## {name}")
            lines.append("")
            for item in items:
                prefix = "- [保持] " if item.get("action") == "reinforce" else "- [必须] "
                lines.append(f"{prefix}{item.get('content', '')}")
            lines.append("")

        return "\n".join(lines)


# ─── 全局单例 ─────────────────────────────────────────────

_extractor: PreferenceExtractor | None = None


def get_preference_extractor() -> PreferenceExtractor:
    """获取全局偏好提取器实例"""
    global _extractor  # noqa: PLW0603
    if _extractor is None:
        _extractor = PreferenceExtractor()
    return _extractor
