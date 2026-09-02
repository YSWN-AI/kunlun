"""
昆仑创作引擎 — 信息差追踪器
管理每个角色在当前节点掌握的情报，防止上帝视角
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from kunlun.config import settings


@dataclass
class IntelItem:
    """一条情报"""

    uid: str  # 唯一标识，如 intel_villain_weakness
    content: str  # 情报内容
    source_event_uid: str  # 来源事件
    acquired_chapter: int  # 获取章节
    classification: str = ""  # 秘密/公开/谣言/...


@dataclass
class CharacterIntel:
    """角色的情报掌握表"""

    character_uid: str
    known_intel: dict[str, IntelItem] = field(default_factory=dict)
    # intel_uid → IntelItem


class IntelTracker:
    """
    信息差追踪器

    核心能力:
    - 记录每个角色获取的情报
    - 查询"角色X是否知道Y"
    - 校验剧情中角色是否使用了未掌握的信息（上帝视角检测）
    """

    def __init__(self, book_id: str = ""):
        self._characters: dict[str, CharacterIntel] = {}
        self._global_intel: dict[str, IntelItem] = {}  # 所有已知情报池
        self._book_id = book_id
        self._data_dir: Path | None = None
        if book_id:
            self._data_dir = settings.DATA_DIR / "intel" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def _intel_to_dict(self, item: IntelItem) -> dict:
        return {
            "uid": item.uid,
            "content": item.content,
            "source_event_uid": item.source_event_uid,
            "acquired_chapter": item.acquired_chapter,
            "classification": item.classification,
        }

    def _intel_from_dict(self, d: dict) -> IntelItem:
        return IntelItem(
            uid=d["uid"],
            content=d["content"],
            source_event_uid=d.get("source_event_uid", ""),
            acquired_chapter=d.get("acquired_chapter", 0),
            classification=d.get("classification", ""),
        )

    def save(self):
        """持久化到磁盘"""
        if not self._data_dir:
            return
        data = {
            "characters": {},
            "global_intel": {},
        }
        for uid, char in self._characters.items():
            data["characters"][uid] = {
                "character_uid": char.character_uid,
                "known_intel": {k: self._intel_to_dict(v) for k, v in char.known_intel.items()},
            }
        for uid, intel in self._global_intel.items():
            data["global_intel"][uid] = self._intel_to_dict(intel)

        path = self._data_dir / "intel_tracker.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        """从磁盘恢复"""
        if not self._data_dir:
            return
        path = self._data_dir / "intel_tracker.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for uid, cd in data.get("characters", {}).items():
                char = CharacterIntel(character_uid=cd["character_uid"])
                for iuid, idict in cd.get("known_intel", {}).items():
                    char.known_intel[iuid] = self._intel_from_dict(idict)
                self._characters[uid] = char
            for uid, idict in data.get("global_intel", {}).items():
                self._global_intel[uid] = self._intel_from_dict(idict)
        except Exception as e:
            logger.warning(f"[IntelTracker] 加载持久化数据失败: {e}")

    def register_character(self, character_uid: str) -> None:
        if character_uid not in self._characters:
            self._characters[character_uid] = CharacterIntel(character_uid=character_uid)

    def add_intel(self, intel: IntelItem, known_by: list[str]) -> None:
        """添加一条情报，并指定哪些角色已知"""
        self._global_intel[intel.uid] = intel
        for char_uid in known_by:
            self.register_character(char_uid)
            self._characters[char_uid].known_intel[intel.uid] = intel

    def does_character_know(self, character_uid: str, intel_uid: str) -> bool:
        """角色是否知道某情报"""
        char = self._characters.get(character_uid)
        return char is not None and intel_uid in char.known_intel

    def check_god_view(self, character_uid: str, claimed_knowledge: str, chapter: int) -> dict:
        """
        上帝视角检测：角色声称知道某事，但检查其情报掌握表。
        返回 {"violation": bool, "detail": str}
        """
        char = self._characters.get(character_uid)
        if not char:
            return {"violation": False, "detail": f"角色 {character_uid} 未注册"}

        # 检查 claimed_knowledge 是否匹配任何已知情报
        for intel in char.known_intel.values():
            if intel.acquired_chapter <= chapter and intel.content in claimed_knowledge:
                return {
                    "violation": False,
                    "detail": f"情报 {intel.uid} 已于第{intel.acquired_chapter}章获得",
                }

        # 检查是否为公开情报
        for intel in self._global_intel.values():
            if intel.classification == "公开" and intel.content in claimed_knowledge:
                return {"violation": False, "detail": "公开情报，无需特别获取"}

        return {
            "violation": True,
            "detail": f"角色 {character_uid} 在第{chapter}章未掌握此情报，存在上帝视角风险",
        }

    def get_character_intel_summary(self, character_uid: str) -> dict:
        """获取角色情报摘要"""
        char = self._characters.get(character_uid)
        if not char:
            return {"character_uid": character_uid, "intel_count": 0, "intel_list": []}
        return {
            "character_uid": character_uid,
            "intel_count": len(char.known_intel),
            "intel_list": [
                {"uid": i.uid, "content": i.content[:80], "chapter": i.acquired_chapter}
                for i in sorted(char.known_intel.values(), key=lambda x: x.acquired_chapter)
            ],
        }

    def get_info_gap(self, char_a: str, char_b: str) -> dict:
        """
        计算两个角色之间的信息差
        返回 A知道但B不知道的、B知道但A不知道的、双方都知道的
        """
        a = self._characters.get(char_a)
        b = self._characters.get(char_b)
        if not a or not b:
            return {"error": "角色未注册"}

        a_set = set(a.known_intel.keys())
        b_set = set(b.known_intel.keys())

        return {
            "only_a_knows": list(a_set - b_set),
            "only_b_knows": list(b_set - a_set),
            "both_know": list(a_set & b_set),
            "a_total": len(a_set),
            "b_total": len(b_set),
        }


# 全局单例
intel_tracker = IntelTracker()
