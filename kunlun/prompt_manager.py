"""
昆仑创作引擎 — 提示词管理器 (PromptManager)

设计目标: 开放提示词给用户自定义，同时保持底层架构不变

分层覆盖机制:
  Layer 0: 系统默认 Prompt (内置，不可修改) → kunlun/prompts/*.py
  Layer 1: 用户覆盖 Prompt (可修改)        → data/prompts/{book_id}/*.md
  Layer 2: 当前会话临时覆盖 (运行时)        → API请求参数或内存

优先级: Layer 2 > Layer 1 > Layer 0

每个Agent/每个阶段都可以独立覆盖:
  - architect.md     → 覆盖 Architect 的系统提示词
  - writer.md        → 覆盖 Writer 的系统提示词
  - auditor.md       → 覆盖 Auditor 的审计要求
  - pipeline_idea.md → 覆盖创意阶段Prompt
  - pipeline_draft.md→ 覆盖正文生成Prompt
  - society_*.md     → 覆盖社会推演各维度Prompt

使用方式:
  # 在Agent中获取提示词
  prompt = prompt_manager.get("architect", book_id="my_book")

  # 用户通过API修改提示词
  POST /api/v1/prompts/{book_id}/{agent_name}
  {"prompt": "你是一个...（用户自定义内容）"}
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from kunlun.config import settings

# 可自定义的 Agent/阶段列表
CUSTOMIZABLE_PROMPTS = [
    "architect",  # 建筑师Agent
    "writer",  # 写手Agent
    "auditor",  # 审计员Agent
    "sociologist",  # 社会学家Agent
    "style_engineer",  # 风格工程师Agent
    "pipeline_idea",  # 创意阶段
    "pipeline_outline",  # 大纲阶段
    "pipeline_volume",  # 分卷阶段
    "pipeline_draft",  # 正文生成
    "revise",  # 修订指令
    "icu",  # ICU检查指令
]


@dataclass
class PromptSource:
    """提示词来源信息"""

    agent: str
    book_id: str
    source: str  # "system" / "user_override" / "session"
    content: str
    has_override: bool = False


class PromptManager:
    """
    提示词管理器

    管理三层提示词覆盖, 提供统一的获取/修改/重置接口。
    """

    def __init__(self):
        # 用户覆盖目录: data/prompts/{book_id}/{agent}.md
        self._overrides_dir = settings.DATA_DIR / "prompts"
        self._overrides_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存: {(book_id, agent): content}
        self._session_overrides: dict[tuple[str, str], str] = {}

    # ─── 核心获取接口 ─────────────────────────────────

    def get(self, agent: str, book_id: str = "default", default: str = "") -> str:
        """
        获取指定Agent/阶段的提示词。

        优先级: session覆盖 > 用户文件覆盖 > 系统默认
        """
        # Level 2: 会话覆盖
        session_key = (book_id, agent)
        if session_key in self._session_overrides:
            return self._session_overrides[session_key]

        # Level 1: 用户文件覆盖
        user_path = self._user_override_path(book_id, agent)
        if user_path.exists():
            content = user_path.read_text(encoding="utf-8").strip()
            if content:
                return content

        # Level 0: 返回系统默认（由调用方提供）
        return default

    def get_source(self, agent: str, book_id: str = "default") -> PromptSource:
        """获取提示词及其来源信息"""
        session_key = (book_id, agent)
        if session_key in self._session_overrides:
            return PromptSource(
                agent=agent,
                book_id=book_id,
                source="session",
                content=self._session_overrides[session_key],
                has_override=True,
            )
        user_path = self._user_override_path(book_id, agent)
        if user_path.exists():
            content = user_path.read_text(encoding="utf-8")
            return PromptSource(
                agent=agent,
                book_id=book_id,
                source="user_override",
                content=content,
                has_override=True,
            )
        return PromptSource(
            agent=agent, book_id=book_id, source="system", content="", has_override=False
        )

    # ─── 用户覆盖管理 ─────────────────────────────────

    def set_user_override(self, agent: str, book_id: str, content: str):
        """设置用户文件覆盖"""
        if agent not in CUSTOMIZABLE_PROMPTS:
            raise ValueError(f"不可自定义的提示词: {agent}，可选: {CUSTOMIZABLE_PROMPTS}")
        user_path = self._user_override_path(book_id, agent)
        user_path.parent.mkdir(parents=True, exist_ok=True)
        user_path.write_text(content, encoding="utf-8")
        logger.info(f"[PromptManager] {book_id}/{agent} 提示词已保存 ({len(content)}字符)")

    def set_session_override(self, agent: str, book_id: str, content: str):
        """设置会话覆盖（重启后失效）"""
        self._session_overrides[(book_id, agent)] = content

    def reset_user_override(self, agent: str, book_id: str):
        """删除用户覆盖，恢复系统默认"""
        user_path = self._user_override_path(book_id, agent)
        if user_path.exists():
            user_path.unlink()
            logger.info(f"[PromptManager] {book_id}/{agent} 已恢复系统默认")
        # 也清除会话覆盖
        self._session_overrides.pop((book_id, agent), None)

    def reset_all_overrides(self, book_id: str):
        """删除某本书的所有用户覆盖"""
        book_dir = self._overrides_dir / book_id
        if book_dir.exists():
            import shutil

            shutil.rmtree(book_dir)
            logger.info(f"[PromptManager] {book_id} 所有提示词已恢复系统默认")
        # 清除该书的会话覆盖
        keys_to_remove = [k for k in self._session_overrides if k[1] == book_id]
        for k in keys_to_remove:
            self._session_overrides.pop(k, None)

    def list_overrides(self, book_id: str) -> list[PromptSource]:
        """列出某本书的所有提示词状态"""
        results = []
        for agent in CUSTOMIZABLE_PROMPTS:
            source = self.get_source(agent, book_id)
            results.append(source)
        return results

    # ─── 注入支持 ─────────────────────────────────────

    def inject_into_prompt(self, base_prompt: str, agent: str, book_id: str = "default") -> str:
        """
        将用户覆盖注入到系统Prompt中。

        如果用户有自定义提示词，把它作为额外约束追加到系统Prompt末尾。
        保持底层架构不变，只是给LLM增加用户自定义的指令。
        """
        user_content = self.get(agent, book_id)
        if user_content:
            # 追加而非替换：保持底层架构不变
            return f"{base_prompt}\n\n## 📝 作者自定义指令\n{user_content}\n"
        return base_prompt

    def inject_with_params(self, base_prompt: str, agent: str, book_id: str = "default") -> str:
        """注入自定义提示词 + 模型参数脚注（含推荐范围）"""
        result = self.inject_into_prompt(base_prompt, agent, book_id)
        try:
            from kunlun.model_params import model_param_manager

            footnote = model_param_manager.build_footnote(agent, book_id)
            result += footnote
        except Exception:
            logger.debug("脚注追加失败")
        return result

    # ─── 内部方法 ─────────────────────────────────────

    def _user_override_path(self, book_id: str, agent: str) -> Path:
        """用户覆盖文件的路径"""
        return self._overrides_dir / book_id / f"{agent}.md"


# 全局单例
prompt_manager = PromptManager()
