"""
写作内容包管理器 — WritingPackManager

负责 Rule/Workflow/Skill 三类内容包的 CRUD、持久化和查询。
用户自定义包存储在 data/books/book_<id>/writing_packs.json，
内置预设在 kunlun.writing_packs.presets 中定义，运行时合并。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.writing_packs.models import PackType
from kunlun.writing_packs.presets import get_all_builtin_packs, get_builtin_pack_by_id


class WritingPackManager:
    """写作内容包管理器

    提供 Rule / Workflow / Skill 三类包的统一管理接口。
    内置包（builtin=True）不可删除，但可启用/禁用。
    用户自定义包持久化到书籍目录下的 writing_packs.json。
    """

    _instances: dict[str, WritingPackManager] = {}

    def __new__(cls, book_id: str) -> WritingPackManager:
        """单例模式：每本书一个管理器实例"""
        if book_id not in cls._instances:
            cls._instances[book_id] = super().__new__(cls)
            cls._instances[book_id]._initialized = False
        return cls._instances[book_id]

    def __init__(self, book_id: str) -> None:
        if getattr(self, "_initialized", False):
            return
        self.book_id = book_id
        self._user_packs: list[dict[str, Any]] = []
        self._load_user_packs()
        self._initialized = True

    # ─── 持久化 ────────────────────────────────────────────

    def _get_data_dir(self) -> Path:
        """获取书籍数据目录（延迟导入 config 避免循环依赖）"""
        from kunlun.config import settings

        return settings.DATA_DIR / "books" / f"book_{self.book_id}"

    def _get_packs_file(self) -> Path:
        """获取用户自定义包存储文件路径"""
        return self._get_data_dir() / "writing_packs.json"

    def _load_user_packs(self) -> None:
        """从文件加载用户自定义包"""
        packs_file = self._get_packs_file()
        if not packs_file.exists():
            self._user_packs = []
            return
        try:
            with packs_file.open(encoding="utf-8") as f:
                data = json.load(f)
            self._user_packs = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[WritingPacks] 加载用户包失败 ({self.book_id}): {e}")
            self._user_packs = []

    def _save_user_packs(self) -> None:
        """保存用户自定义包到文件"""
        packs_file = self._get_packs_file()
        try:
            packs_file.parent.mkdir(parents=True, exist_ok=True)
            with packs_file.open("w", encoding="utf-8") as f:
                json.dump(self._user_packs, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"[WritingPacks] 保存用户包失败 ({self.book_id}): {e}")

    # ─── 合并视图 ──────────────────────────────────────────

    def _get_all_packs(self) -> list[dict[str, Any]]:
        """获取内置包 + 用户自定义包的合并列表

        用户包覆盖同 ID 的内置包（用于启用/禁用状态覆盖）。
        """
        merged: dict[str, dict[str, Any]] = {}
        # 先加载内置包
        for pack in get_all_builtin_packs():
            merged[pack["id"]] = pack
        # 用户包覆盖（同 ID 时用户设置优先）
        for pack in self._user_packs:
            merged[pack["id"]] = pack
        return list(merged.values())

    def _find_pack_index(self, pack_id: str) -> int:
        """在用户包列表中查找索引，未找到返回 -1"""
        for i, pack in enumerate(self._user_packs):
            if pack.get("id") == pack_id:
                return i
        return -1

    # ─── 查询接口 ──────────────────────────────────────────

    def list_packs(self, pack_type: PackType | None = None) -> list[dict[str, Any]]:
        """列出所有包（含内置+用户自定义）

        Args:
            pack_type: 可选类型过滤

        Returns:
            包列表，每个元素为 dict
        """
        packs = self._get_all_packs()
        if pack_type is not None:
            type_value = pack_type.value if isinstance(pack_type, PackType) else pack_type
            packs = [p for p in packs if p.get("type") == type_value]
        return packs

    def get_pack(self, pack_id: str) -> dict[str, Any] | None:
        """获取单个包

        Args:
            pack_id: 包 ID

        Returns:
            包 dict，未找到返回 None
        """
        for pack in self._get_all_packs():
            if pack.get("id") == pack_id:
                return pack
        return None

    # ─── CRUD 接口 ─────────────────────────────────────────

    def create_pack(self, pack_data: dict[str, Any]) -> dict[str, Any]:
        """创建自定义包

        Args:
            pack_data: 包数据，必须包含 id/name/description/type 及类型特有字段

        Returns:
            创建后的包 dict

        Raises:
            ValueError: ID 已存在或缺少必填字段
        """
        pack_id = pack_data.get("id", "").strip()
        if not pack_id:
            raise ValueError("包 ID 不能为空")

        # 检查 ID 冲突（内置 + 用户）
        if get_builtin_pack_by_id(pack_id) is not None:
            raise ValueError(f"包 ID '{pack_id}' 已被内置包占用")
        if self._find_pack_index(pack_id) >= 0:
            raise ValueError(f"包 ID '{pack_id}' 已存在")

        # 校验必填字段
        pack_type = pack_data.get("type")
        if not pack_type:
            raise ValueError("包类型 type 不能为空")

        now = datetime.now().isoformat()
        new_pack: dict[str, Any] = {
            "id": pack_id,
            "name": pack_data.get("name", ""),
            "description": pack_data.get("description", ""),
            "type": pack_type,
            "enabled": pack_data.get("enabled", True),
            "builtin": False,
            "created_at": now,
        }

        # 按类型添加特有字段
        if pack_type == PackType.RULE.value:
            new_pack["content"] = pack_data.get("content", "")
            new_pack["category"] = pack_data.get("category", "general")
        elif pack_type == PackType.WORKFLOW.value:
            new_pack["steps"] = pack_data.get("steps", [])
            new_pack["trigger_command"] = pack_data.get("trigger_command", "")
        elif pack_type == PackType.SKILL.value:
            new_pack["knowledge"] = pack_data.get("knowledge", "")
            new_pack["trigger_scenes"] = pack_data.get("trigger_scenes", [])
        else:
            raise ValueError(f"未知包类型: {pack_type}")

        self._user_packs.append(new_pack)
        self._save_user_packs()
        logger.info(f"[WritingPacks] 创建包: {pack_id} ({pack_type})")
        return new_pack

    def update_pack(self, pack_id: str, updates: dict[str, Any]) -> bool:
        """更新包

        内置包仅允许更新 enabled 字段，其余字段更新会被拒绝。
        用户自定义包可更新所有字段。

        Args:
            pack_id: 包 ID
            updates: 更新字段

        Returns:
            是否更新成功
        """
        idx = self._find_pack_index(pack_id)
        builtin_pack = get_builtin_pack_by_id(pack_id)

        if idx >= 0:
            # 用户自定义包：允许更新所有字段
            pack = self._user_packs[idx]
            # 不允许修改 id/type/builtin
            protected_fields = {"id", "type", "builtin", "created_at"}
            for key, value in updates.items():
                if key not in protected_fields:
                    pack[key] = value
            self._save_user_packs()
            logger.info(f"[WritingPacks] 更新用户包: {pack_id}")
            return True

        if builtin_pack is not None:
            # 内置包：仅允许更新 enabled，通过创建用户覆盖记录实现
            if set(updates.keys()) <= {"enabled"}:
                override = dict(builtin_pack)
                override["enabled"] = updates.get("enabled", builtin_pack.get("enabled", True))
                override["builtin"] = True
                self._user_packs.append(override)
                self._save_user_packs()
                logger.info(f"[WritingPacks] 覆盖内置包设置: {pack_id}")
                return True
            logger.warning(f"[WritingPacks] 内置包仅允许修改 enabled: {pack_id}")
            return False

        logger.warning(f"[WritingPacks] 包不存在: {pack_id}")
        return False

    def delete_pack(self, pack_id: str) -> bool:
        """删除包

        内置包不可删除，用户自定义包可删除。

        Args:
            pack_id: 包 ID

        Returns:
            是否删除成功
        """
        if get_builtin_pack_by_id(pack_id) is not None:
            logger.warning(f"[WritingPacks] 内置包不可删除: {pack_id}")
            return False

        idx = self._find_pack_index(pack_id)
        if idx >= 0:
            del self._user_packs[idx]
            self._save_user_packs()
            logger.info(f"[WritingPacks] 删除包: {pack_id}")
            return True

        logger.warning(f"[WritingPacks] 包不存在: {pack_id}")
        return False

    def toggle_pack(self, pack_id: str, enabled: bool) -> bool:
        """启用/禁用包

        Args:
            pack_id: 包 ID
            enabled: 是否启用

        Returns:
            是否操作成功
        """
        return self.update_pack(pack_id, {"enabled": enabled})

    # ─── 业务查询接口 ──────────────────────────────────────

    def get_active_rules(self) -> list[str]:
        """获取所有启用的 Rule 内容（用于 Prompt 注入）

        Returns:
            启用的规则内容列表
        """
        packs = self._get_all_packs()
        return [
            pack["content"]
            for pack in packs
            if pack.get("type") == PackType.RULE.value
            and pack.get("enabled", True)
            and pack.get("content")
        ]

    def get_workflow_by_command(self, command: str) -> dict[str, Any] | None:
        """按触发命令查找启用的 Workflow

        Args:
            command: 触发命令，如 /revise

        Returns:
            匹配的 Workflow dict，未找到返回 None
        """
        packs = self._get_all_packs()
        for pack in packs:
            if (
                pack.get("type") == PackType.WORKFLOW.value
                and pack.get("enabled", True)
                and pack.get("trigger_command") == command
            ):
                return pack
        return None

    def get_skills_for_scene(self, scene: str) -> list[dict[str, Any]]:
        """按场景获取激活的 Skill

        Args:
            scene: 场景名称，如 world_building / combat

        Returns:
            匹配场景且启用的 Skill 列表
        """
        packs = self._get_all_packs()
        return [
            pack
            for pack in packs
            if pack.get("type") == PackType.SKILL.value
            and pack.get("enabled", True)
            and scene in pack.get("trigger_scenes", [])
        ]

    def inject_prompt_context(self, base_prompt: str, scene: str | None = None) -> str:
        """将活跃 Rule 和场景 Skill 注入到 Prompt

        Args:
            base_prompt: 原始 Prompt
            scene: 可选场景名称，用于匹配 Skill

        Returns:
            注入上下文后的完整 Prompt
        """
        sections: list[str] = []

        # 注入活跃 Rule
        active_rules = self.get_active_rules()
        if active_rules:
            rule_text = "\n\n".join(f"{i + 1}. {rule}" for i, rule in enumerate(active_rules))
            sections.append(f"【写作规则】\n{rule_text}")

        # 注入场景 Skill
        if scene:
            skills = self.get_skills_for_scene(scene)
            if skills:
                skill_parts = [
                    f"### {skill.get('name', '')}\n{skill.get('knowledge', '')}" for skill in skills
                ]
                sections.append("【专业知识】\n" + "\n\n".join(skill_parts))

        if not sections:
            return base_prompt

        context_block = "\n\n".join(sections)
        return f"{context_block}\n\n---\n\n{base_prompt}"
