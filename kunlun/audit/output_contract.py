"""
昆仑创作引擎 — 输出契约验证器 (Output Contract Validator)

灵感来源:
  - SpecForge: 规范驱动的内容生成
  - Novel-OS: 输出契约 [STATE_UPDATE] 块机制
  - InkOS: Zod Schema 校验

核心机制:
  Agent 输出必须遵循预定义的 JSON Schema，
  Schema 校验失败则拒绝更新 truth files，
  防止坏数据滚雪球。

使用方式:
    validator = OutputContractValidator()
    report = validator.validate("chapter_summary", {
        "chapter": 1,
        "summary": "本章讲述了...",
        "characters": ["王林"],
    })
    if report.valid:
        truth_manager.save("chapter_summaries", data)
    else:
        logger.warning(f"输出契约失败: {report.errors}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class FieldSchema:
    """字段定义"""

    name: str
    type: str  # str / int / float / list / dict / list[str] / optional
    description: str = ""
    required: bool = True
    min_length: int = 0
    max_length: int = 0
    enum: list | None = None  # 枚举值限制


@dataclass
class OutputSchema:
    """输出 Schema 定义"""

    name: str
    fields: list[FieldSchema] = field(default_factory=list)
    description: str = ""


@dataclass
class ValidationReport:
    """校验报告"""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── 预定义的输出 Schema ──────────────────────────────

OUTPUT_SCHEMAS: dict[str, OutputSchema] = {
    "chapter_summary": OutputSchema(
        "chapter_summary",
        [
            FieldSchema("chapter", "int", "章节号", min_length=1),
            FieldSchema("title", "str", "章节标题", min_length=1, max_length=100),
            FieldSchema("summary", "str", "章节摘要", min_length=10, max_length=2000),
            FieldSchema("characters", "list[str]", "本章出场角色"),
            FieldSchema("key_events", "list[str]", "关键事件"),
        ],
        "章节摘要输出",
    ),
    "character_update": OutputSchema(
        "character_update",
        [
            FieldSchema("character_uid", "str", "角色ID", min_length=1),
            FieldSchema("name", "str", "角色名", min_length=1, max_length=50),
            FieldSchema("emotion", "str", "当前情绪"),
            FieldSchema("location", "str", "当前位置"),
            FieldSchema("realm", "str", "当前境界/等级", required=False),
        ],
        "角色状态更新",
    ),
    "foreshadowing": OutputSchema(
        "foreshadowing",
        [
            FieldSchema("name", "str", "伏笔名", min_length=1, max_length=100),
            FieldSchema("priority", "str", "优先级", enum=["high", "medium", "low"]),
            FieldSchema("expectedRevealChapter", "int", "预计揭示章节", min_length=1),
            FieldSchema("description", "str", "伏笔描述", min_length=5),
        ],
        "伏笔定义",
    ),
    "pleasure_point": OutputSchema(
        "pleasure_point",
        [
            FieldSchema("chapter", "int", "章节号", min_length=1),
            FieldSchema(
                "type",
                "str",
                "爽点类型",
                enum=[
                    "face_slap",
                    "power_up",
                    "treasure",
                    "revenge",
                    "reveal",
                    "conquest",
                    "romance",
                    "comedy",
                    "epic",
                ],
            ),
            FieldSchema("strength", "int", "爽点强度(1-10)", min_length=1, max_length=10),
            FieldSchema("description", "str", "爽点描述", min_length=5, max_length=500),
        ],
        "爽点记录",
    ),
    "pipeline_result": OutputSchema(
        "pipeline_result",
        [
            FieldSchema("success", "bool", "是否成功"),
            FieldSchema("pipeline_id", "str", "管线ID"),
            FieldSchema("book_id", "str", "作品ID"),
            FieldSchema("chapter", "int", "章节号"),
            FieldSchema("draft", "str", "正文", min_length=50),
            FieldSchema("steps", "list[str]", "执行步骤"),
        ],
        "管线执行结果",
    ),
}


class OutputContractValidator:
    """
    输出契约验证器

    Agent 输出的结构化数据必须经过此验证器校验，
    通过后才能写入 truth files 或进入下一管线步骤。
    """

    def __init__(self):
        self.schemas = OUTPUT_SCHEMAS

    def validate(self, schema_name: str, data: dict) -> ValidationReport:
        """校验数据是否符合指定 Schema"""
        schema = self.schemas.get(schema_name)
        if not schema:
            return ValidationReport(valid=True, warnings=[f"未知 Schema: {schema_name}"])

        errors: list[str] = []
        warnings: list[str] = []

        for fld in schema.fields:
            value = data.get(fld.name)

            # 必需字段检查
            if fld.required and value is None:
                errors.append(f"{fld.name}: 缺少必需字段")
                continue

            if value is None:
                continue  # 可选字段且未提供

            # 类型检查
            type_ok = self._check_type(value, fld.type)
            if not type_ok:
                errors.append(
                    f"{fld.name}: 类型错误 (期望 {fld.type}, 实际 {type(value).__name__})"
                )
                continue

            # 长度/范围检查
            if isinstance(value, str):
                if fld.min_length and len(value) < fld.min_length:
                    errors.append(f"{fld.name}: 过短 ({len(value)} < {fld.min_length})")
                if fld.max_length and len(value) > fld.max_length:
                    errors.append(f"{fld.name}: 过长 ({len(value)} > {fld.max_length})")

            if isinstance(value, (int, float)):
                if fld.min_length and value < fld.min_length:
                    errors.append(f"{fld.name}: 过小 ({value} < {fld.min_length})")
                if fld.max_length and value > fld.max_length:
                    errors.append(f"{fld.name}: 过大 ({value} > {fld.max_length})")

            if isinstance(value, list) and fld.min_length and len(value) < fld.min_length:
                errors.append(f"{fld.name}: 列表过短 ({len(value)} < {fld.min_length})")

            # 枚举检查
            if fld.enum and value not in fld.enum:
                errors.append(
                    f"{fld.name}: 值 '{value}' 不在枚举 [{', '.join(map(str, fld.enum))}] 中"
                )

        return ValidationReport(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "list[str]": lambda v: isinstance(v, list) and all(isinstance(i, str) for i in v),
            "list[dict]": lambda v: isinstance(v, list) and all(isinstance(i, dict) for i in v),
        }
        checker: object = type_map.get(expected_type)
        if checker is None:
            return True
        if isinstance(checker, type):
            return isinstance(value, checker)
        if callable(checker):
            return checker(value)
        return False

    def safe_update(self, schema_name: str, data: dict, update_fn) -> tuple[bool, dict | None]:
        """安全更新：校验通过后执行更新函数

        Args:
            schema_name: Schema 名称
            data: 待校验数据
            update_fn: 校验通过后执行的回调(data) → dict

        Returns:
            (success, result)
        """
        report = self.validate(schema_name, data)
        if not report.valid:
            logger.warning(f"[OutputContract] {schema_name} 校验失败: {report.errors}")
            return False, {"errors": report.errors}
        return True, update_fn(data)

    def get_schema_json(self, schema_name: str) -> str:
        """获取 Schema 的 JSON 描述（可用于注入 LLM prompt）"""
        schema = self.schemas.get(schema_name)
        if not schema:
            return "{}"
        lines = ["{"]
        for i, f in enumerate(schema.fields):
            req = "必需" if f.required else "可选"
            extra = ""
            if f.enum:
                extra = f", 可选值: {f.enum}"
            if f.min_length:
                extra += f", 最小: {f.min_length}"
            if f.max_length:
                extra += f", 最大: {f.max_length}"
            comma = "," if i < len(schema.fields) - 1 else ""
            lines.append(f'  "{f.name}": {f.type} ({req}{extra}){comma}')
        lines.append("}")
        return "\n".join(lines)


# 全局单例
output_contract = OutputContractValidator()
