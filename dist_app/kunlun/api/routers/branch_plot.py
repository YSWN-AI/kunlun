"""
昆仑创作引擎 — 分支剧情路由 (v2)

端点:
  GET    /branch-plot/tree               — 获取分支树
  POST   /branch-plot/detect             — 检测分支点
  POST   /branch-plot/add-branch         — 添加分支节点
  POST   /branch-plot/recommend          — 获取分支推荐
  GET    /branch-plot/statistics         — 分支树统计
  GET    /branch-plot/export             — 导出分支树/前端可视化
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/branch-plot", tags=["分支剧情"])


class DetectBranchRequest(BaseModel):
    book_id: str = Field(...)
    text: str = Field(..., description="章节文本")
    chapter: int = Field(..., ge=0, description="章节号")
    use_conflict_engine: bool = Field(default=True, description="是否集成冲突引擎")


class AddBranchRequest(BaseModel):
    book_id: str = Field(...)
    parent_id: str = Field(..., description="父节点ID")
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    chapter: int = Field(..., ge=0)
    branch_type: str = Field(default="character_decision")
    conflict_ids: list[str] = Field(default_factory=list)
    character_ids: list[str] = Field(default_factory=list)
    is_canon: bool = Field(default=False)


class RecommendRequest(BaseModel):
    book_id: str = Field(...)
    node_id: str = Field(default="", description="节点ID，为空则使用当前节点")
    top_k: int = Field(default=3, ge=1, le=10)


@router.get("/tree")
async def get_branch_tree(book_id: str):
    validate_book_id(book_id)
    from kunlun.branch_plot import get_branch_engine

    engine = get_branch_engine(book_id)
    engine.get_or_create_tree()
    return {
        "success": True,
        "data": engine.export_for_browser(),
    }


@router.post("/detect")
async def detect_branch_points(req: DetectBranchRequest):
    validate_book_id(req.book_id)
    from kunlun.branch_plot import get_branch_engine
    from kunlun.conflict import get_conflict_manager

    engine = get_branch_engine(req.book_id)
    cm = get_conflict_manager(req.book_id) if req.use_conflict_engine else None
    points = engine.detect_branch_points(req.text, req.chapter, conflict_manager=cm)

    for bp in points:
        bp["suggestions"] = engine.suggest_branch_options(bp, req.text)
        if "branch_type" in bp and not isinstance(bp.get("branch_type"), str):
            bp["type"] = bp["branch_type"].value

    return {"success": True, "data": points}


@router.post("/add-branch")
async def add_branch(req: AddBranchRequest):
    validate_book_id(req.book_id)
    from kunlun.branch_plot import BranchPointType, get_branch_engine

    engine = get_branch_engine(req.book_id)
    try:
        btype = BranchPointType(req.branch_type)
    except ValueError:
        btype = BranchPointType.CHARACTER_DECISION

    node = engine.add_branch(
        parent_id=req.parent_id,
        name=req.name,
        description=req.description,
        chapter=req.chapter,
        branch_type=btype,
        conflict_ids=req.conflict_ids,
        character_ids=req.character_ids,
        is_canon=req.is_canon,
    )

    return {
        "success": True,
        "data": {
            "id": node.id,
            "name": node.name,
            "chapter": node.chapter,
            "branch_type": node.branch_type.value,
            "is_canon": node.is_canon,
        },
    }


@router.post("/recommend")
async def recommend_branches(req: RecommendRequest):
    validate_book_id(req.book_id)
    from kunlun.branch_plot import get_branch_engine

    engine = get_branch_engine(req.book_id)
    node_id = req.node_id
    if not node_id:
        tree = engine.get_or_create_tree()
        node_id = tree.current_path[-1] if tree.current_path else tree.root_id

    recommendations = engine.recommend_branches(node_id, top_k=req.top_k)

    return {
        "success": True,
        "data": [
            {
                "node_id": r.node.id,
                "name": r.node.name,
                "description": r.node.description,
                "score": round(r.score, 3),
                "reason": r.reason,
                "chapter_range": list(r.suggested_chapter_range),
                "quality_score": r.node.quality_score,
                "popularity_score": r.node.popularity_score,
            }
            for r in recommendations
        ],
    }


@router.get("/statistics")
async def branch_statistics(book_id: str):
    validate_book_id(book_id)
    from kunlun.branch_plot import get_branch_engine

    engine = get_branch_engine(book_id)
    return {"success": True, "data": engine.get_statistics()}


@router.get("/export")
async def export_branch_tree(book_id: str):
    validate_book_id(book_id)
    from kunlun.branch_plot import get_branch_engine

    engine = get_branch_engine(book_id)
    return {"success": True, "data": engine.export_for_browser()}
