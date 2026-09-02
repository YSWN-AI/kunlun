"""
worlds 引擎核心实现
世界观一致性检测 + 溢出控制

对标 NovelCrafter Codex 的一致性规则引擎，
纯规则零LLM：7维检测 + 严重度评分 + 溢出报告。

Author: 昆仑创作引擎
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 枚举与数据类
# ══════════════════════════════════════════════════════


class Severity(StrEnum):
    """严重度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Dimension(StrEnum):
    """世界观一致性维度"""

    POWER_SYSTEM = "power_system"  # 力量体系
    GEOGRAPHY = "geography"  # 地理空间
    CULTURE_RULES = "culture_rules"  # 文化规则
    ECONOMY = "economy"  # 经济体系
    MAGIC_TECH = "magic_tech"  # 魔法/科技
    CREATURE_SPECIES = "creature_species"  # 生物种族
    ITEM_ARTIFACT = "item_artifact"  # 道具神器

    @property
    def label(self) -> str:
        labels = {
            "power_system": "力量体系",
            "geography": "地理空间",
            "culture_rules": "文化规则",
            "economy": "经济体系",
            "magic_tech": "魔法/科技",
            "creature_species": "生物种族",
            "item_artifact": "道具神器",
        }
        return labels.get(self.value, self.value)


@dataclass
class WorldSetting:
    """世界观设定条目"""

    key: str  # 唯一标识
    dimension: Dimension  # 所属维度
    name: str  # 显示名称
    description: str  # 描述
    rules: list[str] = field(default_factory=list)  # 约束规则
    chapter_introduced: int = 0  # 引入章节
    chapter_modified: int = 0  # 最后修改章节
    overridable: bool = True  # 是否可被覆盖
    references: list[str] = field(default_factory=list)  # 关联设定 key


@dataclass
class ConsistencyIssue:
    """一致性问题"""

    dimension: Dimension
    setting_key: str
    description: str
    severity: Severity
    chapter: int
    context: str = ""
    suggestion: str = ""


@dataclass
class WorldAuditReport:
    """世界观审计报告"""

    book_id: str
    chapter: int
    issues: list[ConsistencyIssue] = field(default_factory=list)
    dimension_scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    overall_severity: Severity = Severity.INFO
    overflow_warnings: list[str] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def issue_count(self) -> int:
        return len(self.issues)


@dataclass
class OverflowReport:
    """世界观溢出报告 — 检测是否超出设定边界"""

    dimension: Dimension
    setting_key: str
    rule_violated: str
    offending_text: str
    chapter: int
    severity: Severity
    suggestion: str


# ══════════════════════════════════════════════════════
# 世界观一致性检测器
# ══════════════════════════════════════════════════════


