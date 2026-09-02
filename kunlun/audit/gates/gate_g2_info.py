"""
G2: 信息释放节奏

检测新概念/伏笔释放是否合理。
"""

from __future__ import annotations

import re

from loguru import logger

from kunlun.audit.gates._base import GateLevel, GateResult
from kunlun.config import settings


class GateG2InfoRelease:
    """G2: 信息释放节奏"""

    def run(self, draft: str, _blueprint: dict, kg_snapshot_id: str) -> GateResult:
        try:
            from kunlun.kg.snapshot import snapshot_manager

            snapshot = snapshot_manager.get_snapshot(kg_snapshot_id) if kg_snapshot_id else None
        except Exception as e:
            logger.debug(f"G2 KG快照获取失败: {e}")
            snapshot = None

        new_concepts = self._extract_new_concepts(draft)
        new_concept_count = len(new_concepts)

        max_allowed = settings.audit_max_new_concepts_per_chapter
        if new_concept_count > max_allowed:
            return GateResult(
                gate_id="G2",
                level=GateLevel.FAIL,
                score=0.3,
                detail=f"新概念过多 ({new_concept_count} > {max_allowed}): {new_concepts[:3]}...",
                data={"new_concepts": new_concepts, "count": new_concept_count},
            )
        if new_concept_count > max_allowed * 0.7:
            level = GateLevel.WARN
            score = 0.6
        else:
            level = GateLevel.PASS
            score = 0.9 - new_concept_count * 0.1

        detail = f"新概念数量: {new_concept_count}"
        if snapshot:
            expected_reveals = getattr(snapshot, "foreshadowing_planted", [])
            actual_reveals = self._check_foreshadowing_reveals(draft, expected_reveals)
            detail += f", 应释放伏笔: {len(expected_reveals)}, 实际释放: {len(actual_reveals)}"

        return GateResult(
            gate_id="G2",
            level=level,
            score=score,
            detail=detail,
            data={"new_concepts": new_concepts, "count": new_concept_count},
        )

    def _extract_new_concepts(self, draft: str) -> list:
        concepts = []
        pattern = r'[“"]([^“”"]+)[”"]|[《]([^《》]+)[》]|([一-鿿]{1,4}的[一-鿿]{1,6})'
        for match in re.finditer(pattern, draft):
            concepts.extend(group for group in match.groups() if group and len(group) >= 4)
        return list(set(concepts))[:20]

    def _check_foreshadowing_reveals(self, draft: str, expected: list) -> list:
        return [
            item["name"]
            for item in expected
            if isinstance(item, dict) and "name" in item and item["name"] in draft
        ]
