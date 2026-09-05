"""
昆仑创作引擎 — 本地技能包市场引擎

管理本地技能组合包（Combo Pack）的安装/卸载/查询。
每个组合包包含 Rule + Workflow + Skill 集合，安装后写入书籍的 writing_packs.json。

存储:
  - 内置组合包: presets.py 中定义
  - 已安装记录: data/books/book_<id>/installed_packs.json
  - writing_packs: data/books/book_<id>/writing_packs.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.local_marketplace.presets import get_all_packs


def _book_dir(book_id: str) -> Path:
    """获取书籍数据目录"""
    from kunlun.config import settings

    return Path(settings.PROJECT_ROOT) / "data" / "books" / f"book_{book_id}"


def _installed_packs_path(book_id: str) -> Path:
    return _book_dir(book_id) / "installed_packs.json"


def _writing_packs_path(book_id: str) -> Path:
    return _book_dir(book_id) / "writing_packs.json"


def _read_json(path: Path, default: Any) -> Any:
    """安全读取 JSON 文件"""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[LocalMarketplace] 读取 {path} 失败: {e}")
        return default


def _write_json(path: Path, data: Any) -> bool:
    """安全写入 JSON 文件"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError as e:
        logger.error(f"[LocalMarketplace] 写入 {path} 失败: {e}")
        return False


