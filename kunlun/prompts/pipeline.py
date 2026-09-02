"""
昆仑创作引擎 — Makefile 流水线 Prompt 模板

为 Makefile 流水线的每个状态节点提供独立的预设 Prompt 模板。
四个状态: 创意(idea) → 大纲(outline) → 分卷(volume) → 正文(draft)

使用方式:
    from kunlun.prompts.pipeline import PIPELINE_PROMPTS
    template = PIPELINE_PROMPTS["idea"]
    prompt = template.format(**context)
"""

from __future__ import annotations

from dataclasses import dataclass

# ─── 状态机 Prompt 模板 ─────────────────────────────

IDEA_PROMPT = """# 创作阶段: 创意构思

你是一位经验丰富的网文策划编辑，正在帮助作者构思一个爆款网文创意。

## 当前状态
- 目标题材: {genre}
- 目标平台: {platform}
- 目标字数: {word_count}
- 已有灵感: {inspiration}

## 任务要求
1. **核心卖点**: 用一句话说清楚这本书为什么能火
2. **金手指设计**: 设定主角的核心能力，含来源/形式/限制/成长路径
3. **冲突引擎**: 定义推动全书的核心冲突(人vs人/人vs世界/人vs自己)
4. **受众画像**: 目标读者是谁，他们为什么付费
5. **差异化**: 与同类热门作品的区别在哪里

## 输出格式
请输出 JSON 格式:
{{
    "core_hook": "一句话核心卖点",
    "golden_finger": {{
        "name": "金手指名称",
        "source": "获取方式",
        "mechanism": "运作机制",
        "limitation": "使用限制",
        "growth_path": ["阶段1", "阶段2", "阶段3"]
    }},
    "conflict_engine": {{
        "type": "人vs人/人vs世界/人vs自己",
        "primary": "核心冲突描述",
        "secondary": ["次要冲突1", "次要冲突2"]
    }},
    "target_audience": {{
        "demographic": "读者画像",
        "pain_point": "他们想看什么",
        "pay_point": "付费意愿触发点"
    }},
    "differentiation": "差异化分析"
}}"""

OUTLINE_PROMPT = """# 创作阶段: 大纲规划

你是一位资深网文大纲设计师，正在为一个验证过的创意构建完整的故事框架。

## 已知信息
- 核心卖点: {core_hook}
- 金手指: {golden_finger}
- 冲突引擎: {conflict_engine}
- 受众画像: {target_audience}
- 计划章节数: {total_chapters}

## 任务要求
1. **三幕结构**: 按照网文惯用的"建立→升级→巅峰"三幕划分全书
2. **爽点分布**: 标注关键打脸/升级/身份反转节点在第几章
3. **节奏控制**: 确保每20-30章一次大高潮，每5-10章一次小高潮
4. **伏笔规划**: 列出全书重大伏笔及其揭示时机

## 输出格式
请输出 JSON 格式:
{{
    "three_act_structure": {{
        "act1_build": {{"chapters": "1-N", "goal": "建立世界观+主角崛起"}},
        "act2_escalate": {{"chapters": "N-M", "goal": "冲突升级+势力扩张"}},
        "act3_climax": {{"chapters": "M-K", "goal": "终极对决+结局"}}
    }},
    "pleasure_points": [
        {{"chapter": N, "type": "打脸/升级/身份反转", "description": "..."}}
    ],
    "pace_map": {{
        "high_tempo_chapters": [1,2,3,...],
        "medium_tempo_chapters": [...],
        "low_tempo_chapters": [...]
    }},
    "foreshadowing": [
        {{"id": "fp_001", "plant_chapter": N, "reveal_chapter": M, "description": "..."}}
    ]
}}"""

VOLUME_PROMPT = """# 创作阶段: 分卷规划

你正在为一个已完成大纲的创作项目规划分卷结构。

## 已知信息
- 大纲结构: {outline_structure}
- 爽点地图: {pleasure_points}
- 伏笔列表: {foreshadowing_list}
- 每卷字数: {words_per_volume}
- 当前卷号: {volume_number}

## 任务要求
1. **本卷核心冲突**: 本卷要解决的核心问题
2. **章节拆分**: 将本卷划分为具体章节，每章标注核心事件
3. **人物弧光**: 本卷内主要角色的成长变化
4. **战力升级**: 主角在本卷达到的修为/地位层次
5. **钩子设计**: 本卷末的悬念钩子

## 输出格式
请输出 JSON 格式:
{{
    "volume_number": {volume_number},
    "core_conflict": "本卷核心冲突",
    "chapters": [
        {{
            "chapter_number": N,
            "title": "章节标题",
            "core_event": "本章核心事件",
            "pleasure_type": "打脸/升级/日常",
            "word_count_target": N
        }}
    ],
    "character_arcs": [
        {{"character": "角色名", "from": "起点状态", "to": "终点状态"}}
    ],
    "power_progression": "战力/地位升级路径",
    "volume_hook": "卷末钩子"
}}"""

