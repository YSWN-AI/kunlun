"""
昆仑创作引擎 — 主编 Agent（总调度）

对应 inkos 的 Planner + Composer 角色。创作者通过对话与主编交互，
主编理解意图后分配任务给 7 个专业 Agent 协同完成。

Agent 团队:
  📋 Planner     — 读取作者意图 + 焦点 → 产出章节意图
  🏗️ Architect   — 蓝图生成 + 大纲体系（总纲→卷纲→章纲）
  ✍️ Writer      — 正文生成（多模型抽卡 + 去AI味）
  🔍 Auditor     — 33维度连续性审计
  🔧 Reviser     — 自动修复审计问题
  🎨 Stylist     — 文风仿写 + 指纹注入
  📚 Librarian   — 知识管理（KG + 真相文件）

三级大纲体系:
  总纲 (Master Outline) → 卷纲 (Volume Outline) → 章节蓝图 (Chapter Blueprint)

控制文档:
  story/author_intent.md   — 长期创作意图
  story/current_focus.md   — 近期关注点
  story/book_rules.md      — 作品规则
  story/story_bible.md     — 世界观设定
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from loguru import logger

from kunlun.agents.architect import Architect
from kunlun.agents.auditor import Auditor
from kunlun.agents.makefile import Makefile
from kunlun.agents.writer import Writer
from kunlun.audit.audit33 import auditor33
from kunlun.config import settings
from kunlun.filesync import get_syncer
from kunlun.gacha.engine import gacha_engine
from kunlun.kg.snapshot import snapshot_manager
from kunlun.learn.evolve import get_evolution_tracker
from kunlun.style.engineer import StyleEngineer
from kunlun.style.fingerprint import style_analyzer, style_injector
from kunlun.truth import get_truth_manager


@dataclass
class CreativeBrief:
    """创作简报 — 作者意图的结构化表达"""

    book_id: str
    author_intent: str = ""  # 长期创作意图
    current_focus: str = ""  # 近期1-3章关注点
    must_keep: list[str] = field(default_factory=list)  # 必须保留的元素
    must_avoid: list[str] = field(default_factory=list)  # 必须避免的元素
    style_reference: str = ""  # 参考文风
    target_audience: str = ""  # 目标读者
    genre_rules: dict = field(default_factory=dict)  # 题材专属规则


@dataclass
class ChapterIntent:
    """章节意图 — Planner 产出"""

    chapter: int
    must_keep: list[str]  # 本章必须包含
    must_avoid: list[str]  # 本章必须避免
    suggested_scenes: list[dict]  # 建议场景
    emotion_target: str = ""  # 目标情绪
    hook_requirement: str = ""  # 钩子要求
    word_target: int = 3000  # 字数目标
    conflicts_to_advance: list[str] = field(default_factory=list)  # 需推进的冲突


@dataclass
class OutlineNode:
    """大纲节点"""

    id: str
    title: str
    level: str  # master/volume/chapter
    summary: str
    children: list[OutlineNode] = field(default_factory=list)
    arc_stage: str = ""  # 弧线阶段
    foreshadowing: list[str] = field(default_factory=list)
    pleasure_points: int = 0


class EditorInChief:
    """
    主编 Agent — 对话式总调度

    用法:
      editor = EditorInChief(book_id)
      response = await editor.chat("我想写一章主角突破金丹期的剧情")
      # 主编分析意图 → Planner产出章节意图 → Architect生成蓝图 → Writer生成正文
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self._ensure_control_docs()
        self.syncer = get_syncer(book_id)
        self.brief = self._load_brief()

    # ─── 控制文档管理 ───

    def _ensure_control_docs(self):
        """确保控制文档目录和文件存在"""
        story_dir = settings.DATA_DIR / "story" / self.book_id
        story_dir.mkdir(parents=True, exist_ok=True)
        runtime_dir = story_dir / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        docs = {
            "author_intent.md": (
                "# 作者意图\n\n## 这本书想成为什么\n\n"
                "（在此描述你的长期创作目标）\n\n## 核心主题\n\n"
                "## 目标读者\n\n## 创作理念\n"
            ),
            "current_focus.md": (
                "# 当前焦点\n\n## 最近1-3章关注点\n\n## 待推进的冲突\n\n## 需回收的伏笔\n"
            ),
            "book_rules.md": "# 作品规则\n\n## 硬约束\n- \n\n## 软指南\n- \n\n## 角色规则\n- \n",
            "story_bible.md": (
                "# 故事设定\n\n## 世界观\n\n## 力量体系\n\n## 主要势力\n\n## 关键地点\n"
            ),
        }
        for name, content in docs.items():
            path = story_dir / name
            if not path.exists():
                path.write_text(content, encoding="utf-8")

    def _load_brief(self) -> CreativeBrief:
        """加载创作简报"""
        brief = CreativeBrief(book_id=self.book_id)
        story_dir = settings.DATA_DIR / "story" / self.book_id
        try:
            intent_path = story_dir / "author_intent.md"
            if intent_path.exists():
                brief.author_intent = intent_path.read_text(encoding="utf-8")
            focus_path = story_dir / "current_focus.md"
            if focus_path.exists():
                brief.current_focus = focus_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.exception(f"[Editor] 加载简报失败: {e}")
            logger.warning(f"[Editor] 加载简报失败: {e}")
        return brief

    def update_focus(self, new_focus: str):
        """更新当前焦点"""
        story_dir = settings.DATA_DIR / "story" / self.book_id
        (story_dir / "current_focus.md").write_text(new_focus, encoding="utf-8")
        self.brief.current_focus = new_focus

    def update_intent(self, new_intent: str):
        """更新长期意图"""
        story_dir = settings.DATA_DIR / "story" / self.book_id
        (story_dir / "author_intent.md").write_text(new_intent, encoding="utf-8")
        self.brief.author_intent = new_intent

    # ─── 对话接口 ───

    async def chat(self, user_message: str, context: dict | None = None) -> dict:
        """
        主编对话接口 — 理解作者意图，分配任务给专业Agent

        支持的命令:
          - 写/生成/创作 第X章 → 触发完整创作流水线
          - 规划/大纲 → 触发三级大纲生成
          - 设定/世界观 → 更新世界观设定
          - 分析/审计 → 运行33维审计
          - 风格/文风 → 文风仿写/注入
          - 角色/人物 → 角色管理
          - 续写/接续 → 基于上下文继续创作
        """
        # 意图识别
        intent = await self._classify_intent(user_message)

        if intent == "write_chapter":
            return await self._handle_write_chapter(user_message, context)
        if intent == "plan_outline":
            return await self._handle_plan_outline(user_message, context)
        if intent == "world_setting":
            return await self._handle_world_setting(user_message, context)
        if intent == "character":
            return await self._handle_character(user_message, context)
        if intent == "audit":
            return await self._handle_audit(user_message, context)
        if intent == "style":
            return await self._handle_style(user_message, context)
        if intent == "continue":
            return await self._handle_continue(user_message, context)
        return await self._handle_general(user_message, context)

    async def _classify_intent(self, message: str) -> str:
        """通过 LLM 分类用户意图（真实调用）"""
        prompt = f"""分类以下用户消息的意图。只输出一个标签。

用户: {message[:500]}

标签选项:
- write_chapter: 写/生成/创作章节
- plan_outline: 规划/大纲/分卷/章纲
- world_setting: 世界观/设定/力量体系/势力
- character: 角色/人物/关系
- audit: 审计/检查/质量
- style: 文风/风格/模仿
- continue: 续写/接着写/继续
- general: 其他"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "").strip().lower()
            for tag in [
                "write_chapter",
                "plan_outline",
                "world_setting",
                "character",
                "audit",
                "style",
                "continue",
            ]:
                if tag in text:
                    return tag
        except Exception as e:
            logger.exception(f"[Editor] 意图分类跳过: {e}")
            logger.debug(f"[Editor] 意图分类跳过: {e}")
        return "general"

    # ─── 命令处理器 ───

    async def _handle_write_chapter(self, message: str, _ctx: dict | None = None) -> dict:
        """处理写章命令 — 完整流水线（含文件自动联动）"""
        chapter = self._extract_chapter_number(message) or 1
        word_target = self._extract_word_target(message) or 3000
        focus = self._extract_focus(message)

        # ── 每章前：自动重读所有控制文档 + 组装全量上下文 ──
        pipeline_ctx = self.syncer.assemble_pipeline_context(chapter)
        self.brief = self._load_brief()  # 刷新简报（作者可能在Web UI改了）
        logger.info(
            f"[Editor] 第{chapter}章上下文已组装 "
            f"(风格:{pipeline_ctx.style_loaded}, 学习规则:{bool(pipeline_ctx.learned_rules)}, "
            f"警告:{len(pipeline_ctx.consistency_warnings)})"
        )

        # Step 1: Planner 产出章节意图（注入最新控制文档）
        chapter_intent = await self._plan_chapter_intent(chapter, focus, word_target)
        logger.info(f"[Editor] 第{chapter}章意图: {chapter_intent.must_keep[:3]}...")

        # Step 2: Architect 生成蓝图（注入RAG+真相摘要+风格）
        blueprint = await self._generate_blueprint(chapter, chapter_intent)
        logger.info(f"[Editor] 第{chapter}章蓝图: {len(blueprint.get('scenes', []))}场景")

        # Step 3: Writer 生成正文（注入风格指纹+学习补丁）
        draft_result = await self._write_chapter(chapter, blueprint, chapter_intent)
        draft = draft_result.get("draft", "")

        # Step 4: Auditor 33维审计（对照真相文件）
        audit_result = await self._audit_chapter(chapter, draft, blueprint)
        passed = audit_result.get("passed", False)

        # Step 5: 如果审计不通过，Reviser 自动修复（最多3轮）
        revisions = 0
        while not passed and revisions < 3:
            draft_result = await self._revise_chapter(chapter, draft, audit_result, blueprint)
            draft = draft_result.get("draft", draft)
            audit_result = await self._audit_chapter(chapter, draft, blueprint)
            passed = audit_result.get("passed", False)
            revisions += 1

        # Step 6: Stylist 去AI味 + 风格注入
        polished = await self._polish_chapter(draft)

        # Step 7: Librarian 更新KG + 真相文件 + 进化追踪
        await self._update_knowledge(chapter, polished, blueprint)

        # Step 8: 每章后自动同步所有联动文件
        self.syncer.sync_after_chapter(chapter, polished, blueprint, audit_result, chapter_intent)

        return {
            "success": True,
            "chapter": chapter,
            "draft": polished,
            "word_count": len(polished),
            "audit_passed": passed,
            "revisions": revisions,
            "blueprint": blueprint,
            "chapter_intent": chapter_intent.__dict__
            if hasattr(chapter_intent, "__dict__")
            else {},
            "consistency_warnings": pipeline_ctx.consistency_warnings,
        }

    async def _handle_plan_outline(self, message: str, _ctx: dict | None = None) -> dict:
        """三级大纲生成: 总纲→卷纲→章纲"""

        brief = self.brief
        prompt = f"""你是资深网文大纲规划师。请为以下作品生成三级大纲体系。

