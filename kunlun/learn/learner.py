"""
昆仑创作引擎 — LearnAgent (偏好学习引擎)

职责: 监听7类创作事件，持续学习作者偏好
输出: 50维偏好向量 → 注入 Architect / Writer / StyleEngineer 的 prompt 上下文

设计哲学:
- 渐进学习 (Incremental): 每次事件微量更新，不回溯全量数据
- 维度正交 (Orthogonal): 50维分5组，互不干扰
- 遗忘衰减 (Forgetting): 旧偏好随时间衰减，保持适应性
- 置信度加权 (Confidence): 明确反馈权重 > 隐式信号
"""

from __future__ import annotations

import json
import math
import time
from collections import deque

from loguru import logger

from kunlun.config import settings

# ─── 50维偏好向量的维度定义 ──────────────────────────

PREFERENCE_DIM_LABELS = {
    # 组A: 写作风格 (0-9)
    0: "描述密度_高→低",
    1: "对话占比_高→低",
    2: "心理描写_深→浅",
    3: "环境渲染_浓→淡",
    4: "动作描写_细→略",
    5: "修辞偏好_华丽→质朴",
    6: "节奏偏好_快→慢",
    7: "段落长度_长→短",
    8: "视角偏好_多→单",
    9: "留白偏好_多→少",
    # 组B: 叙事偏好 (10-19)
    10: "弧线推进_激进→保守",
    11: "伏笔密度_高→低",
    12: "悬念频率_高→低",
    13: "回忆插叙_多→少",
    14: "多线叙事_多→单",
    15: "章节钩子强度_强→弱",
    16: "世界观展开_渐进→直给",
    17: "时间线_跳跃→线性",
    18: "POV切换频率_高→低",
    19: "章节独立性_强→弱",
    # 组C: 内容偏好 (20-29)
    20: "战斗篇幅_长→短",
    21: "爽点密度_高→低",
    22: "打脸频率_高→低",
    23: "情感浓度_浓→淡",
    24: "黑暗程度_深→浅",
    25: "幽默元素_多→少",
    26: "知识干货_多→少",
    27: "社会议题_多→少",
    28: "奇遇频率_高→低",
    29: "虐点容忍_高→低",
    # 组D: 结构偏好 (30-39)
    30: "章节字数_长→短",
    31: "场景切换_频→稀",
    32: "开头方式_冲突→铺垫",
    33: "结尾方式_悬念→收束",
    34: "标题风格_抓人→朴实",
    35: "摘要风格_详细→简洁",
    36: "分段频率_高→低",
    37: "对话轮次_多→少",
    38: "战斗章字数_长→短",
    39: "过渡章字数_长→短",
    # 组E: 门禁敏感度 (40-49)
    40: "弧线门禁_严格→宽松",
    41: "信息释放门禁_严格→宽松",
    42: "AI味门禁_严格→宽松",
    43: "爽点间隔门禁_严格→宽松",
    44: "爽点多样性门禁_严格→宽松",
    45: "情感一致性门禁_严格→宽松",
    46: "对话质量门禁_严格→宽松",
    47: "战斗门禁_严格→宽松",
    48: "风格一致性_严格→宽松",
    49: "全局质量_严格→宽松",
}


