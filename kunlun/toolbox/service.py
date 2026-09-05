"""
昆仑创作引擎 — 专业生成器工具箱 服务层

统一调度各生成器，提供：
- 通用生成入口（按类型分发）
- 生成结果保存到书籍项目
- 生成历史记录管理
"""
# mypy: ignore-errors

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.toolbox.models import (
    GENERATOR_LABELS,
    GENERATOR_TYPES,
    ChapterOutlineGenerateRequest,
    CharacterGenerateRequest,
    CheatGenerateRequest,
    GeneratorInfo,
    GenericGenerateRequest,
    HistoryRecord,
    NameGenerateRequest,
    OpeningGenerateRequest,
    OutlineGenerateRequest,
    SaveRequest,
    SynopsisGenerateRequest,
    TitleGenerateRequest,
)


def _get_data_dir() -> Path:
    """获取数据目录，延迟导入 settings 避免循环依赖。"""
    from kunlun.config import settings

    return settings.DATA_DIR


def _get_history_path() -> Path:
    p = _get_data_dir() / "toolbox" / "history.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_history() -> list[dict[str, Any]]:
    p = _get_history_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_history(records: list[dict[str, Any]]) -> None:
    p = _get_history_path()
    try:
        p.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning(f"[Toolbox] 保存历史失败: {e}")


def _append_history(record: HistoryRecord) -> None:
    records = _load_history()
    records.insert(0, record.model_dump(mode="json"))
    # 最多保留 500 条
    records = records[:500]
    _save_history(records)


def list_generators() -> list[GeneratorInfo]:
    """获取所有可用生成器列表。"""
    descriptions = {
        "title": "根据题材、风格、关键词生成候选书名",
        "synopsis": "根据书名、主角、核心冲突生成黄金三章格式简介",
        "outline": "根据题材、主角、冲突生成卷级大纲（三幕式/英雄之旅）",
        "chapter_outline": "根据卷大纲生成章节级细纲（场景+冲突+钩子）",
        "opening": "生成3种黄金开篇方案（冲突前置/悬念设置/场景代入）",
        "cheat": "根据题材生成金手指方案（系统/穿越/重生/异能/血脉等）",
        "name": "生成角色/地点/物品/功法名字（古风/现代/西方）",
        "character": "生成完整人设（外貌/背景/性格/动机/能力/弧光/台词）",
    }
    request_models = {
        "title": "TitleGenerateRequest",
        "synopsis": "SynopsisGenerateRequest",
        "outline": "OutlineGenerateRequest",
        "chapter_outline": "ChapterOutlineGenerateRequest",
        "opening": "OpeningGenerateRequest",
        "cheat": "CheatGenerateRequest",
        "name": "NameGenerateRequest",
        "character": "CharacterGenerateRequest",
    }
    return [
        GeneratorInfo(
            type=g,
            name=GENERATOR_LABELS[g],
            description=descriptions[g],
            request_model=request_models[g],
        )
        for g in GENERATOR_TYPES
    ]


