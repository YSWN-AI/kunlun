"""
昆仑创作引擎 — 桌面工作台 API 路由
统一前缀 /api/v1/workstation，为桌面端创作工作台提供六维质量、AI率、风格学习、记忆系统、辩论审校、读者模拟等能力。
"""

import dataclasses
from enum import Enum
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
    layer: str = Field(default="working", description="记忆层级: working/episodic/semantic/procedural")


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
        from kunlun.memory.engine import create_memory_manager, MemoryImportance
        import time
        import uuid

        mm = create_memory_manager(req.book_id)
        memory_id = f"mem_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        layer = req.layer.lower()
        if layer == "working":
            mm.working.add_note(req.content, importance=MemoryImportance.MEDIUM)
        elif layer == "episodic":
            mm.episodic.add_event(
                event_type="manual_note",
                description=req.content,
                chapter=0,
            )
        elif layer == "semantic":
            # 语义层通过实体提取添加
            from kunlun.memory.engine import extract_entities_from_text

            entities = extract_entities_from_text(req.content)
            for ent in entities:
                mm.semantic.add_entity(ent) if hasattr(mm.semantic, "add_entity") else None
        elif layer == "procedural":
            if hasattr(mm.procedural, "add_pattern"):
                mm.procedural.add_pattern(req.content)
        else:
            # 默认写入工作记忆
            mm.working.add_note(req.content, importance=MemoryImportance.MEDIUM)

        # 尝试持久化
        try:
            mm.save()
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
