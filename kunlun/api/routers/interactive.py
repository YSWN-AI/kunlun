"""
昆仑创作引擎 — 交互式小说路由 (v2)

端点:
  POST   /interactive/state             — 获取/初始化游戏状态
  POST   /interactive/choices           — 获取当前节点可选选择
  POST   /interactive/choose            — 做出选择
  POST   /interactive/add-choice        — 添加选择项到节点
  POST   /interactive/add-ending        — 添加结局
  POST   /interactive/check-endings     — 检查当前状态触发的结局
  GET    /interactive/endings           — 获取所有结局
  POST   /interactive/reset             — 重置状态/新周目
  POST   /interactive/sync-kg           — 同步到知识图谱
  GET    /interactive/export            — 导出选择树
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/interactive", tags=["交互式小说"])


class StateRequest(BaseModel):
    book_id: str = Field(...)


class ChoicesRequest(BaseModel):
    book_id: str = Field(...)
    node_id: str = Field(..., description="节点ID")


class MakeChoiceRequest(BaseModel):
    book_id: str = Field(...)
    node_id: str = Field(..., description="当前节点ID")
    choice_id: str = Field(..., description="选择ID")
    next_node_id: str = Field(default="", description="跳转节点ID")


class AddChoiceRequest(BaseModel):
    book_id: str = Field(...)
    node_id: str = Field(..., description="节点ID")
    text: str = Field(..., min_length=1, description="选择文本")
    choice_type: str = Field(default="action", description="选择类型")
    hint: str = Field(default="")
    outcomes: list[dict] = Field(default_factory=list, description="结果列表")


class AddEndingRequest(BaseModel):
    book_id: str = Field(...)
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    conditions: dict[str, str] = Field(default_factory=dict)
    ending_type: str = Field(default="normal")
    epilogue: str = Field(default="")


class CheckEndingsRequest(BaseModel):
    book_id: str = Field(...)


@router.post("/state")
async def get_state(req: StateRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    engine.get_or_create_state()
    return {"success": True, "data": engine.get_state_summary()}


@router.post("/choices")
async def get_choices(req: ChoicesRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    choices = engine.get_choices(req.node_id)

    return {
        "success": True,
        "data": [
            {
                "id": c.id,
                "text": c.text,
                "type": c.choice_type.value,
                "hint": c.hint,
                "popularity": c.popularity,
                "outcome_count": len(c.outcomes),
            }
            for c in choices
        ],
    }


@router.post("/choose")
async def make_choice(req: MakeChoiceRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    try:
        outcomes = engine.make_choice(req.choice_id, req.node_id, req.next_node_id)
        return {
            "success": True,
            "data": {
                "outcomes": [
                    {
                        "description": o.description,
                        "attribute_changes": o.attribute_changes,
                        "relationship_changes": o.relationship_changes,
                        "items_gained": o.items_gained,
                        "items_lost": o.items_lost,
                        "flags_set": o.flags_set,
                        "is_ending": o.is_ending,
                        "ending_id": o.ending_id,
                        "next_chapter_id": o.next_chapter_id,
                    }
                    for o in outcomes
                ],
                "state_summary": engine.get_state_summary(),
            },
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}


@router.post("/add-choice")
async def add_choice(req: AddChoiceRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import ChoiceType, get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    try:
        ctype = ChoiceType(req.choice_type)
    except ValueError:
        ctype = ChoiceType.ACTION

    from kunlun.interactive.engine import ChoiceOutcome

    outcomes = [
        ChoiceOutcome(
            description=o.get("description", ""),
            attribute_changes=o.get("attribute_changes", {}),
            relationship_changes=o.get("relationship_changes", {}),
            items_gained=o.get("items_gained", []),
            items_lost=o.get("items_lost", []),
            flags_set=o.get("flags_set", {}),
            flags_cleared=o.get("flags_cleared", []),
            next_chapter_id=o.get("next_chapter_id", ""),
            is_ending=o.get("is_ending", False),
            ending_id=o.get("ending_id", ""),
        )
        for o in req.outcomes
    ]

    choice = engine.add_choice(
        node_id=req.node_id,
        text=req.text,
        choice_type=ctype,
        outcomes=outcomes,
        hint=req.hint,
    )

    return {"success": True, "data": {"choice_id": choice.id}}


@router.post("/add-ending")
async def add_ending(req: AddEndingRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    ending = engine.add_ending(
        name=req.name,
        description=req.description,
        conditions=req.conditions,
        ending_type=req.ending_type,
        epilogue=req.epilogue,
    )

    return {
        "success": True,
        "data": {
            "id": ending.id,
            "name": ending.name,
            "ending_type": ending.ending_type,
        },
    }


@router.post("/check-endings")
async def check_endings(req: CheckEndingsRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    triggered = engine.check_endings()

    return {
        "success": True,
        "data": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "ending_type": e.ending_type,
            }
            for e in triggered
        ],
    }


@router.get("/endings")
async def get_endings(book_id: str):
    validate_book_id(book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(book_id)
    all_endings = engine.get_all_endings()
    unlocked_ids = set(engine.get_or_create_state().unlocked_endings)

    return {
        "success": True,
        "data": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "ending_type": e.ending_type,
                "is_unlocked": e.id in unlocked_ids,
                "unlock_count": e.unlock_count,
            }
            for e in all_endings
        ],
    }


@router.post("/reset")
async def reset_state(req: StateRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    state = engine.reset_state()
    return {"success": True, "data": {"playthrough": state.playthrough_count}}


@router.post("/sync-kg")
async def sync_to_kg(req: StateRequest):
    validate_book_id(req.book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(req.book_id)
    sync_data = engine.sync_to_kg()
    return {"success": True, "data": sync_data}


@router.get("/export")
async def export_choice_tree(book_id: str):
    validate_book_id(book_id)
    from kunlun.interactive import get_interactive_engine

    engine = get_interactive_engine(book_id)
    return {"success": True, "data": engine.export_choice_tree()}