def generate(generator_type: str, request: GenericGenerateRequest) -> dict[str, Any]:
    """
    通用生成入口，按类型分发到对应生成器。

    返回生成结果的 dict 形式，并自动记录历史。
    """
    if generator_type not in GENERATOR_TYPES:
        raise ValueError(f"未知的生成器类型: {generator_type}，可用: {', '.join(GENERATOR_TYPES)}")

    result_data: dict[str, Any]

    if generator_type == "title":
        from kunlun.toolbox.generators import generate_titles

        req = TitleGenerateRequest(
            genre=request.genre,
            style=request.style,
            keywords=request.keywords,
            count=request.count,
        )
        result = generate_titles(req)
        result_data = result.model_dump()

    elif generator_type == "synopsis":
        from kunlun.toolbox.generators import generate_synopsis

        req = SynopsisGenerateRequest(
            title=request.title or "未命名",
            genre=request.genre,
            protagonist=request.protagonist or "主角",
            core_conflict=request.core_conflict or "命运的抗争",
            word_count=request.word_count,
        )
        result = generate_synopsis(req)
        result_data = result.model_dump()

    elif generator_type == "outline":
        from kunlun.toolbox.generators import generate_outline

        structure = (
            request.structure_type
            if request.structure_type in ("three_act", "hero_journey")
            else "three_act"
        )
        req = OutlineGenerateRequest(
            genre=request.genre,
            protagonist=request.protagonist or "主角",
            core_conflict=request.core_conflict or "命运的抗争",
            structure_type=structure,  # type: ignore[arg-type]
            volume_count=request.volume_count,
        )
        result = generate_outline(req)
        result_data = result.model_dump()

    elif generator_type == "chapter_outline":
        from kunlun.toolbox.generators import generate_chapter_outline

        req = ChapterOutlineGenerateRequest(
            volume_outline=request.volume_outline or "未命名卷大纲",
            volume_title=request.volume_title,
            chapter_count=request.chapter_count,
            genre=request.genre,
        )
        result = generate_chapter_outline(req)
        result_data = result.model_dump()

    elif generator_type == "opening":
        from kunlun.toolbox.generators import generate_opening

        req = OpeningGenerateRequest(
            genre=request.genre,
            protagonist=request.protagonist or "主角",
            core_conflict=request.core_conflict or "命运的抗争",
            word_count=request.word_count,
        )
        result = generate_opening(req)
        result_data = result.model_dump()

    elif generator_type == "cheat":
        from kunlun.toolbox.generators import generate_cheats

        req = CheatGenerateRequest(
            genre=request.genre,
            count=min(request.count, 10),
        )
        result = generate_cheats(req)
        result_data = result.model_dump()

    elif generator_type == "name":
        from kunlun.toolbox.generators import generate_names

        name_type = (
            request.name_type
            if request.name_type in ("character", "location", "item", "technique")
            else "character"
        )
        name_style = (
            request.name_style
            if request.name_style in ("ancient", "modern", "western")
            else "ancient"
        )
        req = NameGenerateRequest(
            name_type=name_type,  # type: ignore[arg-type]
            style=name_style,  # type: ignore[arg-type]
            count=min(request.count, 50),
            gender=request.gender,
        )
        result = generate_names(req)
        result_data = result.model_dump()

    else:  # character
        from kunlun.toolbox.generators import generate_character

        role_type = (
            request.role_type
            if request.role_type in ("protagonist", "antagonist", "supporting")
            else "protagonist"
        )
        req = CharacterGenerateRequest(
            role_type=role_type,  # type: ignore[arg-type]
            genre=request.genre,
            core_trait=request.core_trait or "坚韧不拔",
            name=request.name,
        )
        result = generate_character(req)
        result_data = result.model_dump()

    # 记录历史
    record = HistoryRecord(
        id=str(uuid.uuid4())[:8],
        generator_type=generator_type,
        book_id=request.book_id,
        request_data=request.model_dump(exclude={"book_id"}),
        result_data=result_data,
        created_at=datetime.now(),
    )
    _append_history(record)

    return result_data


def save_result(save_req: SaveRequest) -> dict[str, Any]:
    """
    保存生成结果到当前书籍项目。

    保存到 data/books/<book_id>/toolbox/ 目录下，按生成器类型分文件。
    """
    from kunlun.config import settings

    book_dir = settings.get_book_safe_path(save_req.book_id, "toolbox")
    book_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{save_req.generator_type}_{timestamp}.json"
    filepath = book_dir / filename

    payload = {
        "generator_type": save_req.generator_type,
        "label": save_req.label,
        "result": save_req.result,
        "saved_at": datetime.now().isoformat(),
    }

    try:
        filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[Toolbox] 结果已保存: {filepath}")
        return {"success": True, "path": str(filepath), "filename": filename}
    except OSError as e:
        logger.error(f"[Toolbox] 保存失败: {e}")
        return {"success": False, "error": str(e)}


def get_history(book_id: str = "", limit: int = 50) -> list[HistoryRecord]:
    """获取生成历史，可按书籍筛选。"""
    records = _load_history()
    if book_id:
        records = [r for r in records if r.get("book_id") == book_id]
    records = records[:limit]
    return [HistoryRecord(**r) for r in records]