class WorldConsistencyChecker:
    """世界观一致性检测器 — 纯规则零LLM"""

    # 力量体系关键词模式
    POWER_PATTERNS: dict[str, re.Pattern] = {
        "境界跳跃": re.compile(
            r"(炼气|筑基|金丹|元婴|化神|合体|大乘|渡劫)"
            r".{0,20}(突然|瞬间|一下子|直接)"
            r".{0,20}(突破|晋升|提升|跨越)"
        ),
        "力量矛盾": re.compile(
            r"(明明|刚才还是|之前还).{0,10}(炼气|筑基|金丹|元婴)"
            r".{0,30}(却|竟然|居然).{0,10}(击败|碾压|秒杀)"
        ),
        "越级挑战": re.compile(
            r"(炼气|筑基|金丹).{0,5}(修士|期)"
            r".{0,20}(挑战|对抗|硬撼)"
            r".{0,5}(元婴|化神|合体|大乘)"
        ),
    }

    # 地理一致性检查
    GEOGRAPHY_PATTERNS: dict[str, re.Pattern] = {
        "空间跳跃": re.compile(
            r"(东大陆|西荒|南域|北疆|中州).{0,30}"
            r"(转眼|片刻|瞬间|须臾).{0,30}"
            r"(东大陆|西荒|南域|北疆|中州)"
        ),
        "方向矛盾": re.compile(
            r"(向东|向西|向南|向北).{0,50}"
            r"(向东|向西|向南|向北)"
        ),
    }

    # 魔法/科技规则矛盾
    MAGIC_TECH_PATTERNS: dict[str, re.Pattern] = {
        "冷却无视": re.compile(
            r"(刚刚|才|刚才).{0,10}(使用|施展|释放)"
            r".{0,30}(又|再次|再度).{0,10}(使用|施展|释放)"
        ),
        "魔力溢出": re.compile(
            r"(耗尽|枯竭|用尽|一丝不剩).{0,10}(灵力|魔力|法力)"
            r".{0,50}(又|再次|继续).{0,10}(释放|施展|使用)"
        ),
    }

    # 道具神器矛盾
    ITEM_PATTERNS: dict[str, re.Pattern] = {
        "物品消失": re.compile(
            r"(拿出|取出|祭出|亮出).{0,10}([\u4e00-\u9fff]{2,6}(剑|刀|枪|盾|鼎|印|珠|扇|镜))"
            r".{0,100}(收|丢|毁|碎|断).{0,5}(了|掉)"
            r".{0,50}(又|再次|竟).{0,10}(拿出|取出|祭出)"
        ),
        "物品突变": re.compile(
            r"(凡品|下品|中品|上品|极品|仙品|神品)"
            r".{0,20}(突然|竟|莫名).{0,10}(变成|变为|化作)"
        ),
    }

    @classmethod
    def check_power_system(
        cls, text: str, _settings: list[WorldSetting], chapter: int
    ) -> list[ConsistencyIssue]:
        """检测力量体系一致性"""
        issues: list[ConsistencyIssue] = []
        for name, pattern in cls.POWER_PATTERNS.items():
            issues.extend(
                ConsistencyIssue(
                    dimension=Dimension.POWER_SYSTEM,
                    setting_key="power_system",
                    description=f"力量体系矛盾: {name}",
                    severity=Severity.WARNING if name == "越级挑战" else Severity.ERROR,
                    chapter=chapter,
                    context=match.group()[:80],
                    suggestion={
                        "境界跳跃": "境界突破需要修炼积累，建议加入过渡描写",
                        "力量矛盾": "力量体系前后不一致，需要设定说明或修正",
                        "越级挑战": "越级挑战需要特殊条件支撑，如法宝/丹药/秘术",
                    }.get(name, "检查力量体系设定"),
                )
                for match in pattern.finditer(text)
            )
        return issues

    @classmethod
    def check_geography(
        cls, text: str, _settings: list[WorldSetting], chapter: int
    ) -> list[ConsistencyIssue]:
        """检测地理空间一致性"""
        issues: list[ConsistencyIssue] = []
        for name, pattern in cls.GEOGRAPHY_PATTERNS.items():
            for match in pattern.finditer(text):
                severity = Severity.ERROR if name == "空间跳跃" else Severity.WARNING
                issues.append(
                    ConsistencyIssue(
                        dimension=Dimension.GEOGRAPHY,
                        setting_key="geography",
                        description=f"地理矛盾: {name}",
                        severity=severity,
                        chapter=chapter,
                        context=match.group()[:80],
                        suggestion="确认是否有传送阵/飞行法宝等合理解释，否则需修正",
                    )
                )
        return issues

    @classmethod
    def check_magic_tech(
        cls, text: str, _settings: list[WorldSetting], chapter: int
    ) -> list[ConsistencyIssue]:
        """检测魔法/科技规则一致性"""
        issues: list[ConsistencyIssue] = []
        for name, pattern in cls.MAGIC_TECH_PATTERNS.items():
            issues.extend(
                ConsistencyIssue(
                    dimension=Dimension.MAGIC_TECH,
                    setting_key="magic_tech",
                    description=f"魔法/科技规则矛盾: {name}",
                    severity=Severity.ERROR if name == "魔力溢出" else Severity.WARNING,
                    chapter=chapter,
                    context=match.group()[:80],
                    suggestion={
                        "冷却无视": "确认技能冷却时间设定，确保前后一致",
                        "魔力溢出": "灵力耗尽后应有恢复过程，不能立即继续使用",
                    }.get(name, "检查魔法/科技规则设定"),
                )
                for match in pattern.finditer(text)
            )
        return issues

    @classmethod
    def check_items(
        cls, text: str, _settings: list[WorldSetting], chapter: int
    ) -> list[ConsistencyIssue]:
        """检测道具神器一致性"""
        issues: list[ConsistencyIssue] = []
        for name, pattern in cls.ITEM_PATTERNS.items():
            issues.extend(
                ConsistencyIssue(
                    dimension=Dimension.ITEM_ARTIFACT,
                    setting_key="item_artifact",
                    description=f"道具矛盾: {name}",
                    severity=Severity.ERROR,
                    chapter=chapter,
                    context=match.group()[:80],
                    suggestion={
                        "物品消失": "被毁/丢失的物品不应再次出现，需确认设定",
                        "物品突变": "物品品级变化需要合理解释（如隐藏品级/吞噬进化）",
                    }.get(name, "检查道具设定"),
                )
                for match in pattern.finditer(text)
            )
        return issues

    @classmethod
    def check_culture_rules(
        cls, text: str, _settings: list[WorldSetting], chapter: int
    ) -> list[ConsistencyIssue]:
        """检测文化规则一致性 — 称呼/礼仪/制度"""
        issues: list[ConsistencyIssue] = []

        # 检测称谓矛盾（如"前辈"→"小子"短时间切换）
        honorific_conflict = re.findall(r"(前辈|大人|阁下|师尊).{0,100}(小子|你|尔)", text)
        if honorific_conflict:
            issues.append(
                ConsistencyIssue(
                    dimension=Dimension.CULTURE_RULES,
                    setting_key="culture_rules",
                    description="称谓体系可能矛盾：尊称与蔑称短距离混用",
                    severity=Severity.WARNING,
                    chapter=chapter,
                    context=honorific_conflict[0] if honorific_conflict else "",
                    suggestion="确认对话双方身份关系，保持称谓体系一致",
                )
            )

        return issues

    @classmethod
    def check_creatures(
        cls, text: str, _settings: list[WorldSetting], chapter: int
    ) -> list[ConsistencyIssue]:
        """检测生物种族一致性"""
        issues: list[ConsistencyIssue] = []

        # 种族特性矛盾检测
        creature_contradictions = [
            (r"妖兽.{0,10}(开口|说话|言语)", "妖兽说话需要达到特定等级，确认设定"),
            (r"灵兽.{0,10}(反噬|背叛|攻击).{0,10}主人", "灵兽契约是否允许反噬，需确认"),
        ]
        for pattern, suggestion in creature_contradictions:
            if re.search(pattern, text):
                issues.append(
                    ConsistencyIssue(
                        dimension=Dimension.CREATURE_SPECIES,
                        setting_key="creature_species",
                        description="种族特性可能矛盾",
                        severity=Severity.WARNING,
                        chapter=chapter,
                        suggestion=suggestion,
                    )
                )

        return issues

    @classmethod
    def check_economy(
        cls, text: str, _settings: list[WorldSetting], chapter: int
    ) -> list[ConsistencyIssue]:
        """检测经济体系一致性"""
        issues: list[ConsistencyIssue] = []

        # 货币价值矛盾
        large_small_mix = re.findall(
            r"(\d+[万亿千百]?(灵石|金币|银两)).{0,80}(\d+[万亿千百]?(灵石|金币|银两))", text
        )
        if large_small_mix:
            # 检查是否出现价值跳跃
            for m1_val, m1_unit, m2_val, m2_unit in large_small_mix:
                if m1_unit == m2_unit:
                    issues.append(
                        ConsistencyIssue(
                            dimension=Dimension.ECONOMY,
                            setting_key="economy",
                            description="经济体系：短时间内出现两次货币数额，可能存在价值矛盾",
                            severity=Severity.WARNING,
                            chapter=chapter,
                            context=f"{m1_val}{m1_unit} vs {m2_val}{m2_unit}",
                            suggestion="确认前后货币数额是否合理，避免通胀矛盾",
                        )
                    )

        return issues

    # ── 综合审计 ────────────────────────────────────────

    @classmethod
    def audit(
        cls,
        text: str,
        settings: list[WorldSetting],
        chapter: int = 0,
        book_id: str = "",
    ) -> WorldAuditReport:
        """全面世界观审计"""
        all_issues: list[ConsistencyIssue] = []
        dimension_scores: dict[str, float] = {}

        checkers = [
            (Dimension.POWER_SYSTEM, cls.check_power_system),
            (Dimension.GEOGRAPHY, cls.check_geography),
            (Dimension.MAGIC_TECH, cls.check_magic_tech),
            (Dimension.ITEM_ARTIFACT, cls.check_items),
            (Dimension.CULTURE_RULES, cls.check_culture_rules),
            (Dimension.CREATURE_SPECIES, cls.check_creatures),
            (Dimension.ECONOMY, cls.check_economy),
        ]

        for dim, checker in checkers:
            dim_issues = checker(text, settings, chapter)
            all_issues.extend(dim_issues)
            # 计算维度得分：无问题=1.0，每个WARNING扣0.1，ERROR扣0.2，CRITICAL扣0.3
            penalty = sum(
                0.1
                if i.severity == Severity.WARNING
                else 0.2
                if i.severity == Severity.ERROR
                else 0.3
                for i in dim_issues
            )
            dimension_scores[dim.value] = max(0.0, 1.0 - penalty)

        # 总分
        overall = sum(dimension_scores.values()) / max(len(dimension_scores), 1)

        # 严重度
        if any(i.severity == Severity.CRITICAL for i in all_issues):
            overall_severity = Severity.CRITICAL
        elif any(i.severity == Severity.ERROR for i in all_issues):
            overall_severity = Severity.ERROR
        elif any(i.severity == Severity.WARNING for i in all_issues):
            overall_severity = Severity.WARNING
        else:
            overall_severity = Severity.INFO

        return WorldAuditReport(
            book_id=book_id,
            chapter=chapter,
            issues=all_issues,
            dimension_scores=dimension_scores,
            overall_score=round(overall, 2),
            overall_severity=overall_severity,
        )


