"""
G4: 爽点间隔检测

检测爽点出现的间隔是否在合理范围内。
"""

from __future__ import annotations

from loguru import logger

from kunlun.audit.gates._base import GateLevel, GateResult
from kunlun.config import settings


class GateG4PleasureGap:
    """G4: 爽点间隔检测"""

    PLEASURE_KEYWORDS = {
        "slap_face": ["打脸", "碾压", "秒杀", "完爆", "吊打"],
        "level_up": ["突破", "晋级", "升级", "领悟", "顿悟"],
        "treasure": ["宝物", "神器", "秘籍", "传承", "奇遇"],
        "revenge": ["报仇", "复仇", "雪耻", "洗刷"],
        "revelation": ["真相", "揭秘", "揭露", "原来"],
        "romance": ["心动", "暧昧", "亲吻", "拥抱", "表白"],
        "show_off": ["炫耀", "展示", "震惊", "目瞪口呆"],
    }

    def run(self, draft: str, kg_snapshot_id: str) -> GateResult:
        last_pleasure_chapter = self._get_last_pleasure_chapter(kg_snapshot_id)
        if last_pleasure_chapter is None:
            return self._fallback_keyword_check(draft)

        current_chapter = self._extract_chapter_number(kg_snapshot_id)
        if current_chapter is None:
            return self._fallback_keyword_check(draft)

        gap = current_chapter - last_pleasure_chapter
        max_gap = settings.audit_max_gaps_between_pleasure_points

        if gap > max_gap:
            level = GateLevel.FAIL
            score = 0.3
        elif gap > max_gap * 0.8:
            level = GateLevel.WARN
            score = 0.6
        else:
            level = GateLevel.PASS
            score = 0.9

        has_pleasure = self._has_pleasure_keywords(draft)
        if not has_pleasure and gap >= max_gap:
            level = GateLevel.FAIL
            score = 0.2
            detail = f"已连续{gap}章无爽点，且本章仍未出现爽点关键词"
        else:
            detail = f"距上一爽点章节: {gap}章, 阈值: {max_gap}章"

        return GateResult(
            gate_id="G4",
            level=level,
            score=score,
            detail=detail,
            data={"gap": gap, "max_gap": max_gap, "has_pleasure": has_pleasure},
        )

    def _get_last_pleasure_chapter(self, kg_snapshot_id: str) -> int | None:
        try:
            if not kg_snapshot_id:
                return None

            from kunlun.kg.snapshot import snapshot_manager

            snapshot = snapshot_manager.get_snapshot(kg_snapshot_id)
            if not snapshot:
                return None

            context = snapshot.to_context_dict()
            last_pleasure = context.get("last_pleasure_chapter")
            if last_pleasure:
                return int(last_pleasure)

            from kunlun.kg.client import kg_client

            cypher = """
            MATCH (pp:PleasurePoint)-[:BELONGS_TO]->(ch:Chapter)
            WHERE ch.book_id = $book_id AND ch.chapterNumber < $chapter
            RETURN ch.chapterNumber AS chapter
            ORDER BY ch.chapterNumber DESC
            LIMIT 1
            """
            book_id = snapshot.book_id
            chapter = snapshot.chapter
            results = kg_client.query_cypher(cypher, {"book_id": book_id, "chapter": chapter})
            if results and "chapter" in results[0]:
                return int(results[0]["chapter"])
        except Exception as e:
            logger.warning(f"G4 KG查询失败: {e}")

        return None

    def _extract_chapter_number(self, kg_snapshot_id: str) -> int | None:
        try:
            from kunlun.kg.snapshot import snapshot_manager

            snapshot = snapshot_manager.get_snapshot(kg_snapshot_id)
            return snapshot.chapter if snapshot else None
        except Exception as e:
            logger.debug(f"G4 章节号提取失败: {e}")
            return None

    def _fallback_keyword_check(self, draft: str) -> GateResult:
        try:
            from kunlun.audit.jieba_analyzer import match_keywords

            matched = match_keywords(draft, self.PLEASURE_KEYWORDS)
            pleasure_positions = []
            if matched:
                pleasure_positions = [1]
        except Exception as e:
            logger.debug(f"G4 jieba关键词匹配失败，回退到简单匹配: {e}")
            pleasure_positions = []
            for keywords in self.PLEASURE_KEYWORDS.values():
                for kw in keywords:
                    pos = draft.find(kw)
                    if pos != -1:
                        pleasure_positions.append(pos)

        if not pleasure_positions:
            return GateResult(
                gate_id="G4",
                level=GateLevel.WARN,
                score=0.5,
                detail="未检测到爽点关键词（无法获取KG上下文）",
            )

        pleasure_positions.sort()
        gaps = [
            pleasure_positions[i] - pleasure_positions[i - 1]
            for i in range(1, len(pleasure_positions))
        ]

        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        char_count = len(draft)

        if char_count > 0 and avg_gap > char_count * 0.5:
            level = GateLevel.WARN
            score = 0.6
            detail = f"爽点分布稀疏，平均间隔{avg_gap:.0f}字符"
        else:
            level = GateLevel.PASS
            score = 0.8
            detail = f"检测到{len(pleasure_positions)}处爽点关键词，分布正常"

        return GateResult(
            gate_id="G4",
            level=level,
            score=score,
            detail=detail,
            data={"pleasure_count": len(pleasure_positions), "avg_gap": avg_gap},
        )

    def _has_pleasure_keywords(self, draft: str) -> bool:
        try:
            from kunlun.audit.jieba_analyzer import match_keywords

            matched = match_keywords(draft, self.PLEASURE_KEYWORDS)
            return bool(matched)
        except Exception as e:
            logger.debug(f"G4 jieba分词匹配失败，回退到简单字符串匹配: {e}")
        for keywords in self.PLEASURE_KEYWORDS.values():
            for kw in keywords:
                if kw in draft:
                    return True
        return False
