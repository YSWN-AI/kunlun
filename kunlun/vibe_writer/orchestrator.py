"""
昆仑创作引擎 — Vibe 总调度器 (Vibe Orchestrator)

Vibe Writing + 总调度 Agent：你只需要表达你的感受，AI 自动完成一切。

创作全流程:
  你: "我想写一本玄幻小说"
  AI: 自动完成 → 世界观设定 → 角色设计 → 大纲规划 → 逐章创作 → 质量把控 → 导出

  你: "让主角更强势一些"
  AI: 自动修改所有相关文件 → 角色状态 → 章节内容 → 冲突线 → 世界观

设计原则:
  1. 你说"什么"，AI 自己决定"怎么"做
  2. 所有文件操作自动化（不需要你手动改任何文件）
  3. 全生命周期覆盖：从零到精品完结到导出
  4. 每一次交互都是 Vibe Writing —— 只说感受，不提技术
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class BookProject:
    """一本书的完整项目状态"""

    book_id: str
    title: str = ""
    genre: str = "玄幻"
    status: str = "规划中"  # 规划中/创作中/润色中/已完结/已导出
    total_chapters: int = 0
    total_words: int = 0
    data_dir: Path = Path()

    # 创作进度
    outline_ready: bool = False
    world_ready: bool = False
    characters_ready: bool = False
    current_chapter: int = 0
    target_chapters: int = 100
    quality_score: float = 0.0


class VibeOrchestrator:
    """
    Vibe 总调度器 — 你的至高创作伙伴。

    不需要你知道任何内部机制，只需要表达你的创作意图。
    AI 自动理解、自动执行、自动修改所有文件。

    用法:
        master = VibeOrchestrator(workspace=Path("./data/books"))

        # 创作一本书
        await master.say("我想创作一本玄幻小说，主角从废柴开始逆袭")

        # 查看进度
        status = master.get_status()

        # 调整方向
        await master.say("让女主的戏份更多一些")

        # 最终导出
        await master.say("把这本书导出为 EPUB")
    """

    # 可识别的创作意图类型
    INTENT_TYPES = {
        "开书": ["新建", "创作", "写一本", "开书", "创建", "开始写"],
        "设定": ["世界观", "设定", "力量体系", "地图", "势力"],
        "角色": ["角色", "人物", "主角", "配角", "反派", "女主"],
        "大纲": ["大纲", "情节", "主线", "支线", "故事走向"],
        "写作": ["写章", "写第", "继续写", "创作章节", "生成"],
        "修改": ["修改", "调整", "重写", "润色", "改一改"],
        "质量": ["检查", "审计", "质量", "优化", "提升"],
        "导出": ["导出", "发布", "保存", "EPUB", "PDF", "生成文件"],
        "完结": ["完结", "完本", "结束"],
        "状态": ["进度", "状态", "怎么样了", "多少章了"],
    }

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path("./data/books")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._project: BookProject | None = None
        self._conversation: list[dict] = []  # 完整对话历史
        self._last_suggestion: str = ""
        # 本地模型配置
        self.use_local_model: bool = False
        self.local_model_name: str = "novel_style_qwen7b"

    def set_local_model(self, enabled: bool = True, model_name: str = "novel_style_qwen7b") -> None:
        """启用/禁用本地模型生成

        Args:
            enabled: 是否启用本地模型
            model_name: 本地模型名称（gacha中注册的适配器名）
        """
        self.use_local_model = enabled
        self.local_model_name = model_name
        logger.info(
            f"VibeOrchestrator: 本地模型 {'启用' if enabled else '禁用'} (model={model_name})"
        )

    # ═══════════════════════════════════════════════════════
    # 核心接口 — 你只需要说一句话
    # ═══════════════════════════════════════════════════════

    async def say(self, text: str) -> dict:
        """
        对你的创作伙伴说一句话。

        它会自动判断你想做什么，然后调用对应的能力去执行。
        你不需要告诉它"怎么做"，只需要说"想要什么"。

        示例:
            "我想写一本玄幻小说"           → 开书
            "设定一个力量体系"            → 世界观
            "写第一章"                   → 写作
            "让节奏更快一些"              → 修改
            "导出为EPUB"                 → 导出
            "这本书怎么样了"              → 状态
        """
        self._conversation.append({"role": "user", "content": text})

        # 1. 理解你的意图
        intent = self._classify_intent(text)

        # 2. 执行对应操作
        result = await self._execute(intent, text)

        self._conversation.append({"role": "assistant", "content": result.get("message", "")})

        return result

    # ═══════════════════════════════════════════════════════
    # 意图识别
    # ═══════════════════════════════════════════════════════

    def _classify_intent(self, text: str) -> str:
        """从一句话中理解你的意图"""
        for intent, keywords in self.INTENT_TYPES.items():
            if any(kw in text for kw in keywords):
                return intent
        # 如果已经有了项目，默认是"写作"
        if self._project and self._project.status in ("创作中", "润色中"):
            return "写作"
        return "开书"  # 没有项目默认开书

    # ═══════════════════════════════════════════════════════
    # 执行引擎 — AI 自动完成所有操作
    # ═══════════════════════════════════════════════════════

    async def _execute(self, intent: str, text: str) -> dict:
        """执行你的意图——AI自动完成所有工作"""
        handlers = {
            "开书": self._handle_create_book,
            "设定": self._handle_world_building,
            "角色": self._handle_characters,
            "大纲": self._handle_outline,
            "写作": self._handle_writing,
            "修改": self._handle_revision,
            "质量": self._handle_quality,
            "导出": self._handle_export,
            "完结": self._handle_finish,
            "状态": self._handle_status,
        }
        handler = handlers.get(intent, self._handle_status)
        return await handler(text)

    async def _handle_create_book(self, text: str) -> dict:
        """开书 — 自动创建完整项目"""

        # 1. 提取书名/题材
        import re

        title_match = re.search(r"(?:叫|名为|书名|标题)[《]?([^》。，]{2,10})[》]?", text)
        title = title_match.group(1) if title_match else "未命名"

        genre_match = re.search(r"(玄幻|仙侠|都市|科幻|历史|奇幻|武侠|言情)", text)
        genre = genre_match.group(1) if genre_match else "玄幻"

        book_id = f"book_{title}_{int(asyncio.get_event_loop().time()) % 10000:.0f}"
        project_dir = self.workspace / book_id
        project_dir.mkdir(parents=True, exist_ok=True)

        self._project = BookProject(
            book_id=book_id,
            title=title,
            genre=genre,
            data_dir=project_dir,
        )

        # 2. 自动生成世界观基础
        logger.info(f"[VibeMaster] 开书: {title} ({genre})")

        # 3. 创建初始文件结构
        (project_dir / "chapters").mkdir(exist_ok=True)
        (project_dir / "world").mkdir(exist_ok=True)
        (project_dir / "characters").mkdir(exist_ok=True)

        # 4. 保存项目配置
        self._save_project()

        message = (
            f"✅ 已创建《{title}》（{genre}）\n"
            f"📁 项目位置: {project_dir}\n"
            f"💡 接下来可以：\n"
            f"   • 说「构建世界观」— 设定力量体系、地图\n"
            f"   • 说「设计角色」— 创建主角和配角\n"
            f"   • 说「规划大纲」— 生成全书大纲\n"
            f"   • 说「写第一章」— 开始创作"
        )

        return {"success": True, "message": message, "project": self._project.__dict__}

    async def _handle_world_building(self, text: str) -> dict:
        """世界观构建 — 自动生成设定文件"""
        if not self._project:
            return {"success": False, "message": "还没有项目，先说「我想写一本小说」"}

        # 生成世界观文件
        world_file = self._project.data_dir / "world" / "world_setting.json"
        world_data = {
            "title": self._project.title,
            "genre": self._project.genre,
            "power_system": "待设定",
            "geography": "待设定",
            "history": "待设定",
            "factions": [],
            "rules": [],
            "created_from": text,
        }
        world_file.write_text(json.dumps(world_data, ensure_ascii=False, indent=2))

        self._project.world_ready = True
        self._save_project()

        message = (
            f"🌍 世界观框架已创建\n"
            f"📄 文件: {world_file}\n"
            f"💡 接下来可以：\n"
            f"   • 说「设定力量体系」— 完善修炼体系\n"
            f"   • 说「设计几个势力」— 创建宗门/国家\n"
            f"   • 说「设计角色」— 进入角色创作"
        )

        return {"success": True, "message": message}

    async def _handle_characters(self, text: str) -> dict:
        """角色设计 — 自动创建角色"""
        if not self._project:
            return {"success": False, "message": "还没有项目"}

        # 保存角色文件
        char_file = self._project.data_dir / "characters" / "characters.json"
        chars_data = {
            "title": self._project.title,
            "characters": [],
            "relationships": [],
            "created_from": text,
        }
        char_file.write_text(json.dumps(chars_data, ensure_ascii=False, indent=2))

        self._project.characters_ready = True
        self._save_project()

        return {
            "success": True,
            "message": "👥 角色框架已创建！说「写第一章」开始创作吧",
        }

    async def _handle_outline(self, text: str) -> dict:
        """大纲规划"""
        if not self._project:
            return {"success": False, "message": "还没有项目"}

        outline_file = self._project.data_dir / "outline.json"
        outline_data = {
            "title": self._project.title,
            "genre": self._project.genre,
            "arcs": [],
            "chapters_plan": [],
            "key_twists": [],
            "created_from": text,
        }
        outline_file.write_text(json.dumps(outline_data, ensure_ascii=False, indent=2))

        self._project.outline_ready = True
        self._save_project()

        return {
            "success": True,
            "message": "📋 大纲框架已创建！说「写第一章」开始创作",
        }

    async def _handle_writing(self, text: str) -> dict:
        """自动写作"""
        if not self._project:
            return {"success": False, "message": "还没有项目，先说「我想写一本小说」"}

        # 提取章节号（支持中文数字：十一→11, 二十→20, 二十一→21）
        import re

        ch_match = re.search(r"第([一二三四五六七八九十\d]+)章", text)
        if ch_match:
            ch_num_str = ch_match.group(1)
            if ch_num_str.isdigit():
                chapter = int(ch_num_str)
            else:
                # 中文数字→阿拉伯数字
                cn_map = {
                    "一": 1,
                    "二": 2,
                    "三": 3,
                    "四": 4,
                    "五": 5,
                    "六": 6,
                    "七": 7,
                    "八": 8,
                    "九": 9,
                    "十": 10,
                }
                if len(ch_num_str) == 1:
                    chapter = cn_map.get(ch_num_str, 1)
                elif ch_num_str.startswith("十"):
                    # 十X → 10+X (十一→11, 十九→19)
                    chapter = 10 + cn_map.get(ch_num_str[1], 0) if len(ch_num_str) > 1 else 10
                elif ch_num_str.endswith("十"):
                    # X十 → X*10 (二十→20, 九十→90)
                    chapter = cn_map.get(ch_num_str[0], 1) * 10
                else:
                    # X十Y → X*10+Y (二十一→21, 三十五→35)
                    parts = ch_num_str.split("十")
                    chapter = (
                        cn_map.get(parts[0], 1) * 10 + cn_map.get(parts[1], 0)
                        if len(parts) > 1
                        else 1
                    )
        else:
            chapter = self._project.current_chapter + 1

        from kunlun.vibe_writer import VibeContext, VibeWriter

        vibe = VibeWriter(self._project.book_id)
        vibe.set_context(
            VibeContext(
                chapter_title=f"第{chapter}章",
                genre=self._project.genre,
            )
        )

        # 通过 gacha 生成（支持本地模型）
        from kunlun.gacha.engine import gacha_engine

        prompt = f"写{self._project.genre}小说《{self._project.title}》第{chapter}章。{text}"

        if self.use_local_model:
            # 本地模型模式：分段生成长文本，避免重复
            logger.info(
                f"VibeOrchestrator: 使用本地模型 {self.local_model_name} 分段生成第{chapter}章"
            )
            long_result = await gacha_engine.generate_long_text(
                prompt=prompt,
                model=self.local_model_name,
                target_chars=2500,
                temperature=0.8,
                segment_chars=900,
            )
            draft = long_result.get("text", "")
            dedup_removed = long_result.get("dedup_removed", 0)
            logger.info(
                f"VibeOrchestrator: 分段生成完成，{len(draft)}字，去重删除{dedup_removed}处"
            )
        else:
            # API模型模式：多模型级联抽卡（长文本也用分段生成）
            logger.info(f"VibeOrchestrator: 使用API模型分段生成第{chapter}章")
            long_result = await gacha_engine.generate_long_text(
                prompt=prompt,
                target_chars=2500,
                temperature=0.8,
                segment_chars=900,
            )
            draft = long_result.get("text", "")
            dedup_removed = long_result.get("dedup_removed", 0)
        # 保存章节文件
        ch_file = self._project.data_dir / "chapters" / f"ch{chapter:04d}.md"
        ch_file.write_text(draft, encoding="utf-8")

        self._project.current_chapter = chapter
        self._project.total_chapters = max(self._project.total_chapters, chapter)
        self._project.total_words += len(draft)
        self._project.status = "创作中"
        self._save_project()

        message = (
            f"✍️ 第{chapter}章已完成（{len(draft)}字）\n"
            f"📄 文件: {ch_file}\n"
            f"💡 接下来：\n"
            f"   • 说「继续写」— 写下一章\n"
            f"   • 说「修改这一章」— 调整内容\n"
            f"   • 说「检查质量」— 运行审计\n"
            f"   • 说「第{chapter + 1}章写...」— 指定章节内容"
        )

        return {
            "success": True,
            "message": message,
            "chapter": chapter,
            "draft_preview": draft[:300],
            "word_count": len(draft),
        }

    async def _handle_revision(self, text: str) -> dict:
        """自动修改"""
        if not self._project:
            return {"success": False, "message": "还没有项目"}

        # 找到最新一章
        ch_dir = self._project.data_dir / "chapters"
        if not ch_dir.exists():
            return {"success": False, "message": "还没有写任何章节"}

        ch_files = sorted(ch_dir.glob("ch*.md"))
        if not ch_files:
            return {"success": False, "message": "还没有写任何章节"}

        latest = ch_files[-1]

        from kunlun.vibe_writer import VibeWriter

        vibe = VibeWriter(self._project.book_id)
        response = vibe.write(f"修改文本：{text}")

        if response.generated_text and len(response.generated_text) > 100:
            latest.write_text(response.generated_text, encoding="utf-8")
            return {
                "success": True,
                "message": f"✅ 已根据你的感受「{text}」修改了{latest.name}\n"
                f"💡 如果还不满意，再说一次你的感受",
            }

        return {"success": False, "message": "修改未生成有效内容"}

    async def _handle_quality(self, _text: str) -> dict:
        """质量检查"""
        if not self._project:
            return {"success": False, "message": "还没有项目"}

        ch_dir = self._project.data_dir / "chapters"
        if not ch_dir.exists():
            return {"success": False, "message": "还没有写任何章节"}

        ch_files = sorted(ch_dir.glob("ch*.md"))
        latest = ch_files[-1] if ch_files else None
        draft = latest.read_text(encoding="utf-8") if latest else ""

        if not draft:
            return {"success": False, "message": "没有内容可检查"}

        # 运行番茄流量检查
        try:
            from kunlun.audit.fanqie_gates import FanqieTrafficOptimizer

            report = FanqieTrafficOptimizer.check_chapter(
                draft, chapter=self._project.current_chapter
            )
            self._project.quality_score = report.potential_score

            message = "📊 质量检查结果:\n"
            message += f"   • 流量潜力: {report.traffic_rating}\n"
            message += f"   • AI倾向分: {report.fanqie_ai_score}/100\n"
            message += f"   • 章尾钩子: {'✅' if report.has_cliffhanger else '❌'}\n"
            message += f"   • 首300字: {'✅' if report.has_strong_opening else '❌'}\n"

            if report.suggestions:
                message += "   💡 建议:\n"
                for s in report.suggestions[:3]:
                    message += f"      • {s}\n"

            return {"success": True, "message": message, "report": report.to_dict()}
        except Exception as e:
            return {"success": False, "message": f"检查失败: {e}"}

    async def _handle_export(self, _text: str) -> dict:
        """自动导出"""
        if not self._project:
            return {"success": False, "message": "还没有项目"}

        ch_dir = self._project.data_dir / "chapters"
        if not ch_dir.exists():
            return {"success": False, "message": "还没有写任何章节"}

        # 自动合并所有章节
        export_file = self._project.data_dir / f"{self._project.title}_全文.md"
        ch_files = sorted(ch_dir.glob("ch*.md"))

        with export_file.open("w", encoding="utf-8") as f:
            f.write(f"# {self._project.title}\n\n")
            for ch_file in ch_files:
                content = ch_file.read_text(encoding="utf-8")
                ch_num = ch_file.stem.replace("ch", "")
                f.write(f"\n## 第{int(ch_num)}章\n\n{content}\n")

        self._project.status = "已导出"

        message = (
            f"📚 已导出《{self._project.title}》\n"
            f"   • 章节数: {len(ch_files)}章\n"
            f"   • 总字数: {self._project.total_words}字\n"
            f"   • 文件: {export_file}\n"
            f"💡 还可以说「导出为EPUB」生成电子书格式"
        )

        return {"success": True, "message": message, "export_path": str(export_file)}

    async def _handle_finish(self, _text: str) -> dict:
        """完结"""
        if not self._project:
            return {"success": False, "message": "还没有项目"}

        self._project.status = "已完结"
        self._save_project()

        message = (
            f"🎉 《{self._project.title}》已完结！\n"
            f"   • 总章节: {self._project.total_chapters}章\n"
            f"   • 总字数: {self._project.total_words}字\n"
            f"   💡 说「导出」生成最终文件"
        )
        return {"success": True, "message": message}

    async def _handle_status(self, _text: str = "") -> dict:
        """查看进度"""
        if not self._project:
            return {"success": True, "message": "还没有创作项目。说「我想写一本小说」开始吧！"}

        p = self._project
        progress_pct = min(100, p.current_chapter / max(1, p.target_chapters) * 100)

        message = (
            f"📊 《{p.title}》创作进度\n"
            f"   • 状态: {p.status}\n"
            f"   • 体裁: {p.genre}\n"
            f"   • 进度: 第{p.current_chapter}/{p.target_chapters}章 ({progress_pct:.0f}%)\n"
            f"   • 字数: {p.total_words}字\n"
            f"   • 质量分: {p.quality_score:.1f}/100\n"
            f"   • 世界观: {'✅' if p.world_ready else '⬜'}\n"
            f"   • 角色: {'✅' if p.characters_ready else '⬜'}\n"
            f"   • 大纲: {'✅' if p.outline_ready else '⬜'}\n"
            f"   💡 说「继续写」或「第{p.current_chapter + 1}章...」"
        )
        return {"success": True, "message": message}

    # ═══════════════════════════════════════════════════════
    # 项目管理
    # ═══════════════════════════════════════════════════════

    def _save_project(self):
        if not self._project:
            return
        path = self._project.data_dir / "project.json"
        data = {
            "book_id": self._project.book_id,
            "title": self._project.title,
            "genre": self._project.genre,
            "status": self._project.status,
            "total_chapters": self._project.total_chapters,
            "total_words": self._project.total_words,
            "current_chapter": self._project.current_chapter,
            "target_chapters": self._project.target_chapters,
            "outline_ready": self._project.outline_ready,
            "world_ready": self._project.world_ready,
            "characters_ready": self._project.characters_ready,
            "quality_score": self._project.quality_score,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def get_status(self) -> dict:
        """获取总调度器状态"""
        return {
            "project": self._project.__dict__ if self._project else None,
            "conversation_length": len(self._conversation),
            "workspace": str(self.workspace),
        }

    def get_conversation(self) -> list[dict]:
        """获取完整创作对话"""
        return self._conversation

    @property
    def has_project(self) -> bool:
        return self._project is not None


# 全局总调度器
_master: VibeOrchestrator | None = None


def get_orchestrator() -> VibeOrchestrator:
    global _master  # noqa: PLW0603
    if _master is None:
        _master = VibeOrchestrator()
    return _master
