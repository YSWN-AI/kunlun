"""
昆仑创作引擎 — KUNLUN.md 项目宪法引擎

8 段式项目宪法管理：生成、读取、分段更新、活跃状态同步、约束追加、Prompt 摘要、版本历史。
文件存储：data/books/book_<id>/KUNLUN.md + constitution_history.json
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 常量
# ══════════════════════════════════════════════════════

# 8 个宪法段落定义：(序号, 标准名, 别名集合)
SECTIONS: list[tuple[int, str, set[str]]] = [
    (1, "项目DNA", {"dna", "project_dna", "项目dna"}),
    (2, "世界系统", {"world", "world_system", "世界系统"}),
    (3, "角色", {"characters", "character", "角色"}),
    (4, "情节与结构", {"plot", "plot_structure", "情节与结构", "情节结构"}),
    (5, "风格指南", {"style", "style_guide", "风格指南"}),
    (6, "关键笔记与软约束", {"constraints", "notes", "关键笔记", "软约束", "关键笔记与软约束"}),
    (7, "活跃写作状态", {"active_state", "active", "活跃写作状态", "活跃状态"}),
    (8, "版本历史", {"history", "version_history", "版本历史"}),
]

# 段落标题正则：## 1. 项目DNA 或 ## 1、项目DNA
_SECTION_HEADER_RE = re.compile(r"^##\s+(\d+)[\.、]\s*(.+?)\s*$", re.MULTILINE)

# Prompt 摘要最大字符数
_PROMPT_CONTEXT_MAX = 4000


def _normalize_section_name(section: str) -> str:
    """将用户传入的段落名归一化为标准名。支持序号、英文 key、中文别名。"""
    s = section.strip().lower()
    # 纯数字
    if s.isdigit():
        idx = int(s)
        for num, name, _ in SECTIONS:
            if num == idx:
                return name
    # 别名匹配
    for _, name, aliases in SECTIONS:
        if s == name.lower() or s in aliases:
            return name
    # 模糊包含匹配
    for _, name, aliases in SECTIONS:
        if s in name.lower() or any(s in a for a in aliases):
            return name
    return section.strip()


def _section_header(num: int, name: str) -> str:
    return f"## {num}. {name}"


# ══════════════════════════════════════════════════════
# 主引擎
# ══════════════════════════════════════════════════════


class ConstitutionEngine:
    """KUNLUN.md 项目宪法引擎

    每本书一份宪法文件，8 个段落，支持分段读写、活跃状态自动更新、约束追加、版本历史追踪。
    """

    def __init__(self, book_id: str) -> None:
        self.book_id = book_id
        self.book_dir = settings.DATA_DIR / "books" / book_id
        self.constitution_path = self.book_dir / "KUNLUN.md"
        self.history_path = self.book_dir / "constitution_history.json"

    # ─── 路径与文件 ────────────────────────────────

    def _ensure_dir(self) -> None:
        self.book_dir.mkdir(parents=True, exist_ok=True)

    def _read_raw(self) -> str:
        if self.constitution_path.exists():
            return self.constitution_path.read_text(encoding="utf-8")
        return ""

    def _write_raw(self, content: str) -> None:
        self._ensure_dir()
        self.constitution_path.write_text(content, encoding="utf-8")

    def _append_history(self, action: str, detail: str) -> None:
        """追加一条版本历史记录到 constitution_history.json。"""
        history: list[dict[str, Any]] = []
        if self.history_path.exists():
            try:
                history = json.loads(self.history_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                history = []
        record = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "detail": detail,
        }
        history.append(record)
        # 最多保留 200 条
        if len(history) > 200:
            history = history[-200:]
        self._ensure_dir()
        self.history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ─── 模板生成 ──────────────────────────────────

    def generate_template(self, book_id: str, metadata: dict[str, Any]) -> str:
        """从 project.json 元数据生成初始 KUNLUN.md（男频网文场景示例）。

        Args:
            book_id: 作品 ID
            metadata: project.json 内容或包含 title/genre/target_chapters 等字段的字典

        Returns:
            生成的 KUNLUN.md 全文
        """
        title = metadata.get("title", "未命名作品")
        genre = metadata.get("genre", "玄幻")
        target_chapters = metadata.get("target_chapters", 200)
        total_words_plan = target_chapters * 3000  # 男频每章约 3000 字

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        content = f"""# KUNLUN.md — 项目宪法

