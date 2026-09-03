"""
风格库管理 — 多风格指纹的存储、检索与对比

提供 StyleLibrary 类，用于管理多个命名风格指纹，支持:
- 添加/获取/删除/列出风格
- 目标风格与库中所有风格的批量对比
- JSON 持久化（文件 / 书籍目录）

使用方式:
    from kunlun.style.library import style_library

    # 添加风格
    style_library.add(fp1)
    style_library.add(fp2)

    # 对比
    results = style_library.compare_all(target_fp)

    # 持久化
    style_library.save("styles.json")
    style_library.load("styles.json")
"""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from kunlun.config import settings
from kunlun.style.fingerprint import StyleFingerprint


class StyleLibrary:
    """风格库 — 管理多个命名风格指纹

    支持增删查改、批量对比和持久化。
    """

    def __init__(self):
        self.fingerprints: dict[str, StyleFingerprint] = {}

    def add(self, fp: StyleFingerprint) -> None:
        """添加风格指纹

        Args:
            fp: 风格指纹（name字段作为键）
        """
        if not fp.name:
            logger.warning("[StyleLibrary] 指纹name为空，跳过添加")
            return
        self.fingerprints[fp.name] = fp
        logger.info(f"[StyleLibrary] 已添加风格: {fp.name}")

    def get(self, name: str) -> StyleFingerprint | None:
        """获取指定名称的风格指纹

        Args:
            name: 风格名称

        Returns:
            StyleFingerprint 或 None
        """
        return self.fingerprints.get(name)

    def remove(self, name: str) -> bool:
        """删除指定名称的风格指纹

        Args:
            name: 风格名称

        Returns:
            True 如果删除成功，False 如果不存在
        """
        if name in self.fingerprints:
            del self.fingerprints[name]
            logger.info(f"[StyleLibrary] 已删除风格: {name}")
            return True
        logger.warning(f"[StyleLibrary] 风格不存在: {name}")
        return False

    def list_all(self) -> list[str]:
        """列出所有风格名称

        Returns:
            风格名称列表
        """
        return list(self.fingerprints.keys())

    def compare_all(self, target: StyleFingerprint) -> list[tuple[str, float]]:
        """目标风格与库中所有风格对比，返回(名称, 相似度)排序

        优先使用 cosine_similarity（基于feature_vector），
        若向量为空则回退到 compare() 加权相似度。

        Args:
            target: 目标风格指纹

        Returns:
            (名称, 相似度) 列表，按相似度降序排列
        """
        results: list[tuple[str, float]] = []
        for name, fp in self.fingerprints.items():
            if target.feature_vector and fp.feature_vector:
                sim = target.cosine_similarity(fp)
            else:
                # 回退到加权相似度
                from kunlun.style.fingerprint import style_analyzer

                sim = style_analyzer.compare(target, fp)
            results.append((name, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def save(self, filepath: str) -> None:
        """保存风格库到JSON文件

        Args:
            filepath: 文件路径
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for name, fp in self.fingerprints.items():
            fp_data = {k: v for k, v in fp.__dict__.items() if not k.startswith("_")}
            # 序列化 tuple 为 list
            if "top_words" in fp_data:
                fp_data["top_words"] = [[w, c] for w, c in fp_data["top_words"]]
            data[name] = fp_data

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[StyleLibrary] 风格库已保存: {path} ({len(data)}个风格)")

    def load(self, filepath: str) -> None:
        """从JSON文件加载风格库

        Args:
            filepath: 文件路径
        """
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"[StyleLibrary] 文件不存在: {path}")
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.fingerprints.clear()
            for name, fp_data in data.items():
                fp = StyleFingerprint()
                for k, v in fp_data.items():
                    if hasattr(fp, k):
                        if k == "top_words" and isinstance(v, list):
                            v = [(item[0], item[1]) for item in v if isinstance(item, list)]  # noqa: PLW2901
                        setattr(fp, k, v)
                self.fingerprints[name] = fp
            logger.info(f"[StyleLibrary] 风格库已加载: {path} ({len(self.fingerprints)}个风格)")
        except Exception as e:
            logger.error(f"[StyleLibrary] 风格库加载失败: {e}")

    def save_to_book(self, book_id: str) -> None:
        """保存到书籍目录 data/style/{book_id}/library.json

        Args:
            book_id: 作品ID
        """
        path = settings.DATA_DIR / "style" / book_id / "library.json"
        self.save(str(path))

    def load_from_book(self, book_id: str) -> None:
        """从书籍目录加载 data/style/{book_id}/library.json

        Args:
            book_id: 作品ID
        """
        path = settings.DATA_DIR / "style" / book_id / "library.json"
        self.load(str(path))


# ── 全局单例 ──
style_library = StyleLibrary()
