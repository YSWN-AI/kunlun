"""
适配器管理器 — 文件级持久化 + 模型路由集成

与 FineTuneEngine 的内存级适配器管理并存，本模块提供：
- 适配器目录结构：data/adapters/<name>/adapter_config.json + metadata.json
- 注册/加载/列出/激活/删除/合并/导出/导入
- 与 gacha/model_router 的集成接口
- 所有元数据持久化到 JSON，支持重启恢复
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from kunlun.finetune import AdapterInfo, AdapterType


class AdapterManager:
    """LoRA 适配器文件级管理器

    目录结构:
        data/adapters/
            <adapter_name>/
                adapter_config.json    # LoRA 配置
                adapter_model.safetensors  # 权重占位
                metadata.json          # 元数据
            active_adapter.json        # 当前激活的适配器

    用法:
        mgr = AdapterManager("data/adapters")
        info = mgr.register_adapter("my_style", "qwen3:14b", AdapterType.STYLE)
        mgr.activate_adapter("my_style")
        active = mgr.get_active_adapter()
    """

    def __init__(self, adapters_dir: str = "data/adapters") -> None:
        self.adapters_dir = Path(adapters_dir)
        self.adapters_dir.mkdir(parents=True, exist_ok=True)
        self._active_file = self.adapters_dir / "active_adapter.json"

    # ── 注册 ──────────────────────────────────────

    def register_adapter(
        self,
        name: str,
        base_model: str,
        adapter_type: AdapterType = AdapterType.STYLE,
        source_dataset: str = "",
        description: str = "",
        tags: list[str] | None = None,
    ) -> AdapterInfo:
        """注册新适配器（创建目录 + 元数据）

        Args:
            name: 适配器名称
            base_model: 基础模型
            adapter_type: 适配器类型
            source_dataset: 来源数据集路径
            description: 描述
            tags: 标签列表

        Returns:
            AdapterInfo 实例
        """
        adapter_dir = self.adapters_dir / name
        adapter_dir.mkdir(parents=True, exist_ok=True)

        info = AdapterInfo(
            name=name,
            base_model=base_model,
            adapter_type=adapter_type,
            path=str(adapter_dir),
            description=description,
            tags=tags or [],
            created_at=time.time(),
        )

        # 写入 adapter_config.json（LoRA 配置占位）
        config_data = {
            "name": name,
            "base_model": base_model,
            "adapter_type": str(adapter_type),
            "rank": 16,
            "alpha": 32,
            "dropout": 0.05,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "source_dataset": source_dataset,
        }
        (adapter_dir / "adapter_config.json").write_text(
            json.dumps(config_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 写入 metadata.json
        self._write_metadata(adapter_dir, info)

        # 创建权重占位文件
        placeholder = adapter_dir / "adapter_model.safetensors"
        if not placeholder.exists():
            placeholder.write_bytes(b"")

        return info

    # ── 加载 ──────────────────────────────────────

    def load_adapter(self, name: str) -> AdapterInfo | None:
        """加载适配器元数据

        Returns:
            AdapterInfo 或 None（不存在时）
        """
        adapter_dir = self.adapters_dir / name
        meta_path = adapter_dir / "metadata.json"

        if not meta_path.exists():
            return None

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        return self._dict_to_adapter_info(data)

    # ── 列出 ──────────────────────────────────────

    def list_adapters(
        self, adapter_type: AdapterType | None = None
    ) -> list[AdapterInfo]:
        """列出所有适配器

        Args:
            adapter_type: 按类型过滤，None 则全部

        Returns:
            AdapterInfo 列表
        """
        result: list[AdapterInfo] = []

        if not self.adapters_dir.exists():
            return result

        for item in self.adapters_dir.iterdir():
            if not item.is_dir():
                continue
            meta_path = item / "metadata.json"
            if not meta_path.exists():
                continue

            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                info = self._dict_to_adapter_info(data)
                if adapter_type is None or info.adapter_type == adapter_type:
                    # 检查是否激活
                    info.is_active = self._is_active(name=info.name)
                    result.append(info)
            except (OSError, json.JSONDecodeError):
                continue

        return result

    # ── 激活/取消激活 ─────────────────────────────

    def activate_adapter(self, name: str) -> bool:
        """激活适配器（写入 active_adapter.json）

        Returns:
            True 表示成功
        """
        adapter_dir = self.adapters_dir / name
        if not adapter_dir.exists():
            return False

        active_data = {
            "name": name,
            "activated_at": time.time(),
            "path": str(adapter_dir),
        }
        self._active_file.write_text(
            json.dumps(active_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    def get_active_adapter(self) -> AdapterInfo | None:
        """获取当前激活的适配器"""
        if not self._active_file.exists():
            return None

        try:
            data = json.loads(self._active_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        name = data.get("name", "")
        if not name:
            return None

        info = self.load_adapter(name)
        if info:
            info.is_active = True
        return info

    def deactivate_adapter(self) -> None:
        """取消激活"""
        if self._active_file.exists():
            self._active_file.unlink()

    # ── 删除 ──────────────────────────────────────

    def delete_adapter(self, name: str) -> bool:
        """删除适配器（删除目录）

        Returns:
            True 表示成功
        """
        adapter_dir = self.adapters_dir / name
        if not adapter_dir.exists():
            return False

        # 如果是激活状态，先取消
        active = self.get_active_adapter()
        if active and active.name == name:
            self.deactivate_adapter()

        shutil.rmtree(adapter_dir, ignore_errors=True)
        return True

    # ── 合并 ──────────────────────────────────────

    def merge_adapters(
        self,
        adapter_names: list[str],
        merged_name: str,
        weights: list[float] | None = None,
    ) -> AdapterInfo | None:
        """合并多个适配器（加权平均，创建合并适配器元数据）

        Args:
            adapter_names: 要合并的适配器名称列表
            merged_name: 合并后适配器名称
            weights: 权重列表，None 则等权

        Returns:
            合并后的 AdapterInfo，失败返回 None
        """
        if not adapter_names:
            return None

        # 加载所有适配器
        infos: list[AdapterInfo] = []
        for name in adapter_names:
            info = self.load_adapter(name)
            if info is None:
                return None
            infos.append(info)

        # 默认等权
        if weights is None:
            weights = [1.0 / len(infos)] * len(infos)
        elif len(weights) != len(infos):
            return None

        # 归一化权重
        total = sum(weights)
        if total == 0:
            return None
        weights = [w / total for w in weights]

        # 以第一个适配器为基础
        base = infos[0]
        merged_dir = self.adapters_dir / merged_name
        merged_dir.mkdir(parents=True, exist_ok=True)

        # 加权平均训练步数和 loss
        avg_steps = sum(
            info.trained_steps * w for info, w in zip(infos, weights, strict=False)
        )
        avg_loss = sum(
            info.training_loss * w for info, w in zip(infos, weights, strict=False)
        )

        merged_info = AdapterInfo(
            name=merged_name,
            base_model=base.base_model,
            adapter_type=base.adapter_type,
            path=str(merged_dir),
            description=f"Merged from: {', '.join(adapter_names)} (weights: {weights})",
            tags=list({tag for info in infos for tag in info.tags}),
            trained_steps=int(avg_steps),
            training_loss=round(avg_loss, 4),
            created_at=time.time(),
        )

        # 写入合并配置
        config_data = {
            "name": merged_name,
            "base_model": base.base_model,
            "adapter_type": str(base.adapter_type),
            "merged_from": adapter_names,
            "merge_weights": weights,
            "rank": 16,
            "alpha": 32,
        }
        (merged_dir / "adapter_config.json").write_text(
            json.dumps(config_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._write_metadata(merged_dir, merged_info)

        # 权重占位
        placeholder = merged_dir / "adapter_model.safetensors"
        if not placeholder.exists():
            placeholder.write_bytes(b"")

        return merged_info

    # ── 导出/导入 ─────────────────────────────────

    def export_adapter(self, name: str, output_dir: str) -> str:
        """导出适配器（复制目录到输出路径）

        Returns:
            导出路径
        """
        adapter_dir = self.adapters_dir / name
        if not adapter_dir.exists():
            return ""

        out_path = Path(output_dir) / name
        if out_path.exists():
            shutil.rmtree(out_path, ignore_errors=True)
        shutil.copytree(adapter_dir, out_path)
        return str(out_path)

    def import_adapter(
        self, source_dir: str, name: str | None = None
    ) -> AdapterInfo | None:
        """导入适配器

        Args:
            source_dir: 源适配器目录
            name: 重命名，None 则使用原目录名

        Returns:
            导入后的 AdapterInfo
        """
        src = Path(source_dir)
        if not src.exists() or not src.is_dir():
            return None

        meta_path = src / "metadata.json"
        if not meta_path.exists():
            return None

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        target_name = name or data.get("name", src.name)
        target_dir = self.adapters_dir / target_name

        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        shutil.copytree(src, target_dir)

        # 更新元数据中的名称和路径
        info = self._dict_to_adapter_info(data)
        info.name = target_name
        info.path = str(target_dir)
        self._write_metadata(target_dir, info)

        return info

    # ── 更新元数据 ────────────────────────────────

    def update_adapter_metadata(self, name: str, **kwargs: Any) -> bool:
        """更新适配器元数据

        Args:
            name: 适配器名称
            **kwargs: 要更新的字段

        Returns:
            True 表示成功
        """
        adapter_dir = self.adapters_dir / name
        meta_path = adapter_dir / "metadata.json"

        if not meta_path.exists():
            return False

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        # 允许更新的字段
        allowed_fields = {
            "description",
            "tags",
            "trained_steps",
            "training_loss",
            "eval_loss",
            "size_bytes",
            "version",
            "base_model",
        }

        for key, value in kwargs.items():
            if key in allowed_fields:
                data[key] = value

        meta_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    # ── 统计 ──────────────────────────────────────

    def get_adapter_stats(self) -> dict[str, Any]:
        """适配器库统计

        Returns:
            总数、按类型分布、激活状态、总大小估算
        """
        adapters = self.list_adapters()
        type_dist: dict[str, int] = {}
        total_size = 0

        for info in adapters:
            type_str = str(info.adapter_type)
            type_dist[type_str] = type_dist.get(type_str, 0) + 1

            # 估算目录大小
            adapter_dir = Path(info.path)
            if adapter_dir.exists():
                for f in adapter_dir.iterdir():
                    if f.is_file():
                        total_size += f.stat().st_size

        active = self.get_active_adapter()

        return {
            "total": len(adapters),
            "by_type": type_dist,
            "active_adapter": active.name if active else None,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    # ── 模型路由集成 ──────────────────────────────

    def get_router_config(self) -> dict[str, Any]:
        """返回模型路由配置（当前激活适配器对应的路由参数）

        Returns:
            路由配置字典，无激活适配器时返回空字典
        """
        active = self.get_active_adapter()
        if not active:
            return {}

        return {
            "adapter_name": active.name,
            "base_model": active.base_model,
            "adapter_type": str(active.adapter_type),
            "adapter_path": active.path,
            "use_adapter": True,
            "adapter_config": {
                "rank": 16,
                "alpha": 32,
                "dropout": 0.05,
            },
        }

    def apply_to_model_router(self, model_router: Any) -> bool:
        """将激活适配器应用到模型路由器

        通过 hasattr 检查，不硬依赖 gacha 模块。
        如果 model_router 不支持适配器，返回 False 但不报错。

        Args:
            model_router: 模型路由器实例

        Returns:
            True 表示成功应用
        """
        active = self.get_active_adapter()
        if not active:
            return False

        router_config = self.get_router_config()

        # 尝试设置适配器属性
        if hasattr(model_router, "set_adapter"):
            try:
                model_router.set_adapter(router_config)
                return True
            except Exception:
                return False

        # 尝试直接设置属性
        if hasattr(model_router, "active_adapter"):
            try:
                model_router.active_adapter = router_config
                return True
            except Exception:
                return False

        # 尝试添加到配置字典
        if hasattr(model_router, "config") and isinstance(model_router.config, dict):
            try:
                model_router.config["adapter"] = router_config
                return True
            except Exception:
                return False

        return False

    # ── 内部工具 ──────────────────────────────────

    @staticmethod
    def _write_metadata(adapter_dir: Path, info: AdapterInfo) -> None:
        """写入 metadata.json"""
        data = {
            "name": info.name,
            "base_model": info.base_model,
            "adapter_type": str(info.adapter_type),
            "version": info.version,
            "created_at": info.created_at,
            "trained_steps": info.trained_steps,
            "training_loss": info.training_loss,
            "eval_loss": info.eval_loss,
            "size_bytes": info.size_bytes,
            "path": str(adapter_dir),
            "tags": info.tags,
            "description": info.description,
        }
        (adapter_dir / "metadata.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _dict_to_adapter_info(data: dict[str, Any]) -> AdapterInfo:
        """从字典构建 AdapterInfo"""
        try:
            adapter_type = AdapterType(data.get("adapter_type", "style"))
        except ValueError:
            adapter_type = AdapterType.STYLE

        return AdapterInfo(
            name=data.get("name", ""),
            base_model=data.get("base_model", ""),
            adapter_type=adapter_type,
            version=data.get("version", 1),
            created_at=data.get("created_at", time.time()),
            trained_steps=data.get("trained_steps", 0),
            training_loss=data.get("training_loss", 0.0),
            eval_loss=data.get("eval_loss", 0.0),
            size_bytes=data.get("size_bytes", 0),
            path=data.get("path", ""),
            tags=data.get("tags", []),
            description=data.get("description", ""),
        )

    def _is_active(self, name: str) -> bool:
        """检查适配器是否处于激活状态"""
        if not self._active_file.exists():
            return False
        try:
            data = json.loads(self._active_file.read_text(encoding="utf-8"))
            return data.get("name") == name
        except (OSError, json.JSONDecodeError):
            return False
