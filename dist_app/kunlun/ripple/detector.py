"""
昆仑创作引擎 — 蝴蝶效应检测器
当核心设定发生变更时，沿知识图谱追溯所有受影响的实体并生成影响报告
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from kunlun.kg.client import kg_client


@dataclass
class RippleImpact:
    """蝴蝶效应影响项"""

    entity_uid: str
    entity_type: str
    entity_name: str
    impact_description: str
    severity: str  # FATAL / HIGH / MEDIUM / LOW
    suggestion: str = ""


@dataclass
class RippleReport:
    """蝴蝶效应报告"""

    changed_entity_uid: str
    changed_entity_type: str
    change_description: str
    impacts: list[RippleImpact] = field(default_factory=list)
    total_affected: int = 0


class RippleDetector:
    """
    蝴蝶效应检测器

    当作者修改核心设定时：
    1. 通过 KG 图查询所有关联实体
    2. 评估每个关联实体受影响的程度
    3. 生成影响报告
    """

    def __init__(self):
        pass

    def detect(self, changed_entity_uid: str, change_description: str) -> RippleReport:
        """
        检测修改一个实体后的蝴蝶效应。

        Args:
            changed_entity_uid: 被修改的实体 UID
            change_description: 修改内容描述

        Returns:
            RippleReport: 影响报告
        """
        report = RippleReport(
            changed_entity_uid=changed_entity_uid,
            changed_entity_type="unknown",
            change_description=change_description,
        )

        try:
            # 获取被修改实体的类型和名称
            entity_info = self._get_entity_info(changed_entity_uid)
            report.changed_entity_type = entity_info.get("type", "unknown")

            # 通过图数据库查询所有直接关联的实体
            related = self._get_related_entities(changed_entity_uid)

            # 分析每个关联实体的受影响程度
            for rel in related:
                impact = self._assess_impact(
                    changed_entity_uid, entity_info, rel, change_description
                )
                if impact:
                    report.impacts.append(impact)

            report.total_affected = len(report.impacts)

        except Exception as e:
            logger.warning(f"[RippleDetector] 检测失败: {e}")

        return report

    def _get_entity_info(self, uid: str) -> dict:
        """获取实体信息（使用参数化查询防止注入）"""
        try:
            result = kg_client.query_cypher(
                "MATCH (n {uid: $uid}) RETURN n.type AS type, n.name AS name LIMIT 1",
                {"uid": uid},
            )
            if result:
                return result[0]
        except Exception as e:
            logger.debug(f"[RippleDetector] 获取实体信息失败 (uid={uid}): {e}")
        return {"type": "unknown", "name": uid}

    def _get_related_entities(self, uid: str) -> list[dict]:
        """获取所有直接关联实体（使用参数化查询防止注入）"""
        related = []
        try:
            edges = kg_client.query_cypher(
                """
                MATCH (n {uid: $uid})-[r]->(m)
                RETURN m.uid AS uid, m.type AS type, m.name AS name, type(r) AS relation
                UNION
                MATCH (m)-[r]->(n {uid: $uid})
                RETURN m.uid AS uid, m.type AS type, m.name AS name, type(r) AS relation
                """,
                {"uid": uid},
            )
            if edges:
                related.extend(edges)
        except Exception as e:
            logger.debug(f"[RippleDetector] 获取关联实体失败 (uid={uid}): {e}")
        return related

    def _assess_impact(
        self, changed_uid: str, entity_info: dict, related: dict, change_description: str
    ) -> RippleImpact | None:
        """评估单个关联实体的受影响程度"""
        rel_type = related.get("relation", "")
        entity_type = related.get("type", "")

        # 根据关系类型和实体类型分级
        severity_rules = {
            # 角色相关
            ("MEMBER_OF", "Organization"): ("HIGH", "角色所属组织变更可能影响身份/资源/剧情线"),
            ("INVOLVED_IN", "Event"): ("HIGH", "相关事件可能需要重新编排"),
            ("KNOWS_SKILL", "Skill"): ("MEDIUM", "角色技能体系可能需要调整"),
            ("LOCATED_AT", "Location"): ("LOW", "位置信息需要同步更新"),
            ("POSSESSES", "Item"): ("MEDIUM", "物品归属可能需要调整"),
            # 组织相关
            ("HOSTILE_ORG", "Organization"): ("HIGH", "势力博弈关系可能改变"),
            ("SUBORDINATE_OF", "Character"): ("MEDIUM", "从属关系需要重新定义"),
        }

        key = (rel_type, entity_type)
        severity, base_desc = severity_rules.get(
            key, ("MEDIUM", f"关系类型 {rel_type} 下的 {entity_type} 实体可能受影响")
        )

        return RippleImpact(
            entity_uid=related.get("uid", ""),
            entity_type=entity_type,
            entity_name=related.get("name", ""),
            impact_description=(
                f"{base_desc}，因 {entity_info.get('name', changed_uid)} "
                f"的变更：{change_description}"
            ),
            severity=severity,
            suggestion=f"请检查 {related.get('name', '')} 是否需要对应调整",
        )

    def generate_markdown_report(self, report: RippleReport) -> str:
        """生成 Markdown 格式的影响报告"""
        lines = [
            "## 🦋 蝴蝶效应检测报告",
            "",
            f"**变更实体**: `{report.changed_entity_uid}` ({report.changed_entity_type})",
            f"**变更内容**: {report.change_description}",
            f"**影响范围**: {report.total_affected} 个关联实体",
            "",
            "| 严重度 | 实体 | 类型 | 影响描述 | 建议 |",
            "|--------|------|------|----------|------|",
        ]
        lines.extend(
            f"| {imp.severity} | {imp.entity_name} ({imp.entity_uid}) | "
            f"{imp.entity_type} | {imp.impact_description} | {imp.suggestion} |"
            for imp in sorted(
                report.impacts, key=lambda x: ["FATAL", "HIGH", "MEDIUM", "LOW"].index(x.severity)
            )
        )

        if not report.impacts:
            lines.append("| — | 未发现受影响实体 | — | — | — |")

        return "\n".join(lines)


# 全局单例
ripple_detector = RippleDetector()
