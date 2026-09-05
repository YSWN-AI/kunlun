"""
昆仑创作引擎 — 桌面工作台 API 路由
统一前缀 /api/v1/workstation，为桌面端创作工作台提供六维质量、AI率、风格学习、
记忆系统、辩论审校、读者模拟等能力。
"""

import dataclasses
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/workstation", tags=["桌面工作台"])


# ---------------------------------------------------------------------------
# 辅助函数：递归将 dataclass / Enum / 嵌套结构转为可 JSON 序列化的 dict
# ---------------------------------------------------------------------------
def _to_dict(obj: Any) -> Any:
    """递归转换对象为可序列化结构，处理 Enum → .value、dataclass → dict。"""
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_dict(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------
class TextChapterRequest(BaseModel):
    text: str = Field(..., description="待分析文本")
    chapter: int = Field(default=0, description="章节号")


class AIRateRequest(BaseModel):
    text: str = Field(..., description="待检测文本")
    threshold: float = Field(default=35.0, description="AI率阈值")


class HumanizeRequest(BaseModel):
    text: str = Field(..., description="待去AI味文本")
    aggressive: float = Field(default=0.5, description="去AI味强度 0.0-1.0")


class StyleExtractRequest(BaseModel):
    text: str = Field(..., description="待提取风格的文本")
    author_name: str = Field(default="", description="作者名称（可选）")


class StyleSimilarityRequest(BaseModel):
    text1: str = Field(..., description="文本1")
    text2: str = Field(..., description="文本2")


class MemoryQueryRequest(BaseModel):
    book_id: str = Field(default="default", description="书籍ID")


class MemoryAddRequest(BaseModel):
    book_id: str = Field(default="default", description="书籍ID")
    content: str = Field(..., description="记忆内容")
    layer: str = Field(
        default="working", description="记忆层级: working/episodic/semantic/procedural"
    )


class DebateReviewRequest(BaseModel):
    text: str = Field(..., description="待审校文本")
    chapter: int = Field(default=0, description="章节号")
    target_score: float = Field(default=85.0, description="目标分数")


# ---------------------------------------------------------------------------
# 六维质量分析
# ---------------------------------------------------------------------------
@router.post("/six-dim", summary="六维质量分析")
async def six_dim_analysis(req: TextChapterRequest) -> dict:
    """对文本进行六维质量分析（情节/人物/语言/节奏/设定/情感）。"""
    try:
        from kunlun.quality import six_dim_dashboard

        report = six_dim_dashboard.analyze(req.text, req.chapter)
        return {"success": True, "report": _to_dict(report)}
    except Exception as e:
        logger.error(f"[workstation] six-dim 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# AI率检测
# ---------------------------------------------------------------------------
@router.post("/ai-rate", summary="AI率检测")
async def ai_rate_detect(req: AIRateRequest) -> dict:
    """检测文本的AI生成概率。"""
    try:
        from kunlun.ai_rate import detect_ai_rate

        report = detect_ai_rate(req.text, req.threshold)
        return {"success": True, "report": _to_dict(report)}
    except Exception as e:
        logger.error(f"[workstation] ai-rate 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# AI率去AI味（人文化）
# ---------------------------------------------------------------------------
@router.post("/ai-rate/humanize", summary="去AI味（人文化）")
async def ai_rate_humanize(req: HumanizeRequest) -> dict:
    """对文本进行去AI味人文化处理。"""
    try:
        from kunlun.ai_rate import humanize_text

        result = humanize_text(req.text, req.aggressive)
        return {"success": True, "result": _to_dict(result)}
    except Exception as e:
        logger.error(f"[workstation] ai-rate/humanize 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 风格学习 - 提取风格指纹
# ---------------------------------------------------------------------------
@router.post("/style/extract", summary="提取风格指纹")
async def style_extract(req: StyleExtractRequest) -> dict:
    """从文本中提取作者风格指纹。"""
    try:
        from kunlun.style_learner import extract_style_fingerprint

        fingerprint = extract_style_fingerprint(req.text, req.author_name)
        return {"success": True, "fingerprint": _to_dict(fingerprint)}
    except Exception as e:
        logger.error(f"[workstation] style/extract 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 风格学习 - 预设风格列表
# ---------------------------------------------------------------------------
@router.get("/style/presets", summary="预设风格列表")
async def style_presets() -> dict:
    """获取系统内置的预设风格列表。"""
    try:
        from kunlun.style_learner import list_preset_styles

        styles = list_preset_styles()
        return {"success": True, "styles": styles}
    except Exception as e:
        logger.error(f"[workstation] style/presets 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 风格学习 - 风格相似度对比
# ---------------------------------------------------------------------------
@router.post("/style/similarity", summary="风格相似度对比")
async def style_similarity(req: StyleSimilarityRequest) -> dict:
    """计算两段文本的风格相似度。"""
    try:
        from kunlun.style_learner import calculate_style_similarity

        result = calculate_style_similarity(req.text1, req.text2)
        return {"success": True, "result": _to_dict(result)}
    except Exception as e:
        logger.error(f"[workstation] style/similarity 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 记忆系统 - 查询
# ---------------------------------------------------------------------------
@router.post("/memory/query", summary="记忆系统查询")
async def memory_query(req: MemoryQueryRequest) -> dict:
    """查询指定书籍的记忆系统状态摘要。"""
    try:
        from kunlun.memory.engine import create_memory_manager

        mm = create_memory_manager(req.book_id)
        # 汇总各层记忆的可序列化状态
        memory_state: dict[str, Any] = {
            "book_id": req.book_id,
            "token_budget": mm.token_budget,
            "enhanced_context": mm.get_enhanced_context(),
        }
        # 工作记忆
        try:
            memory_state["working"] = _to_dict(mm.working.to_dict())
        except Exception:
            memory_state["working"] = {}
        # 情节记忆摘要
        try:
            memory_state["episodic"] = _to_dict(mm.episodic.to_dict())
        except Exception:
            memory_state["episodic"] = {}
        # 语义记忆摘要
        try:
            memory_state["semantic"] = _to_dict(mm.semantic.to_dict())
        except Exception:
            memory_state["semantic"] = {}
        # 程序记忆摘要
        try:
            memory_state["procedural"] = _to_dict(mm.procedural.to_dict())
        except Exception:
            memory_state["procedural"] = {}

        return {"success": True, "memory": memory_state}
    except Exception as e:
        logger.error(f"[workstation] memory/query 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 记忆系统 - 添加记忆
# ---------------------------------------------------------------------------
@router.post("/memory/add", summary="添加记忆")
async def memory_add(req: MemoryAddRequest) -> dict:
    """向指定书籍的记忆系统添加一条记忆。"""
    try:
        import time
        import uuid

        from kunlun.memory.engine import MemoryImportance, create_memory_manager

        mm = create_memory_manager(req.book_id)
        memory_id = f"mem_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        layer = req.layer.lower()
        if layer == "working":
            mm.working.add_note(req.content, importance=MemoryImportance.MEDIUM)
        elif layer == "episodic":
            try:
                from kunlun.memory.engine import EpisodicEvent

                event = EpisodicEvent(
                    id=memory_id,
                    chapter=0,
                    scene="manual",
                    summary=req.content,
                    participants=[],
                    location="",
                    event_type="manual_note",
                    emotional_arc="neutral",
                    plot_relevance=0.5,
                    foreshadowing=[],
                    resolved_hooks=[],
                    importance=MemoryImportance.MEDIUM,
                )
                mm.episodic.add_event(event)
            except Exception:
                pass
        elif layer == "semantic":
            # 语义层通过实体提取添加
            from kunlun.memory.engine import extract_entities_from_text

            entities = extract_entities_from_text(req.content)
            for ent in entities:
                if hasattr(mm.semantic, "add_entity"):
                    try:
                        from kunlun.memory.engine import SemanticEntity

                        mm.semantic.add_entity(SemanticEntity(**ent))
                    except Exception:
                        pass
        elif layer == "procedural":
            if hasattr(mm.procedural, "add_pattern"):
                try:
                    import time

                    from kunlun.memory.engine import ProceduralPattern

                    pattern = ProceduralPattern(
                        id=f"pattern_{int(time.time() * 1000)}",
                        name=req.content[:50],
                        pattern_type="custom",
                        description=req.content,
                        trigger_conditions=[],
                        template=req.content,
                        examples=[],
                        effectiveness=0.5,
                        usage_count=0,
                        author_preference=0.5,
                        tags=[],
                    )
                    mm.procedural.add_pattern(pattern)
                except Exception:
                    pass
        else:
            # 默认写入工作记忆
            mm.working.add_note(req.content, importance=MemoryImportance.MEDIUM)

        # 尝试持久化
        try:
            save_dir = Path("data/memory/workstation")
            save_dir.mkdir(parents=True, exist_ok=True)
            mm.save(str(save_dir / f"{req.book_id}_memory.json"))
        except Exception:
            pass

        return {"success": True, "added": True, "id": memory_id, "layer": layer}
    except Exception as e:
        logger.error(f"[workstation] memory/add 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 辩论审校
# ---------------------------------------------------------------------------
@router.post("/debate-review", summary="辩论审校")
async def debate_review_endpoint(req: DebateReviewRequest) -> dict:
    """通过多Agent辩论对文本进行深度审校。"""
    try:
        from kunlun.debate_review import debate_review

        result = debate_review(req.text, req.chapter, req.target_score)
        return {"success": True, "result": _to_dict(result)}
    except Exception as e:
        logger.error(f"[workstation] debate-review 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 读者模拟
# ---------------------------------------------------------------------------
@router.post("/reader-simulate", summary="读者模拟")
async def reader_simulate_endpoint(req: TextChapterRequest) -> dict:
    """模拟不同类型读者对文本的反应和评价。"""
    try:
        from kunlun.debate_review import simulate_readers

        result = simulate_readers(req.text, req.chapter)
        return {"success": True, "result": _to_dict(result)}
    except Exception as e:
        logger.error(f"[workstation] reader-simulate 失败: {e}")
        return {"success": False, "error": str(e)}


# ===========================================================================
# 通用 JSON 存储辅助（工作台数据持久化到 data/books/book_<id>/）
# ===========================================================================
import json as _json  # noqa: E402
import time as _time  # noqa: E402
import uuid as _uuid  # noqa: E402


def _book_dir(book_id: str) -> Path:
    path = Path("data/books") / f"book_{book_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_json(book_id: str, filename: str, default):
    path = _book_dir(book_id) / filename
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return default


def _save_json(book_id: str, filename: str, data) -> bool:
    path = _book_dir(book_id) / filename
    try:
        with path.open("w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"[workstation] save {filename} failed: {e}")
        return False


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{int(_time.time()*1000)}_{_uuid.uuid4().hex[:6]}"


# ===========================================================================
# 人物卡管理 (Characters)
# ===========================================================================
class CharacterCreateRequest(BaseModel):
    book_id: str = Field(default="default")
    name: str = Field(...)
    role: str = Field(default="")
    personality: str = Field(default="")
    appearance: str = Field(default="")
    background: str = Field(default="")
    relationships: list = Field(default_factory=list)
    growth_arc: str = Field(default="")
    abilities: str = Field(default="")
    motivation: str = Field(default="")
    notes: str = Field(default="")


class CharacterUpdateRequest(BaseModel):
    book_id: str = Field(default="default")
    name: str | None = None
    role: str | None = None
    personality: str | None = None
    appearance: str | None = None
    background: str | None = None
    relationships: list | None = None
    growth_arc: str | None = None
    abilities: str | None = None
    motivation: str | None = None
    notes: str | None = None


@router.get("/characters", summary="获取人物列表")
async def list_characters(book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "characters.json", {"characters": []})
        characters = data.get("characters", [])
        summary = [
            {
                "id": c.get("id"),
                "name": c.get("name", ""),
                "role": c.get("role", ""),
                "personality": c.get("personality", "")[:100],
                "created_at": c.get("created_at", ""),
                "updated_at": c.get("updated_at", ""),
            }
            for c in characters
        ]
        return {"success": True, "characters": summary, "total": len(summary)}
    except Exception as e:
        logger.error(f"[workstation] characters list failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/characters/{character_id}", summary="获取人物详情")
async def get_character(character_id: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "characters.json", {"characters": []})
        for c in data.get("characters", []):
            if c.get("id") == character_id:
                return {"success": True, "character": c}
        return {"success": False, "error": "character not found"}
    except Exception as e:
        logger.error(f"[workstation] character get failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/characters", summary="创建人物卡")
async def create_character(req: CharacterCreateRequest) -> dict:
    try:
        data = _load_json(req.book_id, "characters.json", {"characters": []})
        now = _time.strftime("%Y-%m-%d %H:%M:%S")
        char = {
            "id": _gen_id("char"),
            "name": req.name,
            "role": req.role,
            "personality": req.personality,
            "appearance": req.appearance,
            "background": req.background,
            "relationships": req.relationships,
            "growth_arc": req.growth_arc,
            "abilities": req.abilities,
            "motivation": req.motivation,
            "notes": req.notes,
            "created_at": now,
            "updated_at": now,
        }
        data.setdefault("characters", []).append(char)
        _save_json(req.book_id, "characters.json", data)
        return {"success": True, "character": char, "id": char["id"]}
    except Exception as e:
        logger.error(f"[workstation] character create failed: {e}")
        return {"success": False, "error": str(e)}


@router.put("/characters/{character_id}", summary="更新人物卡")
async def update_character(character_id: str, req: CharacterUpdateRequest) -> dict:
    try:
        data = _load_json(req.book_id, "characters.json", {"characters": []})
        found = False
        target = None
        for c in data.get("characters", []):
            if c.get("id") == character_id:
                found = True
                target = c
                update_data = req.model_dump(exclude_unset=True, exclude={"book_id"})
                c.update(update_data)
                c["updated_at"] = _time.strftime("%Y-%m-%d %H:%M:%S")
                break
        if not found:
            return {"success": False, "error": "character not found"}
        _save_json(req.book_id, "characters.json", data)
        return {"success": True, "character": target}
    except Exception as e:
        logger.error(f"[workstation] character update failed: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/characters/{character_id}", summary="删除人物卡")
async def delete_character(character_id: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "characters.json", {"characters": []})
        before = len(data.get("characters", []))
        data["characters"] = [c for c in data.get("characters", []) if c.get("id") != character_id]
        if before == len(data["characters"]):
            return {"success": False, "error": "character not found"}
        _save_json(book_id, "characters.json", data)
        return {"success": True, "deleted": True}
    except Exception as e:
        logger.error(f"[workstation] character delete failed: {e}")
        return {"success": False, "error": str(e)}


# ===========================================================================
# 大纲/故事结构 (Outline)
# ===========================================================================
class OutlineNodeRequest(BaseModel):
    book_id: str = Field(default="default")
    title: str = Field(...)
    node_type: str = Field(default="chapter")
    parent_id: str | None = None
    summary: str = Field(default="")
    plot_points: list = Field(default_factory=list)
    characters: list = Field(default_factory=list)
    word_target: int = Field(default=0)
    status: str = Field(default="draft")
    order: int = Field(default=0)


class OutlineUpdateRequest(BaseModel):
    book_id: str = Field(default="default")
    title: str | None = None
    node_type: str | None = None
    parent_id: str | None = None
    summary: str | None = None
    plot_points: list | None = None
    characters: list | None = None
    word_target: int | None = None
    status: str | None = None
    order: int | None = None


class ForeshadowRequest(BaseModel):
    book_id: str = Field(default="default")
    title: str = Field(...)
    description: str = Field(default="")
    planted_chapter: str = Field(default="")
    resolved_chapter: str = Field(default="")
    status: str = Field(default="active")
    importance: str = Field(default="medium")


@router.get("/outline", summary="获取大纲树")
async def get_outline(book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "outline.json", {"nodes": [], "foreshadows": []})
        return {
            "success": True,
            "nodes": data.get("nodes", []),
            "foreshadows": data.get("foreshadows", []),
        }
    except Exception as e:
        logger.error(f"[workstation] outline get failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/outline/nodes", summary="创建大纲节点")
async def create_outline_node(req: OutlineNodeRequest) -> dict:
    try:
        data = _load_json(req.book_id, "outline.json", {"nodes": [], "foreshadows": []})
        now = _time.strftime("%Y-%m-%d %H:%M:%S")
        node = {
            "id": _gen_id("node"),
            "title": req.title,
            "node_type": req.node_type,
            "parent_id": req.parent_id,
            "summary": req.summary,
            "plot_points": req.plot_points,
            "characters": req.characters,
            "word_target": req.word_target,
            "status": req.status,
            "order": req.order,
            "created_at": now,
            "updated_at": now,
        }
        data.setdefault("nodes", []).append(node)
        _save_json(req.book_id, "outline.json", data)
        return {"success": True, "node": node, "id": node["id"]}
    except Exception as e:
        logger.error(f"[workstation] outline node create failed: {e}")
        return {"success": False, "error": str(e)}


@router.put("/outline/nodes/{node_id}", summary="更新大纲节点")
async def update_outline_node(node_id: str, req: OutlineUpdateRequest) -> dict:
    try:
        data = _load_json(req.book_id, "outline.json", {"nodes": [], "foreshadows": []})
        found = False
        target = None
        for n in data.get("nodes", []):
            if n.get("id") == node_id:
                found = True
                target = n
                update_data = req.model_dump(exclude_unset=True, exclude={"book_id"})
                n.update(update_data)
                n["updated_at"] = _time.strftime("%Y-%m-%d %H:%M:%S")
                break
        if not found:
            return {"success": False, "error": "node not found"}
        _save_json(req.book_id, "outline.json", data)
        return {"success": True, "node": target}
    except Exception as e:
        logger.error(f"[workstation] outline node update failed: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/outline/nodes/{node_id}", summary="删除大纲节点")
async def delete_outline_node(node_id: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "outline.json", {"nodes": [], "foreshadows": []})
        to_delete = {node_id}
        changed = True
        while changed:
            changed = False
            for n in data.get("nodes", []):
                if n.get("parent_id") in to_delete and n.get("id") not in to_delete:
                    to_delete.add(n["id"])
                    changed = True
        before = len(data.get("nodes", []))
        data["nodes"] = [n for n in data.get("nodes", []) if n.get("id") not in to_delete]
        if before == len(data["nodes"]):
            return {"success": False, "error": "node not found"}
        _save_json(book_id, "outline.json", data)
        return {"success": True, "deleted": len(to_delete)}
    except Exception as e:
        logger.error(f"[workstation] outline node delete failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/outline/foreshadows", summary="获取伏笔列表")
async def list_foreshadows(book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "outline.json", {"nodes": [], "foreshadows": []})
        return {"success": True, "foreshadows": data.get("foreshadows", [])}
    except Exception as e:
        logger.error(f"[workstation] foreshadows list failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/outline/foreshadows", summary="创建伏笔")
async def create_foreshadow(req: ForeshadowRequest) -> dict:
    try:
        data = _load_json(req.book_id, "outline.json", {"nodes": [], "foreshadows": []})
        fs = {
            "id": _gen_id("fs"),
            "title": req.title,
            "description": req.description,
            "planted_chapter": req.planted_chapter,
            "resolved_chapter": req.resolved_chapter,
            "status": req.status,
            "importance": req.importance,
            "created_at": _time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data.setdefault("foreshadows", []).append(fs)
        _save_json(req.book_id, "outline.json", data)
        return {"success": True, "foreshadow": fs, "id": fs["id"]}
    except Exception as e:
        logger.error(f"[workstation] foreshadow create failed: {e}")
        return {"success": False, "error": str(e)}


@router.put("/outline/foreshadows/{fs_id}", summary="更新伏笔")
async def update_foreshadow(fs_id: str, req: ForeshadowRequest) -> dict:
    try:
        data = _load_json(req.book_id, "outline.json", {"nodes": [], "foreshadows": []})
        found = False
        target = None
        for f in data.get("foreshadows", []):
            if f.get("id") == fs_id:
                found = True
                target = f
                f.update(req.model_dump(exclude={"book_id"}))
                break
        if not found:
            return {"success": False, "error": "foreshadow not found"}
        _save_json(req.book_id, "outline.json", data)
        return {"success": True, "foreshadow": target}
    except Exception as e:
        logger.error(f"[workstation] foreshadow update failed: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/outline/foreshadows/{fs_id}", summary="删除伏笔")
async def delete_foreshadow(fs_id: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "outline.json", {"nodes": [], "foreshadows": []})
        before = len(data.get("foreshadows", []))
        data["foreshadows"] = [f for f in data.get("foreshadows", []) if f.get("id") != fs_id]
        if before == len(data["foreshadows"]):
            return {"success": False, "error": "foreshadow not found"}
        _save_json(book_id, "outline.json", data)
        return {"success": True, "deleted": True}
    except Exception as e:
        logger.error(f"[workstation] foreshadow delete failed: {e}")
        return {"success": False, "error": str(e)}


# ===========================================================================
# 版本/检查点 (Versions)
# ===========================================================================
class CheckpointCreateRequest(BaseModel):
    book_id: str = Field(default="default")
    chapter_id: str = Field(default="")
    chapter_name: str = Field(default="")
    content: str = Field(default="")
    label: str = Field(default="")
    word_count: int = Field(default=0)


class VersionRestoreRequest(BaseModel):
    book_id: str = Field(default="default")
    version_id: str = Field(...)


@router.get("/versions", summary="获取版本历史")
async def list_versions(book_id: str = "default", chapter_id: str = "") -> dict:
    try:
        data = _load_json(book_id, "versions.json", {"versions": []})
        versions = data.get("versions", [])
        if chapter_id:
            versions = [v for v in versions if v.get("chapter_id") == chapter_id]
        versions.sort(key=lambda v: v.get("created_at", ""), reverse=True)
        summary = [
            {
                "id": v.get("id"),
                "chapter_id": v.get("chapter_id", ""),
                "chapter_name": v.get("chapter_name", ""),
                "label": v.get("label", ""),
                "word_count": v.get("word_count", 0),
                "created_at": v.get("created_at", ""),
                "is_checkpoint": v.get("is_checkpoint", False),
            }
            for v in versions
        ]
        return {"success": True, "versions": summary, "total": len(summary)}
    except Exception as e:
        logger.error(f"[workstation] versions list failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/versions/{version_id}", summary="获取版本详情")
async def get_version(version_id: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "versions.json", {"versions": []})
        for v in data.get("versions", []):
            if v.get("id") == version_id:
                return {"success": True, "version": v}
        return {"success": False, "error": "version not found"}
    except Exception as e:
        logger.error(f"[workstation] version get failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/versions/checkpoint", summary="创建检查点")
async def create_checkpoint(req: CheckpointCreateRequest) -> dict:
    try:
        data = _load_json(req.book_id, "versions.json", {"versions": []})
        now = _time.strftime("%Y-%m-%d %H:%M:%S")
        version = {
            "id": _gen_id("ver"),
            "chapter_id": req.chapter_id,
            "chapter_name": req.chapter_name,
            "content": req.content,
            "label": req.label or f"checkpoint {now}",
            "word_count": req.word_count or len(req.content),
            "is_checkpoint": True,
            "created_at": now,
        }
        data.setdefault("versions", []).append(version)
        _save_json(req.book_id, "versions.json", data)
        return {"success": True, "version": version, "id": version["id"]}
    except Exception as e:
        logger.error(f"[workstation] checkpoint create failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/versions/restore", summary="恢复版本")
async def restore_version(req: VersionRestoreRequest) -> dict:
    try:
        data = _load_json(req.book_id, "versions.json", {"versions": []})
        for v in data.get("versions", []):
            if v.get("id") == req.version_id:
                return {
                    "success": True,
                    "restored": True,
                    "content": v.get("content", ""),
                    "chapter_id": v.get("chapter_id", ""),
                    "chapter_name": v.get("chapter_name", ""),
                    "version": v,
                }
        return {"success": False, "error": "version not found"}
    except Exception as e:
        logger.error(f"[workstation] version restore failed: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/versions/{version_id}", summary="删除版本")
async def delete_version(version_id: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "versions.json", {"versions": []})
        before = len(data.get("versions", []))
        data["versions"] = [v for v in data.get("versions", []) if v.get("id") != version_id]
        if before == len(data["versions"]):
            return {"success": False, "error": "version not found"}
        _save_json(book_id, "versions.json", data)
        return {"success": True, "deleted": True}
    except Exception as e:
        logger.error(f"[workstation] version delete failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/versions/diff", summary="版本差异对比")
async def version_diff(version_a: str, version_b: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "versions.json", {"versions": []})
        content_a = ""
        content_b = ""
        for v in data.get("versions", []):
            if v.get("id") == version_a:
                content_a = v.get("content", "")
            if v.get("id") == version_b:
                content_b = v.get("content", "")
        lines_a = content_a.split("\n")
        lines_b = content_b.split("\n")
        diff_result = []
        max_len = max(len(lines_a), len(lines_b))
        for i in range(max_len):
            la = lines_a[i] if i < len(lines_a) else None
            lb = lines_b[i] if i < len(lines_b) else None
            if la == lb:
                diff_result.append({"type": "same", "line": i + 1, "text": la or ""})
            elif la is not None and lb is not None:
                diff_result.append({"type": "modified", "line": i + 1, "old": la, "new": lb})
            elif la is not None:
                diff_result.append({"type": "removed", "line": i + 1, "text": la})
            else:
                diff_result.append({"type": "added", "line": i + 1, "text": lb})
        return {
            "success": True,
            "diff": diff_result,
            "stats": {
                "added": sum(1 for d in diff_result if d["type"] == "added"),
                "removed": sum(1 for d in diff_result if d["type"] == "removed"),
                "modified": sum(1 for d in diff_result if d["type"] == "modified"),
                "same": sum(1 for d in diff_result if d["type"] == "same"),
            },
        }
    except Exception as e:
        logger.error(f"[workstation] version diff failed: {e}")
        return {"success": False, "error": str(e)}


# ===========================================================================
# 故事圣经 (Story Bible)
# ===========================================================================
class BibleSectionRequest(BaseModel):
    book_id: str = Field(default="default")
    section: str = Field(...)
    title: str = Field(default="")
    content: str = Field(default="")
    tags: list = Field(default_factory=list)


class BibleUpdateRequest(BaseModel):
    book_id: str = Field(default="default")
    section: str | None = None
    title: str | None = None
    content: str | None = None
    tags: list | None = None


@router.get("/bible", summary="获取故事圣经")
async def get_bible(book_id: str = "default", section: str = "") -> dict:
    try:
        data = _load_json(book_id, "bible.json", {"sections": {}})
        sections = data.get("sections", {})
        if section:
            return {"success": True, "section": section, "items": sections.get(section, [])}
        return {"success": True, "sections": sections}
    except Exception as e:
        logger.error(f"[workstation] bible get failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/bible/items", summary="创建圣经条目")
async def create_bible_item(req: BibleSectionRequest) -> dict:
    try:
        data = _load_json(req.book_id, "bible.json", {"sections": {}})
        now = _time.strftime("%Y-%m-%d %H:%M:%S")
        item = {
            "id": _gen_id("bible"),
            "section": req.section,
            "title": req.title,
            "content": req.content,
            "tags": req.tags,
            "created_at": now,
            "updated_at": now,
        }
        data.setdefault("sections", {}).setdefault(req.section, []).append(item)
        _save_json(req.book_id, "bible.json", data)
        return {"success": True, "item": item, "id": item["id"]}
    except Exception as e:
        logger.error(f"[workstation] bible item create failed: {e}")
        return {"success": False, "error": str(e)}


@router.put("/bible/items/{item_id}", summary="更新圣经条目")
async def update_bible_item(item_id: str, req: BibleUpdateRequest) -> dict:
    try:
        data = _load_json(req.book_id, "bible.json", {"sections": {}})
        found = False
        target = None
        for sec_name, items in data.get("sections", {}).items():
            for item in items:
                if item.get("id") == item_id:
                    found = True
                    target = item
                    update_data = req.model_dump(exclude_unset=True, exclude={"book_id"})
                    item.update(update_data)
                    item["updated_at"] = _time.strftime("%Y-%m-%d %H:%M:%S")
                    if "section" in update_data and update_data["section"] != sec_name:
                        items.remove(item)
                        data.setdefault("sections", {}).setdefault(
                            update_data["section"], []
                        ).append(item)
                    break
            if found:
                break
        if not found:
            return {"success": False, "error": "item not found"}
        _save_json(req.book_id, "bible.json", data)
        return {"success": True, "item": target}
    except Exception as e:
        logger.error(f"[workstation] bible item update failed: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/bible/items/{item_id}", summary="删除圣经条目")
async def delete_bible_item(item_id: str, book_id: str = "default") -> dict:
    try:
        data = _load_json(book_id, "bible.json", {"sections": {}})
        found = False
        for items in data.get("sections", {}).values():
            before = len(items)
            items[:] = [item for item in items if item.get("id") != item_id]
            if len(items) < before:
                found = True
        if not found:
            return {"success": False, "error": "item not found"}
        _save_json(book_id, "bible.json", data)
        return {"success": True, "deleted": True}
    except Exception as e:
        logger.error(f"[workstation] bible item delete failed: {e}")
        return {"success": False, "error": str(e)}