> 作品：{title} | 类型：{genre} | 生成时间：{now_str}
> 本文件为昆仑创作引擎项目宪法，定义作品的核心 DNA、世界规则、角色、情节、风格与活跃状态。
> 静态段落（1/5）人工维护，半静态段落（2/3/4）随大纲更新，自动段落（6/7/8）由引擎维护。

---

## 1. 项目DNA

| 维度 | 内容 |
|------|------|
| 作品类型 | {genre}（男频网络文学） |
| 核心主题 | 逆天改命、强者为尊、兄弟情义、红颜相伴 |
| 目标读者 | 18-35 岁男性，偏好爽文、升级流、扮猪吃虎 |
| 情感承诺 | 主角从底层崛起，每 3-5 章一个小高潮，压抑后必爆发，反派必打脸 |
| 字数计划 | 目标 {target_chapters} 章，约 {total_words_plan} 字，单章 2500-3500 字 |
| 核心卖点 | 金手指设定新颖 + 节奏明快 + 反派智商在线 + 女主不花瓶 |

**一句话梗概**：少年身怀逆天秘宝，在宗门倾轧中步步为营，最终踏碎诸天、执掌轮回。

---

## 2. 世界系统

### 核心世界规则
- 修炼体系：炼气 → 筑基 → 金丹 → 元婴 → 化神 → 炼虚 → 合体 → 大乘 → 渡劫
- 每一大境界分初/中/后/巅峰四小层，越级挑战上限为一个大境界
- 灵力浓度决定修炼速度，秘境/遗迹为核心资源争夺点
- 宗门等级：三流 → 二流 → 一流 → 顶尖 → 圣地，等级决定资源分配

### 世界索引指针
- 世界观详情：`worlds/worldbuilding.md`
- 势力分布：`worlds/factions.json`
- 地理地图：`worlds/geography.md`
- 修炼体系详表：`worlds/cultivation_system.md`

---

## 3. 角色

### 角色索引
| 角色 | 身份 | 境界 | 与主角关系 | 核心特质 |
|------|------|------|-----------|---------|
| 主角 | 宗门杂役 → 亲传弟子 | 炼气三层（开局） | — | 隐忍果决、重情重义、杀伐果断 |
| 女主1 | 宗门圣女 | 筑基后期 | 亦师亦友 → 道侣 | 清冷孤傲、外冷内热 |
| 兄弟 | 同门师兄 | 炼气七层 | 生死兄弟 | 豪爽仗义、粗中有细 |
| 反派1 | 内门天才 | 筑基初期 | 死敌 | 心胸狭隘、背景深厚 |
| 师父 | 宗门长老 | 元婴期 | 引路人 | 神秘莫测、亦正亦邪 |

### 关系网络
- 主角 ↔ 女主1：救命之恩 → 并肩作战 → 情愫暗生
- 主角 ↔ 反派1：资源争夺 → 杀师之仇 → 不死不休
- 主角 ↔ 兄弟：同门学艺 → 秘境共患难 → 结为异性兄弟

> 详细人物卡：`characters/` 目录

---

## 4. 情节与结构

### 故事结构（三幕式 + 升级流）
- **第一幕（1-50章）**：开局获金手指 → 宗门小比崭露头角 → 初遇女主 → 与反派结仇
- **第二幕（51-150章）**：秘境探险 → 境界突破 → 宗门大比夺冠 → 反派背后势力登场 → 被迫出走
- **第三幕（151-{target_chapters}章）**：闯荡中州 → 建立势力 → 揭露身世之谜 → 最终决战 → 登顶

### 节奏规则
- 每 3 章一个小冲突，每 10 章一个中高潮，每 30 章一个大转折
- 打脸情节前置铺垫不超过 2 章，压抑不超过 5 章
- 升级间隔：炼气期每 5-8 章一级，筑基期每 10-15 章一级

### 大纲索引
- 总纲：`outline/master_outline.md`
- 分卷大纲：`outline/volume_*.md`
- 章节细纲：`outline/chapters/ch_{{n}}.md`

---

## 5. 风格指南

### 基础基调
- 主色调：热血、爽快、略带黑暗写实
- 叙事视角：第三人称限知（主角视角为主，关键场景切换反派视角）
- 整体风格：古龙式简洁 + 网文式节奏，短句为主，少用长难句

### 语言修辞
- 战斗描写：动作优先，一招一式清晰，少用形容词堆砌
- 环境描写：服务于氛围，不超过 3 句，避免大段景物描写
- 心理描写：主角内心独白用短句，反派心理用反讽
- 禁用：流水账式日常、过度解释设定、现代网络用语（除非角色设定需要）

