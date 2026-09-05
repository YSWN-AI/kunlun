"""
昆仑创作引擎 — AI拆书案例库 服务层

提供案例的CRUD、搜索、对比分析、方法论提取等功能。
纯数据+规则实现，不调用LLM。
"""
# mypy: ignore-errors

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from kunlun.book_analysis.cases import BUILTIN_CASES
from kunlun.book_analysis.models import (
    BookAnalysisCase,
    CustomCaseCreateRequest,
    CustomCaseUpdateRequest,
)


def _get_custom_dir() -> Path:
    """获取自定义案例存储目录，不存在则创建。"""
    from kunlun.config import settings

    d = settings.DATA_DIR / "book_analysis"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_custom_cases() -> dict[str, BookAnalysisCase]:
    """从磁盘加载所有自定义案例。"""
    custom: dict[str, BookAnalysisCase] = {}
    d = _get_custom_dir()
    for f in d.glob("case_*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            case = BookAnalysisCase(**data)
            custom[case.id] = case
        except Exception:
            continue
    return custom


def _save_custom_case(case: BookAnalysisCase) -> None:
    """保存自定义案例到磁盘。"""
    d = _get_custom_dir()
    f = d / f"{case.id}.json"
    f.write_text(
        case.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _delete_custom_case(case_id: str) -> bool:
    """从磁盘删除自定义案例。"""
    d = _get_custom_dir()
    f = d / f"{case_id}.json"
    if f.exists():
        f.unlink()
        return True
    return False


def get_all_cases() -> list[BookAnalysisCase]:
    """获取所有案例（内置+自定义）。"""
    cases = list(BUILTIN_CASES)
    custom = _load_custom_cases()
    cases.extend(custom.values())
    return cases


def get_case(case_id: str) -> BookAnalysisCase | None:
    """根据ID获取单个案例。"""
    for case in BUILTIN_CASES:
        if case.id == case_id:
            return case
    custom = _load_custom_cases()
    return custom.get(case_id)


def search_cases(
    genre: str | None = None,
    platform: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[BookAnalysisCase], int]:
    """
    搜索/筛选案例，支持分页。

    Returns:
        (案例列表, 总数)
    """
    cases = get_all_cases()

    if genre:
        cases = [c for c in cases if c.genre == genre]
    if platform:
        cases = [c for c in cases if c.platform == platform]
    if tag:
        cases = [c for c in cases if tag in c.tags]
    if search:
        keyword = search.lower()
        cases = [
            c
            for c in cases
            if keyword in c.title.lower()
            or keyword in c.author.lower()
            or keyword in c.summary.lower()
            or any(keyword in t.lower() for t in c.tags)
        ]

    total = len(cases)
    start = (page - 1) * page_size
    end = start + page_size
    return cases[start:end], total


def get_categories() -> list[dict[str, Any]]:
    """获取题材分类及数量。"""
    cases = get_all_cases()
    genre_count: dict[str, int] = {}
    for case in cases:
        genre_count[case.genre] = genre_count.get(case.genre, 0) + 1

    return [
        {"genre": genre, "count": count}
        for genre, count in sorted(genre_count.items(), key=lambda x: -x[1])
    ]


def compare_cases(case_ids: list[str]) -> dict[str, Any]:
    """
    多案例对比分析，返回各维度对比矩阵。

    对比维度：叙事节奏、爽点设置、情节结构、风格指纹。
    """
    cases = [get_case(cid) for cid in case_ids]
    cases = [c for c in cases if c is not None]

    if len(cases) < 2:
        return {"success": False, "error": "至少需要2个有效案例进行对比"}

    # 叙事节奏对比
    rhythm_compare: dict[str, Any] = {}
    for phase in ["opening", "middle", "climax", "ending"]:
        phase_data: dict[str, Any] = {}
        for case in cases:
            phase_obj = getattr(case.narrative_rhythm, phase)
            phase_data[case.title] = {
                "score": phase_obj.score,
                "description": phase_obj.description,
            }
        rhythm_compare[phase] = phase_data

    # 爽点对比
    pleasure_compare: dict[str, Any] = {}
    for case in cases:
        types_count: dict[str, int] = {}
        avg_score = 0
        if case.pleasure_points:
            for pp in case.pleasure_points:
                types_count[pp.type] = types_count.get(pp.type, 0) + 1
            avg_score = sum(pp.effect_score for pp in case.pleasure_points) / len(
                case.pleasure_points
            )
        pleasure_compare[case.title] = {
            "count": len(case.pleasure_points),
            "types": types_count,
            "avg_effect_score": round(avg_score, 1),
        }

    # 情节结构对比
    plot_compare: dict[str, Any] = {}
    for case in cases:
        ps = case.plot_structure
        plot_compare[case.title] = {
            "structure_type": ps.structure_type,
            "foreshadowing_count": ps.foreshadowing_count,
            "twist_count": ps.twist_count,
            "sub_line_count": len(ps.sub_lines),
            "main_line": ps.main_line,
        }

    # 风格指纹对比（12维度评分）
    style_compare: dict[str, Any] = {}
    all_dims: set[str] = set()
    for case in cases:
        all_dims.update(case.style_fingerprint.scores.keys())
    for dim in sorted(all_dims):
        dim_data: dict[str, int] = {}
        for case in cases:
            dim_data[case.title] = case.style_fingerprint.scores.get(dim, 0)
        style_compare[dim] = dim_data

    # 人物弧光对比
    character_compare: dict[str, Any] = {}
    for case in cases:
        arc_types: dict[str, int] = {}
        for arc in case.character_arcs:
            arc_types[arc.arc_type] = arc_types.get(arc.arc_type, 0) + 1
        character_compare[case.title] = {
            "character_count": len(case.character_arcs),
            "arc_types": arc_types,
        }

    return {
        "success": True,
        "compared_count": len(cases),
        "case_titles": [c.title for c in cases],
        "narrative_rhythm": rhythm_compare,
        "pleasure_points": pleasure_compare,
        "plot_structure": plot_compare,
        "style_fingerprint": style_compare,
        "character_arcs": character_compare,
    }


def extract_methodology(case_ids: list[str]) -> dict[str, Any]:
    """
    从多个案例中提炼共性方法论。

    基于规则的方法：统计方法论关键词出现频率，
    提取高频共性技巧，并按类别分组。
    """
    cases = [get_case(cid) for cid in case_ids]
    cases = [c for c in cases if c is not None]

    if not cases:
        return {"success": False, "error": "未找到有效案例"}

    # 收集所有方法论
    all_methods: list[str] = []
    for case in cases:
        all_methods.extend(case.methodology)

    # 按关键词分类
    categories: dict[str, list[str]] = {
        "开局设计": [],
        "节奏控制": [],
        "人物塑造": [],
        "情节设计": [],
        "爽点营造": [],
        "风格写作": [],
        "结构布局": [],
        "结局处理": [],
    }

    keyword_map = {
        "开局": "开局设计",
        "开篇": "开局设计",
        "第一章": "开局设计",
        "三章": "开局设计",
        "节奏": "节奏控制",
        "章末": "节奏控制",
        "钩子": "节奏控制",
        "快慢": "节奏控制",
        "人物": "人物塑造",
        "角色": "人物塑造",
        "配角": "人物塑造",
        "人设": "人物塑造",
        "弧光": "人物塑造",
        "情节": "情节设计",
        "伏笔": "情节设计",
        "转折": "情节设计",
        "反转": "情节设计",
        "线索": "情节设计",
        "爽点": "爽点营造",
        "打脸": "爽点营造",
        "装逼": "爽点营造",
        "逆袭": "爽点营造",
        "满足": "爽点营造",
        "风格": "风格写作",
        "文笔": "风格写作",
        "对话": "风格写作",
        "描写": "风格写作",
        "语言": "风格写作",
        "结构": "结构布局",
        "主线": "结构布局",
        "支线": "结构布局",
        "世界观": "结构布局",
        "地图": "结构布局",
        "结局": "结局处理",
        "结尾": "结局处理",
        "收束": "结局处理",
        "留白": "结局处理",
    }

    for method in all_methods:
        assigned = False
        for keyword, category in keyword_map.items():
            if keyword in method:
                categories[category].append(method)
                assigned = True
                break
        if not assigned:
            categories.setdefault("其他技巧", []).append(method)

    # 去重并统计
    result_categories: list[dict[str, Any]] = []
    for cat_name, methods in categories.items():
        # 去重（保留顺序）
        seen: set[str] = set()
        unique_methods: list[str] = []
        for m in methods:
            if m not in seen:
                seen.add(m)
                unique_methods.append(m)
        if unique_methods:
            result_categories.append(
                {
                    "category": cat_name,
                    "count": len(unique_methods),
                    "methods": unique_methods,
                }
            )

    # 提取跨案例共性（出现在多个案例中的方法论模式）
    cross_case_patterns: list[str] = []
    pattern_keywords = [
        ("开局三章定生死", "开局"),
        ("章末钩子定律", "钩子"),
        ("打脸延迟满足", "延迟"),
        ("升级体系可视化", "升级"),
        ("配角工具化", "配角"),
        ("世界观渐进展开", "世界观"),
        ("情感线服务主线", "情感"),
        ("留白式叙事", "留白"),
        ("双线并行结构", "双线"),
        ("时间跨度制造宿命感", "时间"),
    ]
    for pattern_name, keyword in pattern_keywords:
        found_in = 0
        for case in cases:
            if any(keyword in m for m in case.methodology):
                found_in += 1
        if found_in >= 2:
            cross_case_patterns.append(f"{pattern_name}（{found_in}/{len(cases)}个案例共通）")

    return {
        "success": True,
        "case_count": len(cases),
        "case_titles": [c.title for c in cases],
        "total_methods": len(all_methods),
        "unique_methods": len(set(all_methods)),
        "categories": result_categories,
        "cross_case_patterns": cross_case_patterns,
    }


def create_custom_case(req: CustomCaseCreateRequest) -> BookAnalysisCase:
    """创建自定义拆书案例。"""
    case_id = f"case_custom_{uuid.uuid4().hex[:12]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    case = BookAnalysisCase(
        id=case_id,
        title=req.title,
        author=req.author,
        genre=req.genre,
        platform=req.platform,
        tags=req.tags,
        word_count=req.word_count,
        status=req.status,
        summary=req.summary,
        narrative_rhythm=req.narrative_rhythm,
        pleasure_points=req.pleasure_points,
        plot_structure=req.plot_structure,
        character_arcs=req.character_arcs,
        style_fingerprint=req.style_fingerprint,
        methodology=req.methodology,
        key_quotes=req.key_quotes,
        created_at=now,
        is_custom=True,
    )
    _save_custom_case(case)
    return case


def update_custom_case(case_id: str, req: CustomCaseUpdateRequest) -> BookAnalysisCase | None:
    """更新自定义拆书案例。"""
    existing = get_case(case_id)
    if existing is None or not existing.is_custom:
        return None

    update_data = req.model_dump(exclude_unset=True)
    updated_dict = existing.model_dump()
    updated_dict.update(update_data)
    updated_dict["id"] = case_id
    updated_dict["is_custom"] = True

    updated = BookAnalysisCase(**updated_dict)
    _save_custom_case(updated)
    return updated


def delete_custom_case(case_id: str) -> bool:
    """删除自定义拆书案例。"""
    existing = get_case(case_id)
    if existing is None or not existing.is_custom:
        return False
    return _delete_custom_case(case_id)