class LocalMarketplaceEngine:
    """本地技能包市场引擎

    用法:
        engine = LocalMarketplaceEngine()
        packs = engine.list_available(category="xuanhuan")
        engine.install("book_001", "pack_xuanhuan_shuangwen")
    """

    def __init__(self) -> None:
        self._packs: dict[str, dict] = {}
        self._reload_presets()

    def _reload_presets(self) -> None:
        """从 presets 重新加载内置组合包"""
        self._packs = {}
        for pack in get_all_packs():
            self._packs[pack["id"]] = pack

    # ─── 查询 ──────────────────────────────────────

    def list_available(self, category: str | None = None) -> list[dict]:
        """列出可安装的组合包

        Args:
            category: 分类筛选 (xuanhuan/xianxia/dushi/lishi/kehuan)
        """
        result = []
        for pack in self._packs.values():
            if category and pack.get("category") != category:
                continue
            result.append(self._public_view(pack))
        return result

    def get_detail(self, pack_id: str) -> dict | None:
        """获取组合包详情"""
        pack = self._packs.get(pack_id)
        if not pack:
            return None
        return self._public_view(pack, include_contents=True)

    def get_hot(self, limit: int = 5) -> list[dict]:
        """热门组合包（按下载量排序）"""
        packs = sorted(self._packs.values(), key=lambda p: -p.get("downloads", 0))
        return [self._public_view(p) for p in packs[:limit]]

    def search(self, query: str) -> list[dict]:
        """搜索组合包（名称/描述/标签匹配）"""
        if not query:
            return self.list_available()
        q = query.lower()
        result = []
        for pack in self._packs.values():
            match = (
                q in pack.get("name", "").lower()
                or q in pack.get("description", "").lower()
                or any(q in t.lower() for t in pack.get("tags", []))
            )
            if match:
                result.append(self._public_view(pack))
        return result

    # ─── 安装/卸载 ─────────────────────────────────

    def install(self, book_id: str, pack_id: str) -> bool:
        """安装组合包到指定书籍

        将组合包中的 Rule/Workflow/Skill 写入该书的 writing_packs.json，
        并在 installed_packs.json 中记录安装信息。
        """
        pack = self._packs.get(pack_id)
        if not pack:
            logger.warning(f"[LocalMarketplace] 组合包不存在: {pack_id}")
            return False

        # 检查是否已安装
        installed = self._read_installed(book_id)
        if pack_id in installed:
            logger.info(f"[LocalMarketplace] 组合包已安装: {pack_id} -> {book_id}")
            return True

        # 写入 writing_packs.json
        writing_packs = _read_json(
            _writing_packs_path(book_id),
            {"rules": [], "workflows": [], "skills": []},
        )

        existing_rule_ids = {r.get("id") for r in writing_packs.get("rules", [])}
        existing_wf_ids = {w.get("id") for w in writing_packs.get("workflows", [])}
        existing_skill_ids = {s.get("id") for s in writing_packs.get("skills", [])}

        added_rules = 0
        for rule in pack.get("rule_contents", []):
            if rule.get("id") not in existing_rule_ids:
                writing_packs.setdefault("rules", []).append(rule)
                added_rules += 1

        added_wfs = 0
        for wf in pack.get("workflow_contents", []):
            if wf.get("id") not in existing_wf_ids:
                writing_packs.setdefault("workflows", []).append(wf)
                added_wfs += 1

        added_skills = 0
        for skill in pack.get("skill_contents", []):
            if skill.get("id") not in existing_skill_ids:
                writing_packs.setdefault("skills", []).append(skill)
                added_skills += 1

        if not _write_json(_writing_packs_path(book_id), writing_packs):
            return False

        # 记录安装信息
        installed[pack_id] = {
            "pack_id": pack_id,
            "name": pack.get("name", ""),
            "installed_at": time.time(),
            "added_rules": added_rules,
            "added_workflows": added_wfs,
            "added_skills": added_skills,
        }
        if not _write_json(_installed_packs_path(book_id), installed):
            return False

        # 更新下载量（内存中）
        pack["downloads"] = pack.get("downloads", 0) + 1

        logger.info(
            f"[LocalMarketplace] 安装成功: {pack_id} -> {book_id} "
            f"(+{added_rules} rules, +{added_wfs} workflows, +{added_skills} skills)"
        )
        return True

    def uninstall(self, book_id: str, pack_id: str) -> bool:
        """从指定书籍卸载组合包

        从 writing_packs.json 中移除该组合包包含的 Rule/Workflow/Skill，
        并从 installed_packs.json 中删除记录。
        注意：如果某个 Rule/Workflow/Skill 被多个组合包共享，不会删除。
        """
        installed = self._read_installed(book_id)
        if pack_id not in installed:
            logger.warning(f"[LocalMarketplace] 组合包未安装: {pack_id} -> {book_id}")
            return False

        pack = self._packs.get(pack_id)
        if not pack:
            # 组合包已不存在（可能被移除），仅清理安装记录
            installed.pop(pack_id, None)
            _write_json(_installed_packs_path(book_id), installed)
            return True

        writing_packs = _read_json(
            _writing_packs_path(book_id),
            {"rules": [], "workflows": [], "skills": []},
        )

        # 收集待移除的 ID
        remove_rule_ids = {r.get("id") for r in pack.get("rule_contents", [])}
        remove_wf_ids = {w.get("id") for w in pack.get("workflow_contents", [])}
        remove_skill_ids = {s.get("id") for s in pack.get("skill_contents", [])}

        # 检查其他已安装组合包是否也包含这些 ID（共享则不删除）
        other_pack_ids = [pid for pid in installed if pid != pack_id]
        for other_id in other_pack_ids:
            other_pack = self._packs.get(other_id)
            if not other_pack:
                continue
            remove_rule_ids -= {r.get("id") for r in other_pack.get("rule_contents", [])}
            remove_wf_ids -= {w.get("id") for w in other_pack.get("workflow_contents", [])}
            remove_skill_ids -= {s.get("id") for s in other_pack.get("skill_contents", [])}

        # 执行移除
        writing_packs["rules"] = [
            r for r in writing_packs.get("rules", []) if r.get("id") not in remove_rule_ids
        ]
        writing_packs["workflows"] = [
            w for w in writing_packs.get("workflows", []) if w.get("id") not in remove_wf_ids
        ]
        writing_packs["skills"] = [
            s for s in writing_packs.get("skills", []) if s.get("id") not in remove_skill_ids
        ]

        if not _write_json(_writing_packs_path(book_id), writing_packs):
            return False

        # 删除安装记录
        installed.pop(pack_id, None)
        if not _write_json(_installed_packs_path(book_id), installed):
            return False

        logger.info(f"[LocalMarketplace] 卸载成功: {pack_id} -> {book_id}")
        return True

    def list_installed(self, book_id: str) -> list[dict]:
        """列出指定书籍已安装的组合包"""
        installed = self._read_installed(book_id)
        result = []
        for pack_id, info in installed.items():
            pack = self._packs.get(pack_id)
            if pack:
                view = self._public_view(pack)
                view["installed_at"] = info.get("installed_at")
                view["added_rules"] = info.get("added_rules", 0)
                view["added_workflows"] = info.get("added_workflows", 0)
                view["added_skills"] = info.get("added_skills", 0)
                result.append(view)
            else:
                # 组合包已不存在，仍返回基本信息
                result.append(
                    {
                        "id": pack_id,
                        "name": info.get("name", pack_id),
                        "installed_at": info.get("installed_at"),
                        "available": False,
                    }
                )
        return result

    # ─── 内部工具 ──────────────────────────────────

    def _read_installed(self, book_id: str) -> dict[str, dict]:
        """读取已安装记录"""
        data = _read_json(_installed_packs_path(book_id), {})
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _public_view(pack: dict, include_contents: bool = False) -> dict:
        """返回组合包的公开视图（默认不包含完整内容）"""
        view = {
            "id": pack.get("id", ""),
            "name": pack.get("name", ""),
            "description": pack.get("description", ""),
            "author": pack.get("author", "昆仑官方"),
            "category": pack.get("category", ""),
            "rule_ids": pack.get("rule_ids", []),
            "workflow_ids": pack.get("workflow_ids", []),
            "skill_ids": pack.get("skill_ids", []),
            "rule_count": len(pack.get("rule_contents", [])),
            "workflow_count": len(pack.get("workflow_contents", [])),
            "skill_count": len(pack.get("skill_contents", [])),
            "rating": pack.get("rating", 0.0),
            "downloads": pack.get("downloads", 0),
            "tags": pack.get("tags", []),
        }
        if include_contents:
            view["rule_contents"] = pack.get("rule_contents", [])
            view["workflow_contents"] = pack.get("workflow_contents", [])
            view["skill_contents"] = pack.get("skill_contents", [])
        return view


# ─── 全局单例 ─────────────────────────────────────────────

_engine: LocalMarketplaceEngine | None = None


def get_local_marketplace() -> LocalMarketplaceEngine:
    """获取全局本地技能包市场引擎实例"""
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = LocalMarketplaceEngine()
    return _engine