class PreferenceVector:
    """50维偏好向量 + 置信度 + 最后更新时间"""

    def __init__(self):
        self.dims = [0.0] * 50  # -1.0 ~ +1.0，0=中性
        self.confidence = [0.0] * 50  # 0.0 ~ 1.0，置信度
        self.last_update = [0.0] * 50  # timestamp

    def update(self, dim: int, delta: float, confidence: float) -> None:
        """更新单维偏好（更新前先执行遗忘衰减）"""
        if not (0 <= dim < 50):
            return

        now = time.time()

        # 先执行遗忘衰减（确保旧值随时间衰退，防止偏好固化）
        self.decay(dim)

        # 衰减旧值后叠加新值
        old_val = self.dims[dim]
        old_conf = self.confidence[dim]

        # EMA 更新
        alpha = max(confidence, 0.1)
        self.dims[dim] = old_val * (1 - alpha) + delta * alpha
        self.confidence[dim] = min(old_conf + confidence * 0.1, 1.0)
        self.last_update[dim] = now

    def decay(self, dim: int, rate: float = 0.03) -> None:
        """遗忘衰减：置信度随时间自然降低（24h 后约衰减至 48%）"""
        now = time.time()
        elapsed = now - self.last_update[dim]
        if elapsed > 3600:  # 超过1小时开始衰减
            decay_factor = math.exp(-rate * elapsed / 3600)
            self.confidence[dim] *= decay_factor

    def get_group(self, group: str) -> dict:
        """获取某组偏好摘要"""
        groups = {
            "style": (0, 10),
            "narrative": (10, 10),
            "content": (20, 10),
            "structure": (30, 10),
            "gates": (40, 10),
        }
        start, size = groups.get(group, (0, 50))
        return {
            f"dim_{i}": {
                "label": PREFERENCE_DIM_LABELS.get(i, f"dim_{i}"),
                "value": round(self.dims[i], 3),
                "confidence": round(self.confidence[i], 3),
            }
            for i in range(start, start + size)
        }

    def top_preferences(self, n: int = 10) -> list[dict]:
        """返回置信度最高的 N 个偏好"""
        indexed = [(i, abs(self.dims[i]), self.confidence[i]) for i in range(50)]
        indexed.sort(key=lambda x: x[2], reverse=True)
        return [
            {
                "dim": i,
                "label": PREFERENCE_DIM_LABELS.get(i, f"dim_{i}"),
                "value": round(self.dims[i], 3),
                "confidence": round(conf, 3),
            }
            for i, _, conf in indexed[:n]
            if conf > 0.1
        ]

    def to_prompt_hints(self) -> str:
        """将高置信度偏好转为自然语言提示，注入 LLM prompt"""
        top = self.top_preferences(15)
        if not top:
            return "（尚未积累足够偏好数据，按默认风格写作）"

        lines = ["## 作者偏好 (LearnAgent 推断)", ""]
        for t in top:
            label = t["label"]
            val = t["value"]
            conf = t["confidence"]

            # 拆解 "维度名_极端A→极端B"
            parts = label.split("→", 1)
            dim_name = parts[0].rstrip("_")
            if len(parts) == 2:
                extremes = parts[1]
                # 根据 value 的正负判断偏向哪端
                if val > 0.3:
                    bias = extremes.split("→")[-1] if "→" in extremes else extremes
                    lines.append(f"- {dim_name}: 偏好「{bias}」(置信度 {conf:.0%})")
                elif val < -0.3:
                    bias = extremes.split("→")[0] if "→" in extremes else extremes
                    lines.append(f"- {dim_name}: 偏好「{bias}」(置信度 {conf:.0%})")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "dims": self.dims,
            "confidence": self.confidence,
            "last_update": self.last_update,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PreferenceVector:
        pv = cls()
        if "dims" in data:
            pv.dims = data["dims"][:50]
        if "confidence" in data:
            pv.confidence = data["confidence"][:50]
        if "last_update" in data:
            pv.last_update = data["last_update"][:50]
        return pv