# ══════════════════════════════════════════════════════
# 世界观溢出控制
# ══════════════════════════════════════════════════════


class WorldOverflowChecker:
    """世界观溢出检测 — 检测是否超出设定边界"""

    OVERFLOW_RULES: dict[Dimension, list[tuple[re.Pattern, str]]] = {
        Dimension.POWER_SYSTEM: [
            (re.compile(r"超越.{0,5}(极限|巅峰|桎梏|规则)"), "力量体系设定可能被突破"),
            (re.compile(r"打破.{0,5}(天道|法则|规则|秩序)"), "世界规则被打破，需确认是否在设定内"),
        ],
        Dimension.MAGIC_TECH: [
            (
                re.compile(r"(发明|创造|研发).{0,10}(新.{0,5}(功法|丹药|法宝|阵法))"),
                "新增魔法/科技元素，确认是否在设定范围内",
            ),
        ],
        Dimension.GEOGRAPHY: [
            (
                re.compile(r"(发现|找到).{0,10}(秘境|遗迹|洞府|空间|小世界)"),
                "新增地理空间，确认是否在设定范围内",
            ),
        ],
    }

    @classmethod
    def check(
        cls,
        text: str,
        _settings: list[WorldSetting],
        chapter: int,
    ) -> list[OverflowReport]:
        """检测世界观溢出"""
        reports: list[OverflowReport] = []

        for dim, rules in cls.OVERFLOW_RULES.items():
            for pattern, description in rules:
                for match in pattern.finditer(text):
                    severity = Severity.WARNING if dim in (Dimension.GEOGRAPHY,) else Severity.ERROR
                    reports.append(
                        OverflowReport(
                            dimension=dim,
                            setting_key=dim.value,
                            rule_violated=description,
                            offending_text=match.group()[:80],
                            chapter=chapter,
                            severity=severity,
                            suggestion=(
                                f"确认此内容是否在{dim.label}设定范围内，"
                                f"如需新增请在 story_bible.md 中记录"
                            ),
                        )
                    )

        return reports