作者意图: {brief.author_intent[:500]}
当前焦点: {brief.current_focus[:500]}
用户需求: {message[:500]}

输出JSON格式（不要markdown代码块）:
{{
  "master_outline": {{"title": "总纲标题", "summary": "全书概要(100-200字)",
    "total_chapters_estimate": 100, "main_arcs": ["主线1","主线2"], "themes": ["主题"]}},
  "volumes": [{{"number":1,"title":"卷名","arc_stage":"开幕/展开/转折/高潮/收尾",
    "chapter_range":"1-30","summary":"本卷概要"}}],
  "chapter_outlines": [{{"number":1,"title":"章名","type":"normal",
    "summary":"本章概要","scenes":["场景"],"foreshadowing":["伏笔"],"word_target":3000}}]
}}

生成3-5卷和前10章大纲。"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start, json_end = text.find("{"), text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                outline = json.loads(text[json_start : json_end + 1])
                self._save_outline(outline)
                return {"success": True, "outline": outline}
        except Exception as e:
            logger.exception(f"[Editor] 大纲生成失败: {e}")
            logger.error(f"[Editor] 大纲生成失败: {e}")

        return {"success": False, "error": "大纲生成失败"}

    async def _handle_world_setting(self, message: str, _ctx: dict | None = None) -> dict:
        """世界观设定 — 调用 Architect 生成/更新"""

        story_dir = settings.DATA_DIR / "story" / self.book_id
        current_bible = ""
        bible_path = story_dir / "story_bible.md"
        if bible_path.exists():
            current_bible = bible_path.read_text(encoding="utf-8")[:2000]

        prompt = f"""你是世界观架构师。请根据用户需求更新/生成世界观设定。

当前设定: {current_bible}
用户需求: {message[:500]}

输出JSON:
{{"power_system":{{"name":"体系名","levels":["级1","级2"],"rules":"规则"}},"locations":[{{"name":"地名","type":"类型","desc":"描述"}}],"factions":[{{"name":"势力","type":"类型","desc":"描述"}}],"world_history":"世界历史概要","unique_features":["特色1","特色2"]}}"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start, json_end = text.find("{"), text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                world_data = json.loads(text[json_start : json_end + 1])
                # 更新 story_bible.md
                bible_content = self._format_bible(world_data)
                bible_path.write_text(bible_content, encoding="utf-8")
                return {"success": True, "world_data": world_data}
        except Exception as e:
            logger.exception(f"[Editor] 世界观生成失败: {e}")
            logger.error(f"[Editor] 世界观生成失败: {e}")

        return {"success": False, "error": "世界观生成失败"}

    async def _handle_character(self, message: str, _ctx: dict | None = None) -> dict:
        """角色管理 — 生成/更新角色"""

        prompt = f"""你是角色设计师。根据用户需求设计角色。

用户需求: {message[:500]}

输出JSON:
{{"characters":[{{"name":"姓名","role":"protagonist/antagonist/supporting","gender":"男/女","age":"年龄","personality":["性格"],"background":"背景故事","abilities":"能力","relationships":[{{"target":"角色","type":"关系"}}],"arc":"角色弧线"}}]}}"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start, json_end = text.find("{"), text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                char_data = json.loads(text[json_start : json_end + 1])
                return {"success": True, "characters": char_data.get("characters", [])}
        except Exception as e:
            logger.exception(f"[Editor] 角色生成失败: {e}")
            logger.error(f"[Editor] 角色生成失败: {e}")

        return {"success": False, "error": "角色生成失败"}

    async def _handle_audit(self, _message: str, ctx: dict | None = None) -> dict:
        """运行33维审计"""
        draft = ctx.get("draft", "") if ctx else ""
        chapter = ctx.get("chapter", 0) if ctx else 0
        if not draft:
            return {"success": False, "error": "请提供待审计的正文"}

        audit_result = await self._audit_chapter(chapter, draft, ctx.get("blueprint", {}) if ctx else {})
        return {"success": True, "audit": audit_result}

    async def _handle_style(self, message: str, _ctx: dict | None = None) -> dict:
        """文风仿写/注入"""

        prompt = f"""你是文风分析专家。分析以下用户需求，提取风格指南。

用户需求: {message[:500]}

输出JSON:
{{"style_name":"风格名称","sentence_length_preference":"短/中/长","vocabulary_features":["特征"],"rhythm_pattern":"节奏模式","taboo_words":["禁用词"],"recommended_patterns":["推荐句式"],"ai_detection_rules":["去AI味规则"]}}"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start, json_end = text.find("{"), text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                style_data = json.loads(text[json_start : json_end + 1])
                return {"success": True, "style": style_data}
        except Exception as e:
            logger.exception(f"[Editor] 风格分析失败: {e}")
            logger.error(f"[Editor] 风格分析失败: {e}")

        return {"success": False, "error": "风格分析失败"}

    async def _handle_continue(self, message: str, ctx: dict | None = None) -> dict:
        """续写 — 基于已有章节继续"""

        snap = snapshot_manager.get_latest(self.book_id)
        last_chapter = snap.chapter if snap else 0
        next_chapter = last_chapter + 1
        return await self._handle_write_chapter(
            f"续写第{next_chapter}章，保持前文风格和情节连贯性 {message}", ctx
        )

    async def _handle_general(self, message: str, _ctx: dict | None = None) -> dict:
        """通用对话 — 直接回复作者"""

        brief = self.brief
        prompt = f"""你是昆仑创作引擎的主编Agent。你是作者的创作伙伴，帮助作者完成网文创作。

当前作品: {self.book_id}
作者意图: {brief.author_intent[:300]}
当前焦点: {brief.current_focus[:300]}

作者对你说: {message[:500]}

请用友好的语气回复作者。你可以:
- 回答创作相关问题
- 提供写作建议
- 帮助分析情节走向
- 推荐创作方向

回复（简洁，100-200字）:"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            return {"success": True, "reply": result.get("best_text", ""), "type": "chat"}
        except Exception as e:
            logger.exception(f"[Editor] 通用对话失败: {e}")
            logger.debug(f"主编对话意图分发失败，返回默认回复: {e}")
            return {
                "success": True,
                "reply": (
                    "收到你的消息。我是主编Agent，可以帮你创作、"
                    "规划大纲、设定世界观、设计角色。请告诉我你想做什么？"
                ),
                "type": "chat",
            }

    # ─── Agent 委托方法 ───

    async def _plan_chapter_intent(
        self, chapter: int, focus: str, word_target: int
    ) -> ChapterIntent:
        """Planner: 产出章节意图"""

        brief = self.brief
        prompt = f"""你是章节规划师。根据作者意图和当前焦点，为第{chapter}章产出章节意图。

作者意图: {brief.author_intent[:500]}
当前焦点: {brief.current_focus[:500]}
用户指令: {focus}
字数目标: {word_target}

输出JSON:
{{"must_keep":["必须包含的元素"],"must_avoid":["必须避免的元素"],"suggested_scenes":[{{"title":"场景","function":"作用","emotion":"情绪"}}],"emotion_target":"目标情绪","hook_requirement":"钩子类型","conflicts_to_advance":["需推进的冲突"]}}"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            json_start, json_end = text.find("{"), text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                data = json.loads(text[json_start : json_end + 1])
                return ChapterIntent(
                    chapter=chapter,
                    must_keep=data.get("must_keep", []),
                    must_avoid=data.get("must_avoid", []),
                    suggested_scenes=data.get("suggested_scenes", []),
                    emotion_target=data.get("emotion_target", ""),
                    hook_requirement=data.get("hook_requirement", ""),
                    word_target=word_target,
                    conflicts_to_advance=data.get("conflicts_to_advance", []),
                )
        except Exception as e:
            logger.exception(f"[Editor] 章节意图生成失败: {e}")
            logger.error(f"[Editor] 章节意图生成失败: {e}")

        return ChapterIntent(
            chapter=chapter,
            must_keep=[],
            must_avoid=[],
            suggested_scenes=[],
            word_target=word_target,
        )

    async def _generate_blueprint(self, chapter: int, intent: ChapterIntent) -> dict:
        """Architect: 生成章节蓝图"""

        snap = snapshot_manager.create_snapshot(self.book_id, chapter)
        architect = Architect()
        result = await architect.execute(
            {
                "book_id": self.book_id,
                "chapter": chapter,
                "kg_snapshot_id": snap.snapshot_id,
                "kg_summary": snap.to_summary(),
                "chapter_type": "normal",
                "preference_hints": (
                    f"本章需包含: {', '.join(intent.must_keep)}. "
                    f"需避免: {', '.join(intent.must_avoid)}"
                ),
            }
        )
        return result.get("blueprint", {})

    async def _write_chapter(self, chapter: int, blueprint: dict, intent: ChapterIntent) -> dict:
        """Writer: 生成正文（注入风格指纹 + 学习补丁）"""

        # 组装增强提示（风格 + 学习规则 + 控制文档）
        hints = f"字数目标: {intent.word_target}. 情绪: {intent.emotion_target}"
        ctx = self.syncer.assemble_pipeline_context(chapter)
        if ctx.style_prompt:
            hints += f"\n\n{ctx.style_prompt}"
        if ctx.learned_rules:
            hints += f"\n\n{ctx.learned_rules}"
        if ctx.consistency_warnings:
            hints += "\n\n⚠️ 注意事项:\n" + "\n".join(ctx.consistency_warnings)

        writer = Writer()
        return await writer._generate(
            {
                "blueprint": blueprint,
                "mode": "gacha_parallel_3",
                "kg_snapshot_id": "",
                "preference_hints": hints,
            }
        )

    async def _audit_chapter(self, chapter: int, draft: str, blueprint: dict | None = None) -> dict:
        """Auditor: 33维连续性审计（升级版）"""
        try:
            report = auditor33.run_audit(draft, chapter, blueprint or {}, self.book_id)
            return {
                "passed": report.passed,
                "overall_score": report.overall_score,
                "fatal_count": report.fatal_count,
                "warn_count": report.warn_count,
                "ai_detection_score": report.ai_detection_score,
                "summary": report.summary,
                "dimensions": {
                    d.dim_id: {
                        "name": d.name,
                        "score": d.score,
                        "level": d.level,
                        "detail": d.detail,
                    }
                    for d in report.dimensions
                },
                "gates": {
                    d.dim_id: {"level": d.level, "score": d.score, "detail": d.detail}
                    for d in report.dimensions
                },
            }
        except Exception as e:
            logger.exception(f"[Editor] 33维审计失败，降级到8门禁: {e}")
            logger.warning(f"[Editor] 33维审计失败，降级到8门禁: {e}")

            auditor = Auditor()
            return await auditor.execute(
                {"draft": draft, "blueprint": blueprint or {}, "chapter": chapter}
            )

    async def _revise_chapter(
        self, _chapter: int, draft: str, audit_result: dict, blueprint: dict
    ) -> dict:
        """Reviser: 自动修复（先反检测改写，再常规修订）"""

        # 先尝试反检测改写
        try:
            ai_score = audit_result.get("ai_detection_score", 100)
            if ai_score < 70:
                draft = await auditor33.auto_fix_ai_patterns(draft)
                logger.info(f"[Editor] 已执行反检测改写 (AI分: {ai_score:.0f})")
        except Exception as e:
            logger.exception(f"[Editor] 反检测改写跳过: {e}")
            logger.warning(f"[Editor] 反检测改写跳过: {e}")

        writer = Writer()
        return await writer._revise(
            {
                "draft": draft,
                "audit_report": audit_result,
                "blueprint": blueprint,
            }
        )

    async def _polish_chapter(self, draft: str) -> str:
        """Stylist: 去AI味 + 风格指纹注入（升级版）"""
        # 先加载风格指纹
        try:
            fp = style_analyzer.load_fingerprint(self.book_id)
            if fp:
                style_prompt = style_injector.build_style_prompt(fp)
                if style_prompt:
                    result = await gacha_engine.generate(
                        f"{style_prompt}\n\n请按照以上风格要求润色以下文本，保持原意和字数不变:\n\n{draft[:4000]}",
                        mode="single_fix",
                    )
                    polished = result.get("best_text", "")
                    if polished and len(polished) > len(draft) * 0.5:
                        return polished
        except Exception as e:
            logger.exception(f"[Editor] 风格注入跳过: {e}")
            logger.debug(f"[Editor] 风格注入跳过: {e}")

        # 降级到规则润色

        engineer = StyleEngineer()
        result = await engineer.execute({"draft": draft})
        return result.get("polished_draft", draft)

    async def _update_knowledge(self, chapter: int, draft: str, blueprint: dict):
        """Librarian: 更新KG + 7个真相文件 + 进化追踪"""
        try:
            # 1. KG更新

            m = Makefile()
            await m._run_kg_update(
                {
                    "book_id": self.book_id,
                    "chapter": chapter,
                    "blueprint": blueprint,
                    "draft": draft,
                }
            )

            # 2. 真相文件更新

            tm = get_truth_manager(self.book_id)
            tm.add_chapter_summary(
                chapter,
                draft[:200],
                blueprint.get("scenes", []),
                blueprint.get("characters_involved", []),
                blueprint.get("foreshadowing", {}).get("to_plant", []),
            )

            # 提取角色情绪更新
            scenes = blueprint.get("scenes", []) or []
            for scene in scenes:
                for char in scene.get("characters_involved", []):
                    tm.update_emotional_arc(
                        char, chapter, scene.get("emotion", "neutral"), 0.5, scene.get("title", "")
                    )

            # 注册新伏笔
            for hook in blueprint.get("foreshadowing", {}).get("to_plant", []):
                tm.register_hook(hook, chapter, chapter + 10, "medium", hook)

            # 回收伏笔
            for hook in blueprint.get("foreshadowing", {}).get("to_reveal", []):
                tm.reveal_hook(hook, chapter)

            # 检查逾期伏笔
            overdue = tm.check_overdue_hooks(chapter)
            if overdue:
                logger.warning(f"[Editor] {len(overdue)}个伏笔逾期")

            # 3. 进化追踪

            tracker = get_evolution_tracker(self.book_id)
            tracker.record_chapter(chapter, len(draft), 85.0, 0, 0)

            logger.info("[Editor] 知识更新完成: KG+真相文件+进化追踪")
        except Exception as e:
            logger.exception(f"[Editor] 知识更新部分失败: {e}")
            logger.warning(f"[Editor] 知识更新部分失败: {e}")

    # ─── 辅助方法 ───

    def _extract_chapter_number(self, message: str) -> int | None:

        m = re.search(r"第\s*(\d+)\s*章", message)
        return int(m.group(1)) if m else None

    def _extract_word_target(self, message: str) -> int | None:

        m = re.search(r"(\d{3,5})\s*字", message)
        return int(m.group(1)) if m else None

    def _extract_focus(self, message: str) -> str:
        return message[:500]

    def _save_outline(self, outline: dict):
        path = settings.DATA_DIR / "story" / self.book_id / "outline.json"
        path.write_text(json.dumps(outline, ensure_ascii=False, indent=2))

    def _save_runtime_artifacts(
        self, chapter: int, intent: ChapterIntent, blueprint: dict, audit: dict
    ):
        """保存运行时产物（对应 inkos 的 runtime artifacts）"""
        runtime_dir = settings.DATA_DIR / "story" / self.book_id / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        # chapter-XXXX.intent.md
        intent_md = f"# 第{chapter}章 创作意图\n\n"
        intent_md += "## 必须包含\n" + "\n".join(f"- {x}" for x in intent.must_keep) + "\n\n"
        intent_md += "## 必须避免\n" + "\n".join(f"- {x}" for x in intent.must_avoid) + "\n\n"
        intent_md += f"## 目标情绪: {intent.emotion_target}\n"
        intent_md += f"## 钩子要求: {intent.hook_requirement}\n"
        (runtime_dir / f"chapter-{chapter:04d}.intent.md").write_text(intent_md, encoding="utf-8")

        # context.json
        context = {
            "chapter": chapter,
            "intent": intent.__dict__ if hasattr(intent, "__dict__") else {},
            "blueprint": blueprint,
            "audit_summary": {k: v for k, v in audit.items() if k != "gates"},
        }
        (runtime_dir / f"chapter-{chapter:04d}.context.json").write_text(
            json.dumps(context, ensure_ascii=False, indent=2)
        )

    def _format_bible(self, data: dict) -> str:
        parts = ["# 故事设定\n"]
        if ps := data.get("power_system"):
            parts.append(f"## 力量体系: {ps.get('name', '')}\n{ps.get('rules', '')}\n")
        if locs := data.get("locations"):
            parts.append(
                "## 地点\n" + "\n".join(f"- {loc['name']}: {loc.get('desc', '')}" for loc in locs)
            )
        if facs := data.get("factions"):
            parts.append(
                "## 势力\n" + "\n".join(f"- {f['name']}: {f.get('desc', '')}" for f in facs)
            )
        if hist := data.get("world_history"):
            parts.append(f"## 世界历史\n{hist}")
        return "\n\n".join(parts)


# ─── 前端对话接口 ───


async def editor_chat(book_id: str, message: str, context: dict | None = None) -> dict:
    """供 API 调用的便捷接口"""
    editor = EditorInChief(book_id)
    return await editor.chat(message, context)


# 全局缓存
_editors: dict[str, EditorInChief] = {}


def get_editor(book_id: str) -> EditorInChief:
    if book_id not in _editors:
        _editors[book_id] = EditorInChief(book_id)
    return _editors[book_id]