class LearnAgent:
    """
    偏好学习引擎

    事件驱动: 监听创作链路中的7类事件
    持久化: 偏好向量存为 JSON，启动时恢复
    """

    agent_name = "learn_agent"

    # 7类事件
    EVENT_TYPES = [
        "CHAPTER_COMPLETED",
        "AUDIT_PASSED",
        "AUDIT_FAILED",
        "REVISION_APPLIED",
        "AUTHOR_FEEDBACK",
        "READER_FEEDBACK",
        "STYLE_MODIFIED",
    ]

    def __init__(self, book_id: str = "default"):
        self.book_id = book_id
        self.prefs = PreferenceVector()

        # 近期事件缓冲区 (用于批量更新)
        self.event_buffer: deque = deque(maxlen=100)

        # 持久化路径
        self._storage_path = settings.DATA_DIR / "learn" / f"{book_id}_preferences.json"
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 恢复历史偏好
        self._load()

    # ─── 事件监听接口 ─────────────────────────────────

    def on_event(self, event_type: str, payload: dict) -> None:
        """处理创作事件，更新偏好向量"""
        if event_type not in self.EVENT_TYPES:
            logger.warning(f"LearnAgent: 未知事件类型 {event_type}")
            return

        self.event_buffer.append(
            {
                "type": event_type,
                "payload": payload,
                "timestamp": time.time(),
            }
        )

        # 路由到具体处理器
        handler = getattr(self, f"_on_{event_type.lower()}", None)
        if handler:
            handler(payload)
        else:
            self._on_generic(event_type, payload)

        # 定期持久化 (每10个事件)
        if len(self.event_buffer) % 10 == 0:
            self._save()

    # ─── 事件处理器 ───────────────────────────────────

    def _on_chapter_completed(self, payload: dict):
        """章节完成后，从审计结果反推偏好"""
        metrics = payload.get("metrics", {})
        audit = payload.get("audit_result", {})

        # 从通过的审计门禁推断偏好倾向
        for gate, result in audit.get("gates", {}).items():
            if result.get("level") == "PASS":
                continue
            # 失败/警告的门禁 → 强化对应维度的严格度
            gate_dim = self._gate_to_dim(gate)
            if gate_dim is not None:
                self.prefs.update(gate_dim, -0.1, 0.3)

        # 从指标推断
        word_count = metrics.get("word_count", 0)
        if word_count > 0:
            # 章节字数偏好 (dim_30)
            target = 2500
            ratio = word_count / target
            if ratio > 1.3:
                self.prefs.update(30, 0.1, 0.2)  # 偏好长章
            elif ratio < 0.7:
                self.prefs.update(30, -0.1, 0.2)  # 偏好短章

    def _on_audit_passed(self, payload: dict):
        """审计通过 → 降低对应门禁敏感度"""
        gate = payload.get("gate", "")
        gate_dim = self._gate_to_dim(gate)
        if gate_dim is not None:
            self.prefs.update(gate_dim, 0.05, 0.1)  # 略微放松

        # 通过的爽点类型 → 强化该类型偏好
        if gate == "G5" and "distribution" in payload:
            for ptype, count in payload["distribution"].items():
                dim = self._pleasure_to_dim(ptype)
                if dim is not None and count > 0:
                    self.prefs.update(dim, 0.1, 0.3)

    def _on_audit_failed(self, payload: dict):
        """审计失败 → 大幅强化对应门禁敏感度"""
        gate = payload.get("gate", "")
        gate_dim = self._gate_to_dim(gate)
        if gate_dim is not None:
            self.prefs.update(gate_dim, -0.2, 0.6)

        # 失败原因反推
        reason = payload.get("reason", "")
        if "AI味" in reason or "句式" in reason:
            self.prefs.update(42, -0.15, 0.5)
        if "爽点" in reason or "节奏" in reason:
            self.prefs.update(21, 0.1, 0.3)
        if "情绪" in reason or "情感" in reason:
            self.prefs.update(45, -0.15, 0.5)

    def _on_revision_applied(self, payload: dict):
        """修订被应用 → 学习修订方向"""
        changes = payload.get("changes", [])
        for change in changes:
            change_type = change.get("type", "")

            # 风格修改
            if change_type == "replace_conjunction":
                self.prefs.update(5, -0.1, 0.3)  # 偏好质朴
            elif change_type == "adjust_sentence_opening":
                self.prefs.update(9, -0.05, 0.2)
            elif change_type == "paragraph_rhythm":
                self.prefs.update(6, -0.05, 0.2)

            # 篇幅修改
            delta_words = change.get("delta_words", 0)
            if delta_words > 200:
                self.prefs.update(30, 0.05, 0.15)
            elif delta_words < -200:
                self.prefs.update(30, -0.05, 0.15)

    def _on_author_feedback(self, payload: dict):
        """作者主动反馈 → 最高权重更新"""
        feedback = payload.get("feedback", "")
        # rating 验证：类型 + 范围 (-2 ~ +2)
        raw_rating = payload.get("rating", 0)
        if not isinstance(raw_rating, (int, float)):
            logger.warning(f"LearnAgent: rating 类型无效 ({type(raw_rating).__name__})，使用 0")
            raw_rating = 0
        rating = max(-2.0, min(2.0, float(raw_rating)))

        # 解析自然语言反馈
        if rating != 0:
            confidence = abs(rating) / 2.0 * 0.9  # 最高置信度

            if any(kw in feedback for kw in ["太长", "啰嗦", "太啰嗦"]):
                self.prefs.update(30, -0.3, confidence)
            elif any(kw in feedback for kw in ["太短", "不够长", "太简略"]):
                self.prefs.update(30, 0.2, confidence)

            if any(kw in feedback for kw in ["节奏慢", "拖", "太慢"]):
                self.prefs.update(6, 0.2, confidence)  # 偏好更快
            elif any(kw in feedback for kw in ["节奏快", "跳", "太快"]):
                self.prefs.update(6, -0.2, confidence)

            if any(kw in feedback for kw in ["爽点少", "不爽", "不够爽", "太少"]):
                self.prefs.update(21, 0.3, confidence)
            elif any(kw in feedback for kw in ["太爽", "不真实", "离谱"]):
                self.prefs.update(21, -0.2, confidence)

            if any(kw in feedback for kw in ["对话少", "独白多"]):
                self.prefs.update(1, 0.2, confidence)
            elif any(kw in feedback for kw in ["对话多", "话太多"]):
                self.prefs.update(1, -0.2, confidence)

    def _on_reader_feedback(self, payload: dict):
        """读者反馈 → 低权重信号"""
        # 读者反馈权重较低，避免被噪音干扰
        sentiment = payload.get("sentiment", "neutral")
        metrics = payload.get("metrics", {})

        if sentiment == "positive":
            # 正面反馈 → 确认当前偏好方向
            for dim in PREFERENCE_DIM_LABELS:
                if self.prefs.confidence[dim] > 0.3:
                    self.prefs.update(dim, self.prefs.dims[dim] * 0.05, 0.05)

        # 点击率/留存率信号
        ctr = metrics.get("click_through_rate", 0)
        if ctr > 0.15:
            self.prefs.update(15, 0.1, 0.2)  # 强钩子好
        retention = metrics.get("retention_rate", 0)
        if retention > 0.7:
            self.prefs.update(6, 0.05, 0.15)  # 快节奏好

    def _on_style_modified(self, payload: dict):
        """风格被 StyleEngineer 修改 → 记录方向"""
        mod_type = payload.get("modification_type", "")
        count = payload.get("modification_count", 0)

        if mod_type == "ai_conjunction_replacement" and count > 5:
            self.prefs.update(5, -0.1, 0.3)
        elif mod_type == "sentence_opening_diversify" and count > 3:
            self.prefs.update(9, -0.1, 0.25)

    def _on_generic(self, event_type: str, _payload: dict):
        """未分类事件的通用处理"""
        logger.debug(f"LearnAgent: generic handle {event_type}")

    # ─── 维度映射 ─────────────────────────────────────

    def _gate_to_dim(self, gate: str) -> int | None:
        """审计门禁 → 偏好维度"""
        # 支持 "G1" / "G1_arc" / "G3_ai" 等格式
        gate_code = gate[:2] if len(gate) >= 2 and gate[0] == "G" else gate
        mapping = {
            "G1": 40,  # arc_deviation
            "G2": 41,  # info_release
            "G3": 42,  # ai_detection
            "G4": 43,  # pleasure_gap
            "G5": 44,  # pleasure_diversity
            "G6": 45,  # emotion
            "G7": 46,  # dialogue
            "G8": 47,  # battle
        }
        return mapping.get(gate_code)

    def _pleasure_to_dim(self, ptype: str) -> int | None:
        """爽点类型 → 内容偏好维度"""
        mapping = {
            "slap_face": 22,
            "level_up": 28,
            "treasure": 28,
            "revenge": 24,
            "revelation": 16,
            "romance": 23,
            "show_off": 22,
        }
        return mapping.get(ptype)

    # ─── 持久化 ───────────────────────────────────────

    def _save(self) -> None:
        """持久化偏好向量到 JSON"""
        try:
            data = {
                "book_id": self.book_id,
                "preferences": self.prefs.to_dict(),
                "event_count": len(self.event_buffer),
                "updated_at": time.time(),
            }
            self._storage_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"LearnAgent: 保存偏好失败 {e}")

    def _load(self):
        """从 JSON 恢复偏好向量"""
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text())
                self.prefs = PreferenceVector.from_dict(data.get("preferences", {}))
                logger.info(
                    f"LearnAgent: 已恢复 {self.book_id} 的偏好 "
                    f"({sum(1 for c in self.prefs.confidence if c > 0.1)} 高置信维度)"
                )
        except Exception as e:
            logger.warning(f"LearnAgent: 恢复偏好失败 {e}, 使用空白向量")

    def save(self) -> None:
        """公开保存接口"""
        self._save()

    def get_prompt_hints(self) -> str:
        """获取可注入 LLM prompt 的偏好提示"""
        return self.prefs.to_prompt_hints()


# ─── 全局实例管理 ────────────────────────────────────

_learners: dict[str, LearnAgent] = {}


def get_learner(book_id: str = "default") -> LearnAgent:
    """获取或创建 LearnAgent 实例"""
    if book_id not in _learners:
        _learners[book_id] = LearnAgent(book_id)
    return _learners[book_id]


def on_creation_event(book_id: str, event_type: str, payload: dict) -> None:
    """便捷接口：记录创作事件并更新偏好"""
    learner = get_learner(book_id)
    learner.on_event(event_type, payload)