# ══════════════════════════════════════════════════════
# 世界观管理器
# ══════════════════════════════════════════════════════


class WorldSettingManager:
    """世界观设定管理器"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self.settings: dict[str, WorldSetting] = {}
        self._data_dir: Path | None = None
        if book_id:
            self._data_dir = settings.DATA_DIR / "worlds" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load_settings()

    def _load_settings(self):
        """加载世界观设定"""
        if not self._data_dir:
            return
        settings_file = self._data_dir / "settings.json"
        if settings_file.exists():
            import json

            try:
                data = json.loads(settings_file.read_text(encoding="utf-8"))
                for item in data:
                    # 反序列化时 dimension 为字符串，需转换为 Dimension 枚举
                    if "dimension" in item and isinstance(item["dimension"], str):
                        try:
                            item["dimension"] = Dimension(item["dimension"])
                        except ValueError:
                            logger.warning(f"未知维度: {item['dimension']}，跳过")
                            continue
                    ws = WorldSetting(**item)
                    self.settings[ws.key] = ws
            except Exception:
                logger.warning("世界观设定加载失败，使用空设定")

    def add_setting(self, setting: WorldSetting):
        """添加设定条目"""
        self.settings[setting.key] = setting
        self._save()

    def get_setting(self, key: str) -> WorldSetting | None:
        return self.settings.get(key)

    def get_by_dimension(self, dimension: Dimension) -> list[WorldSetting]:
        return [s for s in self.settings.values() if s.dimension == dimension]

    def list_all(self) -> list[WorldSetting]:
        return list(self.settings.values())

    def list_settings(self) -> list[WorldSetting]:
        """列出所有设定条目（别名，兼容 builder.py）"""
        return self.list_all()

    def _save(self):
        if not self._data_dir:
            return
        import json

        settings_file = self._data_dir / "settings.json"
        data = [
            {
                "key": s.key,
                "dimension": s.dimension.value,
                "name": s.name,
                "description": s.description,
                "rules": s.rules,
                "chapter_introduced": s.chapter_introduced,
                "chapter_modified": s.chapter_modified,
                "overridable": s.overridable,
                "references": s.references,
            }
            for s in self.settings.values()
        ]
        settings_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ── 模板初始化 ────────────────────────────────────

    DEFAULT_TEMPLATES: dict[str, list[WorldSetting]] = {
        "xianxia": [
            WorldSetting(
                key="xiuzhen_levels",
                dimension=Dimension.POWER_SYSTEM,
                name="修真境界",
                description="炼气→筑基→金丹→元婴→化神→合体→大乘→渡劫",
                rules=["每个境界有初期/中期/后期/巅峰四小阶", "突破大境界需要天劫"],
            ),
            WorldSetting(
                key="lingqi_system",
                dimension=Dimension.MAGIC_TECH,
                name="灵气体系",
                description="天地灵气→修士炼化→灵力",
                rules=["灵力耗尽需打坐恢复", "灵气浓度影响修炼速度"],
            ),
            WorldSetting(
                key="cultivation_world",
                dimension=Dimension.GEOGRAPHY,
                name="修真界地理",
                description="东胜神州/西牛贺洲/南赡部洲/北俱芦洲",
                rules=["大陆间有传送阵", "秘境随机出现"],
            ),
        ],
        "xuanhuan": [
            WorldSetting(
                key="douqi_levels",
                dimension=Dimension.POWER_SYSTEM,
                name="斗气等级",
                description="斗者→斗师→大斗师→斗灵→斗王→斗皇→斗宗→斗尊→斗圣→斗帝",
                rules=["每级分1-9星", "大境界突破需要契机"],
            ),
            WorldSetting(
                key="magic_beasts",
                dimension=Dimension.CREATURE_SPECIES,
                name="魔兽体系",
                description="一阶→九阶魔兽，对应人类等级",
                rules=["魔兽可契约", "高阶魔兽有智慧"],
            ),
        ],
    }

    def init_from_template(self, template_key: str):
        """从模板初始化世界观"""
        template = self.DEFAULT_TEMPLATES.get(template_key, [])
        for ws in template:
            if ws.key not in self.settings:
                self.settings[ws.key] = ws
        self._save()
        return len(template)


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_world_managers: dict[str, WorldSettingManager] = {}


def get_world_manager(book_id: str) -> WorldSettingManager:
    """获取世界观管理器（单例）"""
    if book_id not in _world_managers:
        _world_managers[book_id] = WorldSettingManager(book_id)
    return _world_managers[book_id]


def get_world_checker() -> type[WorldConsistencyChecker]:
    """获取世界观一致性检测器类"""
    return WorldConsistencyChecker