DRAFT_PROMPT = """# 创作阶段: 正文生成

你正在创作网文章节的正文内容。按照前面建立的蓝图、大纲和分卷规划，写出高质量网文。

## 章节信息
- 书名: {book_title}
- 卷号: {volume_number}
- 章节号: {chapter_number}
- 章节标题: {chapter_title}
- 章节类型: {chapter_type}
- 核心事件: {core_event}
- 目标字数: {word_count_target}

## 已知上下文
{kg_context}

## 创作要求

### 黄金三章标准 (如为前3章)
{three_chapter_rules}

### 风格要求
{style_rules}

### 技术指标
- 目标字数: {word_count_target}字
- 对话占比: ≥25%
- 段落长度: 2-6行(不连续3段超过5行)
- 句长分布: 3-8字(战斗)+8-15字(日常)+10-20字(情感)
- 爽点要求: 本章至少1个情绪起伏点
- 钩子要求: 章末必须有悬念或爽点收尾

## 输出
请直接输出正文内容，不要包含JSON标记或元数据。章节标题自行添加。"""


# ─── 模板管理 ────────────────────────────────────────


@dataclass
class PipelineTemplate:
    name: str
    stage: str  # idea / outline / volume / draft
    template: str
    description: str = ""


# 全局模板注册表
PIPELINE_PROMPTS: dict[str, PipelineTemplate] = {
    "idea": PipelineTemplate(
        name="创意构思",
        stage="idea",
        template=IDEA_PROMPT,
        description="策划爆款网文创意，定义核心卖点、金手指、冲突引擎和受众画像",
    ),
    "outline": PipelineTemplate(
        name="大纲规划",
        stage="outline",
        template=OUTLINE_PROMPT,
        description="构建完整故事框架，三幕结构+爽点分布+伏笔规划",
    ),
    "volume": PipelineTemplate(
        name="分卷规划",
        stage="volume",
        template=VOLUME_PROMPT,
        description="将大纲拆分为具体卷册，分配章节事件和人物弧光",
    ),
    "draft": PipelineTemplate(
        name="正文生成",
        stage="draft",
        template=DRAFT_PROMPT,
        description="按蓝图生成网文章节正文，遵循风格规则和技术指标",
    ),
}


def get_template(stage: str) -> PipelineTemplate | None:
    """按阶段名获取模板"""
    return PIPELINE_PROMPTS.get(stage)


def format_template(stage: str, **kwargs) -> str:
    """
    获取并格式化指定阶段的 Prompt 模板。

    Args:
        stage: idea / outline / volume / draft
        **kwargs: 模板变量

    Returns:
        格式化后的 Prompt 字符串
    """
    tpl = get_template(stage)
    if not tpl:
        return f"# 未知阶段: {stage}\n\n无可用模板。"
    try:
        return tpl.template.format(**kwargs)
    except KeyError as e:
        return f"{tpl.template}\n\n[警告: 缺少变量 {e}]"


def inject_skill_context(stage: str, base_prompt: str) -> str:
    """
    为 Prompt 注入对应阶段的技能指引。

    Args:
        stage: 当前阶段
        base_prompt: 基础 Prompt

    Returns:
        增强后的 Prompt
    """
    from kunlun.skills import skill_loader

    stage_skill_map = {
        "idea": ["黄金三章模板"],
        "outline": ["黄金三章模板", "过签审核清单"],
        "volume": ["过签审核清单", "fanqie-novel-skills"],
        "draft": ["口语化改写规则", "过签审核清单", "fanqie-novel-skills"],
    }

    skills_to_inject = stage_skill_map.get(stage, [])
    injection = skill_loader.inject_as_system_prompt(skills_to_inject)

    if not injection:
        return base_prompt

    return f"{base_prompt}\n\n{injection}"