### 对话风格
- 主角：话少而精，关键时刻一句话定乾坤，不啰嗦
- 反派：嚣张但有逻辑，不做无脑降智操作
- 女性角色：各有语言特色，不统一傻白甜
- 对话占比：每章对话不超过 40%，战斗/行动优先

### 节奏规则
- 章节开头 200 字内必须有钩子（冲突/悬念/反转）
- 章节结尾必须留悬念或情绪高点
- 信息密度：每章至少推进一个情节节点或揭示一个设定
- 避免：回忆杀超过 500 字、设定讲解超过 300 字、无冲突过渡章

---

## 6. 关键笔记与软约束

### 叙事禁忌
- 禁止主角降智：主角可以隐忍，但不能做愚蠢决策
- 禁止女主花瓶：女性角色必须有独立动机和行动线
- 禁止反派无脑：反派作恶要有合理动机和智商
- 禁止金手指滥用：每次使用必须有代价或限制
- 禁止烂尾伏笔：埋设的伏笔必须在 50 章内回收

### 用户约束
_（暂无，通过 API 或写作会话自动追加）_

---

## 7. 活跃写作状态

| 维度 | 内容 |
|------|------|
| 当前章节 | 第 1 章 |
| 当前卷 | 第一卷 · 宗门风云 |
| 主角境界 | 炼气三层 |
| 主角位置 | 青云宗 · 杂役院 |
| 近期情节 | 主角意外获得上古玉佩，灵根检测引发关注 |
| 待处理线索 | 1. 玉佩来历未明 2. 反派师兄的敌意 3. 圣女的试探 |
| 最后更新时间 | {now_str} |

### 角色快照
- 主角：隐忍中积蓄力量，对宗门规则已有不满
- 女主1：尚未正式登场
- 反派1：已注意到主角的异常

---

## 8. 版本历史

