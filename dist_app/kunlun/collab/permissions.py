"""
权限系统 — 协作写作的访问控制

角色层级:
  Owner    - 完全控制（创建者/转让）
  Editor   - 读写内容 + 管理评论
  Commenter - 只读内容 + 添加评论
  Viewer   - 只读内容

权限检查:
  - can_read(role, resource) -> bool
  - can_write(role, resource) -> bool
  - can_comment(role, resource) -> bool
  - can_manage(role, resource) -> bool
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PermissionRole(StrEnum):
    """协作角色"""

    OWNER = "owner"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"


class Permission(StrEnum):
    """权限枚举"""

    READ = "read"
    WRITE = "write"
    COMMENT = "comment"
    MANAGE = "manage"
    SHARE = "share"
    DELETE = "delete"


@dataclass
class PermissionEntry:
    """单个用户的权限配置"""

    user_id: str
    role: PermissionRole = PermissionRole.VIEWER
    granted_by: str = ""
    granted_at: float = 0.0


@dataclass
class PermissionConfig:
    """资源权限配置"""

    resource_id: str
    owner_id: str
    entries: dict[str, PermissionEntry] = field(default_factory=dict)
    is_public: bool = False

    def get_role(self, user_id: str) -> PermissionRole:
        """获取用户在此资源上的角色"""
        if user_id == self.owner_id:
            return PermissionRole.OWNER
        entry = self.entries.get(user_id)
        return entry.role if entry else PermissionRole.VIEWER

    def can(self, user_id: str, permission: Permission) -> bool:
        """检查用户是否有某权限"""
        role = self.get_role(user_id)
        return _ROLE_PERMISSIONS.get(role, {}).get(permission, False)


# 角色 → 权限映射
_ROLE_PERMISSIONS: dict[PermissionRole, dict[Permission, bool]] = {
    PermissionRole.OWNER: {
        Permission.READ: True,
        Permission.WRITE: True,
        Permission.COMMENT: True,
        Permission.MANAGE: True,
        Permission.SHARE: True,
        Permission.DELETE: True,
    },
    PermissionRole.EDITOR: {
        Permission.READ: True,
        Permission.WRITE: True,
        Permission.COMMENT: True,
        Permission.MANAGE: False,
        Permission.SHARE: False,
        Permission.DELETE: False,
    },
    PermissionRole.COMMENTER: {
        Permission.READ: True,
        Permission.WRITE: False,
        Permission.COMMENT: True,
        Permission.MANAGE: False,
        Permission.SHARE: False,
        Permission.DELETE: False,
    },
    PermissionRole.VIEWER: {
        Permission.READ: True,
        Permission.WRITE: False,
        Permission.COMMENT: False,
        Permission.MANAGE: False,
        Permission.SHARE: False,
        Permission.DELETE: False,
    },
}


class PermissionManager:
    """权限管理器

    管理多个资源的权限配置，提供权限检查接口。

    用法:
        pm = PermissionManager()
        pm.create_resource("chapter_42", owner_id="user_001")
        pm.grant("chapter_42", "user_002", PermissionRole.EDITOR)

        if pm.can_write("chapter_42", "user_002"):
            # 允许编辑
            ...
    """

    def __init__(self):
        self._resources: dict[str, PermissionConfig] = {}

    def create_resource(
        self,
        resource_id: str,
        owner_id: str,
        is_public: bool = False,
    ) -> PermissionConfig:
        """创建资源权限"""
        config = PermissionConfig(
            resource_id=resource_id,
            owner_id=owner_id,
            is_public=is_public,
        )
        self._resources[resource_id] = config
        return config

    def get_resource(self, resource_id: str) -> PermissionConfig | None:
        """获取资源权限配置"""
        return self._resources.get(resource_id)

    def grant(
        self,
        resource_id: str,
        user_id: str,
        role: PermissionRole,
        granted_by: str = "",
    ) -> bool:
        """授予用户权限"""
        import time

        config = self._resources.get(resource_id)
        if not config:
            return False
        config.entries[user_id] = PermissionEntry(
            user_id=user_id,
            role=role,
            granted_by=granted_by,
            granted_at=time.time(),
        )
        return True

    def revoke(self, resource_id: str, user_id: str) -> bool:
        """撤销用户权限"""
        config = self._resources.get(resource_id)
        if not config:
            return False
        config.entries.pop(user_id, None)
        return True

    def transfer_ownership(self, resource_id: str, new_owner_id: str) -> bool:
        """转让所有权"""
        config = self._resources.get(resource_id)
        if not config:
            return False
        config.owner_id = new_owner_id
        config.entries.pop(new_owner_id, None)
        return True

    def list_collaborators(self, resource_id: str) -> list[dict[str, Any]]:
        """列出协作者"""
        config = self._resources.get(resource_id)
        if not config:
            return []
        return [
            {
                "user_id": uid,
                "role": entry.role.value,
                "granted_by": entry.granted_by,
                "granted_at": entry.granted_at,
            }
            for uid, entry in config.entries.items()
        ]

    def can_read(self, resource_id: str, user_id: str) -> bool:
        return self._check(resource_id, user_id, Permission.READ)

    def can_write(self, resource_id: str, user_id: str) -> bool:
        return self._check(resource_id, user_id, Permission.WRITE)

    def can_comment(self, resource_id: str, user_id: str) -> bool:
        return self._check(resource_id, user_id, Permission.COMMENT)

    def can_manage(self, resource_id: str, user_id: str) -> bool:
        return self._check(resource_id, user_id, Permission.MANAGE)

    def _check(self, resource_id: str, user_id: str, permission: Permission) -> bool:
        config = self._resources.get(resource_id)
        if not config:
            return False
        if config.is_public and permission == Permission.READ:
            return True
        return config.can(user_id, permission)

    def delete_resource(self, resource_id: str) -> bool:
        return self._resources.pop(resource_id, None) is not None
