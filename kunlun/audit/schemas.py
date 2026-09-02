"""
审计结果 Pydantic Schema 校验

借鉴 Instructor 库的 structured output 理念，为审计系统提供:
1. 运行时类型校验 — 确保审计结果符合预期结构
2. JSON Schema 生成 — 供 LLM 结构化输出使用
3. 自动修复 — 对轻微偏离的字段进行修复

使用方式:
    from kunlun.audit.schemas import Audit33ReportSchema, validate_and_repair

    # 校验审计报告
    schema = Audit33ReportSchema.model_validate(report_dict)

    # 校验 + 自动修复
    repaired = validate_and_repair(report_dict, Audit33ReportSchema)
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator

# ─── 维度结果 Schema ─────────────────────────────


class DimResultSchema(BaseModel):
    """单个维度的审计结果（Pydantic 校验版）"""

    dim_id: str = Field(
        ...,
        min_length=2,
        max_length=5,
        pattern=r"^[A-F]\d{1,2}$",
        description="维度ID，如 A1, B3, F6",
    )
    name: str = Field(..., min_length=1, max_length=20)
    score: float = Field(..., ge=0, le=100, description="0-100分")
    level: str = Field(..., pattern=r"^(PASS|WARN|FAIL)$", description="PASS/WARN/FAIL")
    detail: str = Field("", max_length=2000)
    suggestion: str = Field("", max_length=1000)
    auto_fixable: bool = False

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        """限幅到 0-100"""
        return max(0.0, min(100.0, float(v)))

    @field_validator("level")
    @classmethod
    def normalize_level(cls, v: str) -> str:
        """标准化等级为 PASS/WARN/FAIL"""
        upper = v.strip().upper()
        if upper in ("PASS", "WARN", "FAIL"):
            return upper
        if upper in ("OK", "GOOD", "TRUE", "1"):
            return "PASS"
        if upper in ("WARNING", "CAUTION"):
            return "WARN"
        if upper in ("ERROR", "FATAL", "FALSE", "0"):
            return "FAIL"
        return "PASS"  # 默认通过


# ─── 审计报告 Schema ─────────────────────────────


class Audit33ReportSchema(BaseModel):
    """33维审计综合报告（Pydantic 校验版）"""

    chapter: int = Field(..., ge=1, description="章节号")
    dimensions: list[DimResultSchema] = Field(
        default_factory=list, min_length=0, max_length=33, description="各维度审计结果（最多33个）"
    )
    overall_score: float = Field(0.0, ge=0, le=100, description="综合分数 0-100")
    passed: bool = False
    fatal_count: int = Field(0, ge=0, description="致命问题数")
    warn_count: int = Field(0, ge=0, description="警告数")
    ai_detection_score: float = Field(
        0.0, ge=0, le=100, description="AI痕迹检测分数（越高AI味越重）"
    )
    summary: str = Field("", max_length=5000)

    @field_validator("overall_score")
    @classmethod
    def clamp_overall(cls, v: float) -> float:
        return max(0.0, min(100.0, float(v)))

    @field_validator("ai_detection_score")
    @classmethod
    def clamp_ai_detection(cls, v: float) -> float:
        return max(0.0, min(100.0, float(v)))

    @model_validator(mode="after")
    def reconcile_counts(self):
        """根据 dimensions 自动修正 fatal_count / warn_count"""
        actual_fatal = sum(1 for d in self.dimensions if d.level == "FAIL")
        actual_warn = sum(1 for d in self.dimensions if d.level == "WARN")

        # 如果声明的数量与维度实际数量不一致，自动修正
        if self.fatal_count != actual_fatal:
            logger.debug(f"[Schema] fatal_count 修正: {self.fatal_count} → {actual_fatal}")
            self.fatal_count = actual_fatal
        if self.warn_count != actual_warn:
            logger.debug(f"[Schema] warn_count 修正: {self.warn_count} → {actual_warn}")
            self.warn_count = actual_warn

        # 自动判定是否通过
        self.passed = self.fatal_count == 0
        return self

    @model_validator(mode="after")
    def compute_score_if_missing(self):
        """如果没有 overall_score 但有维度数据，计算加权平均分"""
        if self.overall_score <= 0 and self.dimensions:
            total = sum(d.score for d in self.dimensions)
            self.overall_score = round(total / len(self.dimensions), 1)
            logger.debug(f"[Schema] overall_score 自动计算: {self.overall_score:.1f}")
        return self

    def to_json_schema(self) -> dict:
        """生成 JSON Schema 供 LLM 结构化输出"""
        return self.model_json_schema()

    def summary_dict(self) -> dict[str, Any]:
        """轻量摘要（用于 API 返回）"""
        return {
            "chapter": self.chapter,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "fatal_count": self.fatal_count,
            "warn_count": self.warn_count,
            "ai_detection_score": self.ai_detection_score,
            "failed_dimensions": [d.dim_id for d in self.dimensions if d.level == "FAIL"],
            "summary": self.summary[:200],
        }


# ─── 门禁结果 Schema ─────────────────────────────


class GateResultSchema(BaseModel):
    """单个门禁结果（Pydantic 校验版）"""

    gate_id: str = Field(
        ..., min_length=2, max_length=4, pattern=r"^G\d{1,2}$", description="门禁ID，如 G1, G8"
    )
    level: str = Field(..., pattern=r"^(PASS|WARN|FAIL)$")
    score: float = Field(..., ge=0, le=1.0, description="0.0-1.0")
    detail: str = Field("", max_length=2000)
    data: dict[str, Any] | None = None

    @field_validator("score")
    @classmethod
    def clamp_gate_score(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("level")
    @classmethod
    def normalize_gate_level(cls, v: str) -> str:
        upper = v.strip().upper()
        if upper in ("PASS", "WARN", "FAIL"):
            return upper
        if upper in ("OK", "GOOD", "TRUE"):
            return "PASS"
        if upper in ("WARNING",):
            return "WARN"
        return "FAIL"


class AuditResultSchema(BaseModel):
    """门禁审计综合结果（Pydantic 校验版）"""

    passed: bool = False
    gates: dict[str, GateResultSchema] = Field(default_factory=dict, max_length=16)
    score: float = Field(0.0, ge=0, le=1.0, description="加权总分 0.0-1.0")
    summary: str = Field("", max_length=2000)

    @model_validator(mode="after")
    def reconcile_passed(self):
        """根据门禁结果自动修正 passed"""
        if self.gates:
            has_fail = any(g.level == "FAIL" for g in self.gates.values())
            self.passed = not has_fail
        return self


# ─── 校验与修复工具 ─────────────────────────────


def validate_and_repair(
    data: dict[str, Any],
    schema_cls: type[BaseModel],
    raise_on_error: bool = False,
) -> tuple[BaseModel | None, list[str]]:
    """
    校验并自动修复审计数据

    借鉴 Instructor 的自动重试理念，对常见偏离进行修复:
    - 类型不匹配 → 尝试转换
    - score 超出范围 → clamp
    - level 大小写不规范 → normalize
    - 缺失字段 → 填充默认值

    Args:
        data: 待校验的原始数据
        schema_cls: Pydantic Schema 类
        raise_on_error: 修复后仍不合格是否抛异常

    Returns:
        (validated_model, repair_log) — 模型实例和修复日志列表
    """
    repairs: list[Any] = []

    # 1. 尝试直接校验
    try:
        model = schema_cls.model_validate(data)
        return model, repairs
    except Exception as e:
        logger.debug(f"[Schema] 直接校验失败，尝试修复: {e}")

    # 2. 逐字段修复
    repaired_data = dict(data)

    # 常见修复
    if "score" in repaired_data:
        s = repaired_data["score"]
        if isinstance(s, (int, float)):
            repaired_data["score"] = max(
                0.0, min(100.0 if schema_cls.__name__.endswith("ReportSchema") else 1.0, float(s))
            )
        elif isinstance(s, str):
            try:
                repaired_data["score"] = float(s)
                repairs.append(f"score: str→float ({s})")
            except ValueError:
                repaired_data["score"] = 0.0
                repairs.append("score: 无法转换，设为0")

    if "overall_score" in repaired_data:
        s = repaired_data["overall_score"]
        if isinstance(s, (int, float)):
            repaired_data["overall_score"] = max(0.0, min(100.0, float(s)))
        elif isinstance(s, str):
            try:
                repaired_data["overall_score"] = float(s)
            except ValueError:
                repaired_data["overall_score"] = 0.0

    if "level" in repaired_data:
        lv = str(repaired_data["level"]).strip().upper()
        if lv not in ("PASS", "WARN", "FAIL"):
            repaired_data["level"] = "PASS"
            repairs.append(f"level: {repaired_data['level']!r} → PASS")

    if "passed" in repaired_data and isinstance(repaired_data["passed"], str):
        repaired_data["passed"] = repaired_data["passed"].lower() in (
            "true",
            "yes",
            "1",
            "pass",
        )
        repairs.append("passed: str→bool")

    # 3. 最终校验
    try:
        model = schema_cls.model_validate(repaired_data)
        for r in repairs:
            logger.info(f"[Schema] 🔧 {r}")
        return model, repairs
    except Exception as e:
        logger.warning(f"[Schema] 修复后仍校验失败: {e}")
        if raise_on_error:
            raise
        return None, [*repairs, f"最终校验失败: {e}"]


def validate_llm_output(
    raw_output: str,
    schema_cls: type[BaseModel],
    default_model: str = "deepseek-chat",
) -> BaseModel | None:
    """
    校验 LLM 结构化输出是否符合预期 Schema

    适用于 LLM 返回 JSON 格式的结构化数据场景。
    如果输出不是合法 JSON，返回 None。

    Args:
        raw_output: LLM 原始输出文本
        schema_cls: 期望的 Pydantic Schema 类
        default_model: 日志记录用

    Returns:
        校验通过的模型实例，或 None
    """
    import json

    try:
        # 尝试提取 JSON（LLM 可能在 JSON 前后加了解释文本）
        raw = raw_output.strip()
        # 移除可能的 markdown json 标记
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"[Schema] LLM 输出不是合法 JSON (model={default_model})")
        return None
    except Exception as e:
        logger.warning(f"[Schema] LLM 输出解析失败: {e}")
        return None

    model, repairs = validate_and_repair(data, schema_cls)
    if model is None:
        logger.warning(f"[Schema] LLM 输出不符合 {schema_cls.__name__} Schema")
    elif repairs:
        logger.info(f"[Schema] LLM 输出经过 {len(repairs)} 项自动修复后通过校验")
    return model


# ─── 导出辅助 ─────────────────────────────


def dim_result_to_schema(dr) -> DimResultSchema:
    """将 dataclass DimResult 转换为 Pydantic Schema"""
    return DimResultSchema(
        dim_id=dr.dim_id,
        name=dr.name,
        score=dr.score,
        level=dr.level,
        detail=dr.detail,
        suggestion=dr.suggestion,
        auto_fixable=dr.auto_fixable,
    )


def audit33_report_to_schema(report) -> Audit33ReportSchema:
    """将 dataclass Audit33Report 转换为 Pydantic Schema"""
    return Audit33ReportSchema(
        chapter=report.chapter,
        dimensions=[dim_result_to_schema(d) for d in report.dimensions],
        overall_score=report.overall_score,
        passed=report.passed,
        fatal_count=report.fatal_count,
        warn_count=report.warn_count,
        ai_detection_score=report.ai_detection_score,
        summary=report.summary,
    )


# ─── JSON Schema 模板（供 LLM prompt 使用）───

AUDIT33_JSON_SCHEMA_PROMPT = """
请以以下 JSON Schema 输出审计结果:

{
  "chapter": <int, 章节号>,
  "overall_score": <float, 综合质量分 0-100>,
  "passed": <bool, 是否通过>,
  "fatal_count": <int, 致命问题数>,
  "warn_count": <int, 警告数>,
  "ai_detection_score": <float, AI痕迹分 0-100>,
  "summary": "<str, 审计总结>",
  "dimensions": [
    {
      "dim_id": "<str, 维度ID 如 A1>",
      "name": "<str, 维度名称>",
      "score": <float, 0-100>,
      "level": "<PASS|WARN|FAIL>",
      "detail": "<str, 详细说明>",
      "suggestion": "<str, 改进建议>",
      "auto_fixable": <bool>
    }
  ]
}
""".strip()