| 时间 | 操作 | 详情 |
|------|------|------|
| {now_str} | 初始化 | 从 project.json 生成初始宪法模板 |
"""
        self._write_raw(content)
        self._append_history("初始化", f"从 project.json 生成初始宪法模板，作品：{title}")
        logger.info(f"[Constitution] 已为 {book_id} 生成 KUNLUN.md 模板")
        return content

    # ─── 读取 ──────────────────────────────────────

    def read(self, book_id: str) -> str:  # noqa: ARG002
        """读取 KUNLUN.md 全文。"""
        return self._read_raw()

    def read_section(self, book_id: str, section: str) -> str:  # noqa: ARG002
        """读取指定段落内容。

        Args:
            book_id: 作品 ID
            section: 段落名（支持序号 1-8、英文 key、中文别名）

        Returns:
            段落正文（不含标题行），若段落不存在返回空字符串
        """
        raw = self._read_raw()
        if not raw:
            return ""
        target = _normalize_section_name(section)
        return self._extract_section(raw, target)

    def _extract_section(self, raw: str, section_name: str) -> str:
        """从全文中提取指定段落正文。"""
        # 找到所有段落标题位置
        headers = list(_SECTION_HEADER_RE.finditer(raw))
        for i, m in enumerate(headers):
            num = int(m.group(1))
            name = m.group(2).strip()
            std_name = _normalize_section_name(name)
            if std_name == section_name or str(num) == section_name:
                start = m.end()
                end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
                return raw[start:end].strip()
        return ""

    # ─── 更新 ──────────────────────────────────────

    def update_section(self, book_id: str, section: str, content: str) -> bool:  # noqa: ARG002
        """更新指定段落内容。

        Args:
            book_id: 作品 ID
            section: 段落名
            content: 新的段落正文（不含标题行）

        Returns:
            是否更新成功
        """
        raw = self._read_raw()
        if not raw:
            logger.warning(f"[Constitution] KUNLUN.md 不存在，无法更新段落 {section}")
            return False

        target = _normalize_section_name(section)
        headers = list(_SECTION_HEADER_RE.finditer(raw))

        for i, m in enumerate(headers):
            num = int(m.group(1))
            name = m.group(2).strip()
            std_name = _normalize_section_name(name)
            if std_name == target or str(num) == section:
                start = m.end()
                end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
                # 保留标题行，替换正文，前后加换行
                new_content = raw[:start] + "\n\n" + content.strip() + "\n\n" + raw[end:]
                self._write_raw(new_content)
                self._append_history("更新段落", f"段落 {num}.{name} 已更新")
                logger.info(f"[Constitution] 段落 {num}.{name} 已更新")
                return True

        logger.warning(f"[Constitution] 未找到段落 {section}")
        return False

    # ─── 活跃状态 ──────────────────────────────────

    def update_active_state(self, book_id: str, state: dict[str, Any]) -> bool:
        """自动更新"活跃写作状态"段落（写作会话后调用）。

        Args:
            book_id: 作品 ID
            state: 状态字典，支持字段：current_chapter, current_volume, protagonist_realm,
                   protagonist_location, recent_plot, pending_threads, character_snapshots

        Returns:
            是否更新成功
        """
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # 构建表格行
        rows = []
        field_map = [
            ("current_chapter", "当前章节", "第 1 章"),
            ("current_volume", "当前卷", "第一卷"),
            ("protagonist_realm", "主角境界", "炼气三层"),
            ("protagonist_location", "主角位置", "未知"),
            ("recent_plot", "近期情节", "暂无"),
            ("pending_threads", "待处理线索", "暂无"),
        ]
        for key, label, default in field_map:
            value = state.get(key, default)
            if isinstance(value, list):
                value = "；".join(str(v) for v in value)
            rows.append(f"| {label} | {value} |")
        rows.append(f"| 最后更新时间 | {now_str} |")

        table = "| 维度 | 内容 |\n|------|------|\n" + "\n".join(rows)

        # 角色快照
        snapshots = state.get("character_snapshots")
        if snapshots:
            if isinstance(snapshots, dict):
                snap_lines = [f"- **{k}**：{v}" for k, v in snapshots.items()]
            elif isinstance(snapshots, list):
                snap_lines = [f"- {s}" for s in snapshots]
            else:
                snap_lines = [str(snapshots)]
            snapshot_section = "\n\n### 角色快照\n" + "\n".join(snap_lines)
        else:
            snapshot_section = ""

        content = table + snapshot_section + "\n"
        result = self.update_section(book_id, "7", content)
        if result:
            chapter = state.get("current_chapter", "未知")
            self._append_history("活跃状态更新", f"写作会话后同步活跃状态，当前章节：{chapter}")
        return result

    # ─── 约束 ──────────────────────────────────────

    def add_constraint(self, book_id: str, constraint: str, source: str) -> bool:
        """添加约束到"关键笔记与软约束"段落。

        Args:
            book_id: 作品 ID
            constraint: 约束内容
            source: 约束来源（如 "用户"、"审计"、"自动检测"）

        Returns:
            是否添加成功
        """
        section_content = self.read_section(book_id, "6")
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        new_line = f"- [{source} · {now_str}] {constraint.strip()}"

        if "### 用户约束" in section_content:
            # 在用户约束小节追加
            parts = section_content.split("### 用户约束", 1)
            if "_（暂无" in parts[1]:
                # 替换占位符
                parts[1] = parts[1].replace("_（暂无，通过 API 或写作会话自动追加）_", new_line)
            else:
                parts[1] = parts[1].rstrip() + "\n" + new_line
            new_content = parts[0] + "### 用户约束" + parts[1]
        else:
            new_content = section_content.rstrip() + "\n\n### 用户约束\n" + new_line + "\n"

        result = self.update_section(book_id, "6", new_content)
        if result:
            self._append_history("添加约束", f"来源={source}，内容={constraint[:50]}...")
        return result

    # ─── Prompt 摘要 ───────────────────────────────

    def get_prompt_context(self, book_id: str) -> str:  # noqa: ARG002
        """提取用于 LLM Prompt 的宪法摘要。

        优先包含：项目DNA、风格指南、关键约束、活跃写作状态，截断到 _PROMPT_CONTEXT_MAX 字符。

        Returns:
            格式化的宪法摘要文本
        """
        raw = self._read_raw()
        if not raw:
            return ""

        sections_to_include = ["1", "5", "6", "7"]
        parts = ["# 项目宪法摘要（KUNLUN.md）\n"]

        for sec in sections_to_include:
            content = self._extract_section(raw, sec)
            if content:
                # 获取段落标准名
                std_name = _normalize_section_name(sec)
                parts.append(f"\n## {std_name}\n{content}")

        result = "\n".join(parts)
        if len(result) > _PROMPT_CONTEXT_MAX:
            result = result[:_PROMPT_CONTEXT_MAX] + "\n...（摘要已截断）"
        return result

    # ─── 版本历史 ──────────────────────────────────

    def get_version_history(self, book_id: str) -> list[dict[str, Any]]:  # noqa: ARG002
        """获取宪法变更历史。

        Returns:
            变更记录列表，按时间正序排列
        """
        if self.history_path.exists():
            try:
                return json.loads(self.history_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"[Constitution] 读取版本历史失败: {e}")
        return []
