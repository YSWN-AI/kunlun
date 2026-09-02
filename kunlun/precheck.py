"""
昆仑创作引擎 — 确定性预检查规则

灵感来源: InkOS 11条写后验证规则 + Novel-OS 9项检查

核心机制:
  - 零LLM成本的确定性检查
  - 在执行核心任务前验证输入
  - 提前识别并拦截潜在错误

检查规则清单:
  1. R1: 输入格式验证
  2. R2: 参数范围校验
  3. R3: 资源配额检查
  4. R4: 安全风险检测
  5. R5: 内容合规性检查
  6. R6: 状态一致性验证
  7. R7: 上下文完整性检查
  8. R8: 输出契约验证
  9. R9: 性能预估检查
  10. R10: 降级模式检测
  11. R11: 业务规则验证

使用方式:
    from kunlun.precheck import PreCheckManager, PreCheckResult

    manager = PreCheckManager()
    result = manager.run_all_checks({
        "book_id": "test_book",
        "chapter": 1,
        "mode": "gacha_parallel_3"
    })

    if not result.passed:
        print(f"预检查失败: {result.errors}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.config import settings


class CheckLevel(Enum):
    """检查级别"""

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    BLOCK = "BLOCK"  # 阻止执行


@dataclass
class CheckResult:
    """单条检查结果"""

    rule_id: str
    level: CheckLevel
    passed: bool
    message: str
    details: dict | None = None


@dataclass
class PreCheckResult:
    """预检查汇总结果"""

    passed: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def errors(self) -> list[str]:
        """获取所有错误消息"""
        return [c.message for c in self.checks if c.level in (CheckLevel.ERROR, CheckLevel.BLOCK)]

    @property
    def warnings(self) -> list[str]:
        """获取所有警告消息"""
        return [c.message for c in self.checks if c.level == CheckLevel.WARN]


class PreCheckRule:
    """预检查规则基类"""

    rule_id: str = "R0"
    description: str = "未命名规则"
    level: CheckLevel = CheckLevel.ERROR

    def check(self, context: dict[str, Any]) -> CheckResult:
        """执行检查"""
        raise NotImplementedError


class R1InputFormat(PreCheckRule):
    """R1: 输入格式验证"""

    rule_id = "R1"
    description = "输入格式验证"

    def check(self, context: dict[str, Any]) -> CheckResult:
        errors = []

        # book_id 格式检查
        book_id = context.get("book_id", "")
        if book_id and not re.match(r"^[a-zA-Z0-9_-]+$", book_id):
            errors.append(f"book_id格式无效: {book_id}")

        # chapter 范围检查
        chapter = context.get("chapter", 0)
        if isinstance(chapter, int) and chapter < 0:
            errors.append(f"章节号不能为负数: {chapter}")

        # mode 有效值检查
        valid_modes = ["gacha_parallel_3", "gacha_cheap_2", "gacha_ultimate_5", "single_fix"]
        mode = context.get("mode", "")
        if mode and mode not in valid_modes:
            errors.append(f"不支持的模式: {mode}")

        if errors:
            return CheckResult(
                rule_id=self.rule_id,
                level=CheckLevel.BLOCK,
                passed=False,
                message=f"输入格式验证失败: {', '.join(errors)}",
            )
        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="输入格式验证通过"
        )


class R2ParamRange(PreCheckRule):
    """R2: 参数范围校验"""

    rule_id = "R2"
    description = "参数范围校验"

    def check(self, context: dict[str, Any]) -> CheckResult:
        warnings = []

        # temperature 范围
        temp = context.get("temperature", 0.7)
        if isinstance(temp, (int, float)):
            if temp < 0:
                warnings.append(f"temperature 过低: {temp}")
            elif temp > 2.0:
                warnings.append(f"temperature 过高: {temp}")

        # max_tokens 范围
        max_tokens = context.get("max_tokens", 2048)
        if isinstance(max_tokens, int):
            if max_tokens < 100:
                warnings.append(f"max_tokens 过小: {max_tokens}")
            elif max_tokens > 32000:
                warnings.append(f"max_tokens 过大: {max_tokens}")

        # chapter_type 有效值
        valid_types = ["normal", "battle", "transition", "exposition"]
        chapter_type = context.get("chapter_type", "")
        if chapter_type and chapter_type not in valid_types:
            warnings.append(f"不支持的章节类型: {chapter_type}")

        if warnings:
            return CheckResult(
                rule_id=self.rule_id,
                level=CheckLevel.WARN,
                passed=True,
                message=f"参数范围警告: {', '.join(warnings)}",
            )
        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="参数范围校验通过"
        )


class R3ResourceQuota(PreCheckRule):
    """R3: 资源配额检查"""

    rule_id = "R3"
    description = "资源配额检查"

    def check(self, _context: dict[str, Any]) -> CheckResult:

        # 检查磁盘空间
        try:
            import shutil

            _, free_space, _ = shutil.disk_usage(str(settings.DATA_DIR))
            if free_space < 1024 * 1024 * 1024:  # 小于1GB
                return CheckResult(
                    rule_id=self.rule_id,
                    level=CheckLevel.WARN,
                    passed=True,
                    message=f"磁盘空间不足: {free_space / (1024**3):.2f}GB 剩余",
                )
        except Exception as e:
            logger.debug(f"磁盘空间检查失败: {e}")

        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="资源配额检查通过"
        )


class R4SecurityRisk(PreCheckRule):
    """R4: 安全风险检测"""

    rule_id = "R4"
    description = "安全风险检测"

    # 潜在危险模式
    DANGEROUS_PATTERNS = [
        r";.*rm\s+-rf",
        r";.*del\s+/f",
        r"eval\(",
        r"exec\(",
        r"system\(",
        r"os\.system",
        r"subprocess",
        r"<script",
        r"onclick",
        r"javascript:",
    ]

    def check(self, context: dict[str, Any]) -> CheckResult:
        # 检查所有字符串字段
        for key, value in context.items():
            if isinstance(value, str):
                for pattern in self.DANGEROUS_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        return CheckResult(
                            rule_id=self.rule_id,
                            level=CheckLevel.BLOCK,
                            passed=False,
                            message=f"检测到潜在安全风险: {key} 字段包含危险内容",
                        )

        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="安全风险检测通过"
        )


class R5ContentCompliance(PreCheckRule):
    """R5: 内容合规性检查"""

    rule_id = "R5"
    description = "内容合规性检查"

    # 违禁词类别
    FORBIDDEN_CATEGORIES = {
        "politics": ["敏感词1", "敏感词2"],
        "violence": ["血腥", "暴力", "屠杀"],
        "pornography": ["色情", "淫秽"],
        "drugs": ["毒品", "鸦片", "大麻"],
        "fraud": ["诈骗", "传销"],
    }

    def check(self, context: dict[str, Any]) -> CheckResult:
        # 检查所有文本内容
        text_fields = [
            value for value in context.values() if isinstance(value, str) and len(value) > 10
        ]

        violations: list[str] = []
        for category, words in self.FORBIDDEN_CATEGORIES.items():
            for text in text_fields:
                violations.extend(f"{category}: {word}" for word in words if word in text)

        if violations:
            return CheckResult(
                rule_id=self.rule_id,
                level=CheckLevel.BLOCK,
                passed=False,
                message=f"内容合规性检查失败: 检测到违禁内容 ({', '.join(violations)})",
            )
        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="内容合规性检查通过"
        )


class R6StateConsistency(PreCheckRule):
    """R6: 状态一致性验证"""

    rule_id = "R6"
    description = "状态一致性验证"

    def check(self, context: dict[str, Any]) -> CheckResult:
        book_id = context.get("book_id")
        chapter = context.get("chapter")

        if book_id and chapter:
            # 检查章节号是否合理（不能超过已存在章节过多）
            try:
                # 检查是否有后续章节已生成
                chapters_dir = settings.DATA_DIR / "published" / book_id
                if chapters_dir.exists():
                    existing = []
                    for f in chapters_dir.glob("ch*.txt"):
                        match = re.match(r"ch(\d+)\.txt", f.name)
                        if match:
                            existing.append(int(match.group(1)))

                    if existing:
                        max_chapter = max(existing)
                        # 如果当前章节比最大已生成章节大太多，可能有问题
                        if chapter > max_chapter + 5:
                            return CheckResult(
                                rule_id=self.rule_id,
                                level=CheckLevel.WARN,
                                passed=True,
                                message=(
                                    f"章节跳跃过大: 当前最大章节 {max_chapter}, 请求章节 {chapter}"
                                ),
                            )
            except Exception as e:
                logger.debug(f"状态一致性检查失败: {e}")

        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="状态一致性验证通过"
        )


class R7ContextIntegrity(PreCheckRule):
    """R7: 上下文完整性检查"""

    rule_id = "R7"
    description = "上下文完整性检查"

    def check(self, context: dict[str, Any]) -> CheckResult:
        required_fields = ["book_id", "chapter"]

        missing = [f for f in required_fields if f not in context or not context[f]]

        if missing:
            return CheckResult(
                rule_id=self.rule_id,
                level=CheckLevel.BLOCK,
                passed=False,
                message=f"必要字段缺失: {', '.join(missing)}",
            )
        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="上下文完整性检查通过"
        )


class R8OutputContract(PreCheckRule):
    """R8: 输出契约验证"""

    rule_id = "R8"
    description = "输出契约验证"

    def check(self, context: dict[str, Any]) -> CheckResult:
        # 检查输出格式要求
        output_format = context.get("output_format", "txt")
        valid_formats = ["txt", "md", "html", "epub", "pdf"]

        if output_format and output_format not in valid_formats:
            return CheckResult(
                rule_id=self.rule_id,
                level=CheckLevel.WARN,
                passed=True,
                message=f"不支持的输出格式: {output_format}",
            )

        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="输出契约验证通过"
        )


class R9PerformanceEstimate(PreCheckRule):
    """R9: 性能预估检查"""

    rule_id = "R9"
    description = "性能预估检查"

    def check(self, context: dict[str, Any]) -> CheckResult:
        mode = context.get("mode", "gacha_parallel_3")

        # 根据模式预估耗时
        time_estimates = {
            "single_fix": "约10-30秒",
            "gacha_cheap_2": "约30-60秒",
            "gacha_parallel_3": "约60-120秒",
            "gacha_ultimate_5": "约120-300秒",
        }

        estimate = time_estimates.get(mode, "不确定")

        return CheckResult(
            rule_id=self.rule_id,
            level=CheckLevel.INFO,
            passed=True,
            message=f"性能预估: {mode} 模式预计耗时 {estimate}",
        )


class R10DegradationMode(PreCheckRule):
    """R10: 降级模式检测"""

    rule_id = "R10"
    description = "降级模式检测"

    def check(self, _context: dict[str, Any]) -> CheckResult:
        warnings = []

        # 检查API密钥配置
        if not settings.deepseek_api_key:
            warnings.append("DeepSeek API Key 未配置")
        if not settings.openai_api_key and not settings.anthropic_api_key:
            warnings.append("至少需要配置一个LLM API Key")

        # 检查依赖服务状态
        try:
            from kunlun.kg.client import kg_client

            kg_status = kg_client.health_check()
            if "error" in kg_status:
                warnings.append(f"知识图谱服务异常: {kg_status['error']}")
        except Exception as e:
            warnings.append(f"知识图谱初始化失败: {e}")

        if warnings:
            return CheckResult(
                rule_id=self.rule_id,
                level=CheckLevel.WARN,
                passed=True,
                message=f"降级模式检测: {', '.join(warnings)}",
            )
        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="所有依赖服务正常"
        )


class R11BusinessRules(PreCheckRule):
    """R11: 业务规则验证"""

    rule_id = "R11"
    description = "业务规则验证"

    def check(self, context: dict[str, Any]) -> CheckResult:
        book_id = context.get("book_id")
        chapter = context.get("chapter")

        # 检查章节顺序（不能跳过多章）
        if book_id and chapter and isinstance(chapter, int):
            try:
                # 检查是否存在中间章节缺失
                chapters_dir = settings.DATA_DIR / "published" / book_id
                if chapters_dir.exists():
                    existing = []
                    for f in chapters_dir.glob("ch*.txt"):
                        match = re.match(r"ch(\d+)\.txt", f.name)
                        if match:
                            existing.append(int(match.group(1)))

                    if existing:
                        expected_chapter = max(existing) + 1
                        if chapter < expected_chapter:
                            return CheckResult(
                                rule_id=self.rule_id,
                                level=CheckLevel.WARN,
                                passed=True,
                                message=f"建议按顺序生成: 当前应生成第 {expected_chapter} 章",
                            )
            except Exception as e:
                logger.debug(f"业务规则检查失败: {e}")

        return CheckResult(
            rule_id=self.rule_id, level=CheckLevel.INFO, passed=True, message="业务规则验证通过"
        )


class PreCheckManager:
    """预检查管理器"""

    def __init__(self):
        self.rules = [
            R1InputFormat(),
            R2ParamRange(),
            R3ResourceQuota(),
            R4SecurityRisk(),
            R5ContentCompliance(),
            R6StateConsistency(),
            R7ContextIntegrity(),
            R8OutputContract(),
            R9PerformanceEstimate(),
            R10DegradationMode(),
            R11BusinessRules(),
        ]

    def run_all_checks(self, context: dict[str, Any]) -> PreCheckResult:
        """运行所有检查"""
        results = []
        all_passed = True

        for rule in self.rules:
            try:
                result = rule.check(context)
                results.append(result)

                # BLOCK级别直接终止
                if result.level == CheckLevel.BLOCK:
                    all_passed = False
                    break

                # ERROR级别标记失败但继续检查
                if not result.passed:
                    all_passed = False
            except Exception as e:
                logger.error(f"预检查规则 {rule.rule_id} 执行失败: {e}")
                results.append(
                    CheckResult(
                        rule_id=rule.rule_id,
                        level=CheckLevel.ERROR,
                        passed=False,
                        message=f"规则执行异常: {e}",
                    )
                )

        return PreCheckResult(passed=all_passed, checks=results)

    def run_selected_checks(self, context: dict[str, Any], rule_ids: list[str]) -> PreCheckResult:
        """运行指定的检查"""
        results = []
        all_passed = True

        for rule in self.rules:
            if rule.rule_id in rule_ids:
                try:
                    result = rule.check(context)
                    results.append(result)

                    if result.level == CheckLevel.BLOCK:
                        all_passed = False
                        break

                    if not result.passed:
                        all_passed = False
                except Exception as e:
                    logger.error(f"预检查规则 {rule.rule_id} 执行失败: {e}")

        return PreCheckResult(passed=all_passed, checks=results)

    def get_rules_summary(self) -> list[dict[str, str]]:
        """获取规则摘要"""
        return [
            {"rule_id": rule.rule_id, "description": rule.description, "level": rule.level.value}
            for rule in self.rules
        ]


# 全局单例
precheck_manager = PreCheckManager()
