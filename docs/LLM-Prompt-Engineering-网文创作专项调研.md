# LLM Prompt Engineering — 网文创作专项调研与优化方案

> 调研时间：2026-06-10 | 关联：500项目架构调研、12维度开源方案
> 核心问题：昆仑现有 Prompt 体系如何从"手工艺"升级为"工程化"？

---

## 一、行业最佳实践速查

### 1.1 业界 Prompt Engineering 五大范式

| 范式 | 代表 | 核心思想 | 昆仑适用性 |
|------|------|---------|:---:|
| **手写提示词** | 传统方式 | 人工迭代 Prompt | ⭐⭐ 当前主流，维护成本高 |
| **Few-shot / In-context** | GPT-4 论文 | 提供示例引导输出 | ⭐⭐⭐ 可用于格式化输出 |
| **Chain-of-Thought (CoT)** | Wei et al. 2022 | 引导模型逐步推理 | ⭐⭐⭐⭐ 审计/大纲生成适用 |
| **DSPy (声明式编程)** | Stanford 2024 | 用代码定义任务，优化器自动编译 Prompt | ⭐⭐⭐⭐⭐ Pipeline 重构目标 |
| **Meta-Prompting** | OpenAI 2025 | 用 LLM 优化自己的 Prompt | ⭐⭐⭐ 自动调优技能文件 |

### 1.2 网文创作 Prompt 的核心挑战

| 挑战 | 描述 | 昆仑现状 |
|------|------|---------|
| **长上下文管理** | 章节动辄3000-5000字，Prompt + 上下文易超限 | `ContextBudgetAllocator` 已解决 |
| **风格一致性** | 跨章节保持统一文风 | 仅 `StyleFingerprint` 采样，Prompt未融入 |
| **情节连贯性** | 人物弧线/伏笔/因果关系不破裂 | 通过 `truth/` 文件 + KG 快照解决 |
| **去AI味** | 避免"然而/此外/总之"等AI套话 | Writer Prompt 中硬编码禁用词 |
| **中文特性** | 成语/诗词/修辞格/口语化 | jieba分词辅助，Prompt无专门处理 |
| **爽点密度** | 每章维持读者兴奋度 | `pleasure_points` 已有规划，Prompt 有爽点排布 |
| **Tommy效应** | 过几章就忘记之前的设定 | KG Snapshot + Truth 文件已缓解 |

---

## 二、昆仑现有 Prompt 体系诊断

### 2.1 架构评分

| 维度 | 评分 | 说明 |
|------|:---:|------|
| 模板结构化 | 7/10 | pipeline.py 模板结构良好，society.py 维度全面 |
| 管理一致性 | 4/10 | pipeline/architect/writer/society 四种不同构建方式 |
| Token 预算 | 6/10 | Architect/Writer 有，Pipeline/Society 无 |
| 技能注入 | 5/10 | 仅 Pipeline 阶段注入，Agent 内部不注入 |
| 版本管理 | 1/10 | 零版本管理，无变更追踪 |
| 效果评估 | 2/10 | 无 A/B 测试，无 Prompt 效果量化 |
| 可覆盖性 | 6/10 | prompt_manager 三级覆盖设计好，但 Agent 内联 Prompt 不走它 |
| **综合** | **4.4/10** | |

### 2.2 八大问题与根因

| # | 问题 | 根因 | 影响 |
|---|------|------|------|
| 1 | 四种 Prompt 构建方式并存 | 历史演进，缺少统一抽象 | 维护困难，风格不一致 |
| 2 | Agent 内联 Prompt 不走 PromptManager | 代码直写，未接入覆盖体系 | 用户无法自定义 Writer/Architect 的 Prompt |
| 3 | 技能注入范围有限 | `inject_skill_context` 只挂在 pipeline.py | skills/ 文件仅在特定阶段生效 |
| 4 | 无效果量化 | 缺少 Prompt level 的 A/B 测试 | 无法知道哪个 Prompt 版本更好 |
| 5 | 社会推演 38/44 维度空置 | 扩展文件质量参差 | 大量预留维度从未生效 |
| 6 | learned_patches.md 手动维护 | 无自动化规则提取 | 学习补丁利用率极低 |
| 7 | 无 Prompt 压缩策略 | 只在 Writer 做了头尾截断 | 其他 Agent 超长时直接裁剪 |
| 8 | 平台特定规则硬编码 | "番茄流量门禁"等写在 Prompt 中 | 换平台需改 Prompt |

---

## 三、优化方案：Prompt as Code

### 3.1 核心理念：DSPy 范式引入

> "Prompting is the new programming—but it shouldn't be artisanal."
> — Stanford DSPy Paper

将 Prompt 视为**代码**（而非自然语言字符串），引入：
- **签名 (Signature)**：用 Pydantic 定义输入/输出类型
- **模块 (Module)**：可组合的 Prompt 单元
- **优化器 (Optimizer)**：基于效果自动调优 Prompt

### 3.2 昆仑版 Prompt as Code 实现

```python
# kunlun/prompts/signatures.py（新建）
"""Prompt 签名定义 — 对标 DSPy Signature，用 Pydantic 定义输入/输出"""

from pydantic import BaseModel, Field
from typing import Optional


class ChapterBlueprintInput(BaseModel):
    """Architect 输入签名"""
    chapter_number: int = Field(description="章节编号")
    chapter_type: str = Field(description="章节类型: normal/climax/battle/transition/epilogue")
    kg_snapshot_id: str = Field(description="KG快照ID")
    kg_summary: str = Field(description="KG快照摘要（人物/弧线/伏笔/世界观）")
    preference_hints: Optional[str] = Field(default="", description="作者偏好提示")
    rag_context: Optional[str] = Field(default="", description="RAG检索到的相关段落")


class ChapterBlueprintOutput(BaseModel):
    """Architect 输出签名"""
    scenes: list[dict] = Field(description="场景设计列表")
    emotion_curve: dict = Field(description="情绪曲线 {start,end}")
    pleasure_points: list[dict] = Field(description="爽点排布")
    foreshadowing: dict = Field(description="伏笔指令 {to_reveal, to_plant}")
    arc_stage: str = Field(description="弧线阶段 (12阶段英雄之旅)")
    hook_requirement: dict = Field(description="结尾钩子 {type, description}")
    word_count_target: int = Field(description="字数目标")
    audit_risk_marks: dict = Field(description="审计风险预标")


class DraftGenerationInput(BaseModel):
    """Writer 输入签名"""
    blueprint: dict = Field(description="Architect 生成的蓝图")
    kg_snapshot_id: str = Field(description="KG快照ID")
    mode: str = Field(default="gacha_parallel_3", description="Gacha模式")
    preference_hints: Optional[str] = Field(default="", description="作者偏好")


class DraftGenerationOutput(BaseModel):
    """Writer 输出签名"""
    draft: str = Field(description="生成的章节正文")
    word_count: int = Field(description="实际字数")
    model_used: str = Field(description="使用的模型")
    scores: dict = Field(default_factory=dict, description="9维评分")
```

### 3.3 统一 Prompt 注册表

```python
# kunlun/prompts/registry.py（新建）
"""统一 Prompt 注册表 — 所有 Prompt 都走这里"""

from dataclasses import dataclass, field
from typing import Optional, Callable
from loguru import logger


@dataclass
class PromptSpec:
    """Prompt 规范 — 声明式定义"""
    name: str                    # 唯一标识 (如 "architect.blueprint")
    version: int = 1             # 版本号
    description: str = ""        # 用途说明
    input_schema: Optional[type] = None   # Pydantic 输入模型
    output_schema: Optional[type] = None  # Pydantic 输出模型
    template: str = ""           # 系统默认模板
    skills: list[str] = field(default_factory=list)  # 关联的技能文件
    token_budget: int = 8000     # Token 预算
    budget_allocation: Optional[dict] = None  # 预算分配比例
    platform_rules: dict = field(default_factory=dict)  # 平台特定规则
    
    def build_context(self, **kwargs) -> str:
        """构建 Prompt 上下文（模板 + 技能注入 + 预算控制）"""
        # 1. 模板填充
        prompt = self.template.format(**kwargs)
        
        # 2. 技能注入
        for skill_file in self.skills:
            prompt += f"\n\n{load_skill_text(skill_file)}"
        
        # 3. Token 预算控制
        if self.token_budget and self.budget_allocation:
            prompt = apply_budget(prompt, self.token_budget, self.budget_allocation)
        
        return prompt


# 全局注册表
PROMPT_REGISTRY: dict[str, PromptSpec] = {}
```

### 3.4 技能文件自动优化

```python
# kunlun/prompts/optimizer.py（新建）
"""Prompt 优化器 — 基于反馈自动改进 Prompt

对标 DSPy BootstrapFewShot + MIPROv2 优化器，但针对网文场景简化。
"""

from collections import defaultdict
from typing import Optional
import json
from pathlib import Path
from loguru import logger


class PromptOptimizer:
    """Prompt 自动优化器
    
    从审计反馈中自动提取高频问题，生成针对性的 Prompt 补丁。
    
    工作原理:
    1. 收集审计失败的样本（通过 8 gates / 33dim audit 的报告）
    2. 按失败类型聚类
    3. 提取高频失败模式
    4. 生成针对性的 Prompt 增强指令
    5. 作为 learned_patches 注入到对应 Prompt
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._failure_history: dict[str, list[dict]] = defaultdict(list)
        self._patch_threshold = 5  # 同一模式出现5次才生成补丁
    
    def record_failure(self, prompt_name: str, failure_type: str, detail: dict):
        """记录一次 Prompt 相关的失败"""
        self._failure_history[prompt_name].append({
            "type": failure_type,
            "detail": detail,
        })
    
    def analyze_and_generate_patches(self) -> dict[str, str]:
        """分析失败历史，生成 Prompt 补丁"""
        patches = {}
        
        for prompt_name, failures in self._failure_history.items():
            # 按失败类型聚合
            by_type = defaultdict(list)
            for f in failures:
                by_type[f["type"]].append(f)
            
            for fail_type, group in by_type.items():
                if len(group) >= self._patch_threshold:
                    patch = self._generate_patch(prompt_name, fail_type, group)
                    if patch:
                        patches[f"{prompt_name}:{fail_type}"] = patch
        
        return patches
    
    def _generate_patch(self, prompt_name: str, fail_type: str, samples: list) -> Optional[str]:
        """为特定失败类型生成针对性补丁"""
        # 已知的失败类型 → 补丁模板映射
        PATCH_TEMPLATES = {
            "ai_detection": (
                "\n## ⚠️ 近期高频问题: AI味过重\n"
                f"最近 {len(samples)} 章触发AI检测。请特别注意:\n"
                "- 避免'然而/此外/总而言之/值得注意的是'等套话\n"
                "- 句式长短交替，段落长度不均匀\n"
                "- 对话中增加语气词（啊、呢、吧、嘛）\n"
                "- 用具体感官描写替代抽象形容词\n"
            ),
            "pleasure_gap": (
                f"\n## ⚠️ 爽点密度不足\n"
                f"最近 {len(samples)} 章爽点间隔过大。请确保:\n"
                "- 每2000字至少1个爽点（打脸/突破/揭秘/逆袭）\n"
                "- 爽点类型交替，避免连续3个同类型\n"
                "- 结尾必须有钩子（悬念/反转/新目标）\n"
            ),
            "ooc": (
                f"\n## ⚠️ 角色OOC(Out of Character)\n"
                f"最近 {len(samples)} 章角色行为与设定不符。\n"
                f"- 角色 {', '.join(s.get('detail', {}).get('character', '未知') for s in samples[:3])} 行为异常\n"
                f"- 请检查角色卡(character_matrix.json)确认性格设定\n"
            ),
            "dialogue_nonsense": (
                f"\n## ⚠️ 对话质量低\n"
                f"最近 {len(samples)} 章对话被标记为低质量。\n"
                f"- 对话要有信息量（推进情节/塑造人物/制造冲突）\n"
                f"- 加入动作描写穿插对话\n"
                f"- 说话风格要与角色身份匹配\n"
            ),
        }
        
        return PATCH_TEMPLATES.get(fail_type)
    
    def inject_patches(self, prompt: str, prompt_name: str) -> str:
        """将学习到的补丁注入到 Prompt 中"""
        patches = self.analyze_and_generate_patches()
        relevant = [
            patch for key, patch in patches.items()
            if key.startswith(prompt_name)
        ]
        if relevant:
            return prompt + "\n\n" + "\n---\n".join(relevant)
        return prompt
    
    def save_learned_patches(self):
        """持久化学习到的补丁"""
        output = self.analyze_and_generate_patches()
        if output:
            patch_file = self.data_dir / "prompts" / "learned_patches.json"
            patch_file.parent.mkdir(parents=True, exist_ok=True)
            patch_file.write_text(json.dumps(output, ensure_ascii=False, indent=2))
            logger.info(f"已保存 {len(output)} 条学习补丁到 {patch_file}")


# 全局单例
prompt_optimizer: Optional[PromptOptimizer] = None
```

### 3.5 Token 预算统一策略

```python
# kunlun/prompts/budget.py（新建）
"""统一 Token 预算分配器 — 对标 WenShape 6段分配，所有 Prompt 统一使用"""

from dataclasses import dataclass
from typing import Optional
from kunlun.config import settings


@dataclass
class BudgetSegment:
    """预算段"""
    name: str
    ratio: float        # 占总预算的比例
    content: str = ""   # 实际内容
    max_chars: int = 0  # 字符上限（中文 ~1.5 chars/token）


class UnifiedBudgetAllocator:
    """统一 Token 预算分配器
    
    标准 6 段分配（对标 WenShape）:
    - system_rules: 15% — 系统指令/角色定义
    - current_context: 35% — 当前章节上下文（蓝图/大纲）
    - character_cards: 12% — 角色卡信息
    - history_summaries: 13% — 历史章节摘要
    - dynamic_facts: 5%  — 动态事实（RAG检索）
    - output_reserve: 20% — 输出预留空间
    """
    
    DEFAULT_ALLOCATION = {
        "architect": {
            "system_rules":      0.15,
            "current_context":   0.35,
            "character_cards":   0.12,
            "history_summaries": 0.13,
            "dynamic_facts":     0.05,
            "output_reserve":    0.20,
        },
        "writer": {
            "system_rules":      0.10,
            "current_blueprint": 0.50,
            "character_cards":   0.10,
            "chapter_summaries": 0.10,
            "output_reserve":    0.20,
        },
        "auditor": {
            "system_rules":      0.10,
            "current_draft":     0.40,
            "reference_rules":   0.20,
            "truth_check":       0.10,
            "output_reserve":    0.20,
        },
    }
    
    def __init__(self, agent_name: str, total_tokens: int = None):
        self.agent_name = agent_name
        self.total_tokens = total_tokens or self._default_budget(agent_name)
        self.allocation = self.DEFAULT_ALLOCATION.get(agent_name, {})
    
    def _default_budget(self, agent: str) -> int:
        return getattr(settings, f"{agent}_context_budget", 8000)
    
    def get_segment_budget(self, segment: str) -> int:
        ratio = self.allocation.get(segment, 0.1)
        return int(self.total_tokens * ratio)
    
    def truncate_segment(self, content: str, segment: str) -> str:
        """按预算截断某段内容（保留头尾，压缩中间）"""
        token_budget = self.get_segment_budget(segment)
        char_limit = int(token_budget * 1.5)  # 中文 ~1.5 chars/token
        
        if len(content) <= char_limit:
            return content
        
        # 智能截断：头60% + 省略标记 + 尾25%
        head_keep = int(char_limit * 0.60)
        tail_keep = int(char_limit * 0.25)
        return (
            content[:head_keep]
            + f"\n\n[...中间 {len(content) - head_keep - tail_keep} 字已省略...]\n\n"
            + content[-tail_keep:]
        )
```

---

## 四、平台适配 Prompt 策略

### 4.1 多平台 Prompt 参数化

```python
# kunlun/prompts/platforms.py（新建）
"""平台特定规则 — 不同发布平台对应不同的 Prompt 增强"""

PLATFORM_RULES = {
    "fanqie": {  # 番茄小说
        "chapter_length": "1800-2500字",
        "style_rules": [
            "每段不超过3行（移动端阅读体验）",
            "对话占比 > 40%（番茄读者偏好对话体）",
            "前300字必须有冲突或悬念（黄金开头）",
            "结尾必须有明确的下一章预告（番茄算法推流依赖）",
        ],
        "taboo": [
            "避免大段心理描写（番茄读者偏好节奏快）",
            "避免生僻成语（AI朗读体验差）",
        ],
        "fanqie_gates": True,  # 启用番茄门禁
    },
    "qidian": {  # 起点中文网
        "chapter_length": "2500-3500字",
        "style_rules": [
            "世界观铺垫要扎实（起点读者偏好设定流）",
            "修炼/升级体系要渐进清晰",
            "允许适度的环境描写和心理活动",
        ],
        "taboo": [],
    },
    "default": {  # 通用
        "chapter_length": "2000-3000字",
        "style_rules": [],
        "taboo": [],
    },
}


def build_platform_context(platform: str = "default") -> str:
    """构建平台上下文 Prompt 片段"""
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["default"])
    ctx = f"## 平台要求 ({platform})\n"
    ctx += f"- 目标字数: {rules['chapter_length']}\n"
    ctx += "\n".join(f"- {r}" for r in rules["style_rules"])
    if rules["taboo"]:
        ctx += "\n## 平台禁忌\n"
        ctx += "\n".join(f"- {t}" for t in rules["taboo"])
    return ctx
```

### 4.2 风格指纹融入 Prompt

```python
# 将 StyleFingerprint 的结果注入 Writer/Auditor Prompt
async def inject_style_context(prompt: str, book_id: str) -> str:
    """将作品的风格指纹注入 Prompt，维持跨章文风一致"""
    from kunlun.style.fingerprint import StyleFingerprint
    
    fp = await StyleFingerprint.load(book_id)
    if not fp:
        return prompt
    
    style_context = f"""
## 作品风格指纹（请严格遵循）

- 平均句长: {fp.avg_sentence_length:.0f}字
- 对话占比: {fp.dialogue_ratio:.1%}
- 形容词密度: {fp.adjective_density:.2f}/句
- 段落节奏: {fp.paragraph_rhythm}

请保持以上风格参数 ±10% 范围内。
"""
    return prompt + style_context
```

---

## 五、分阶段实施路线

### Phase 1：统一入口（4h）
- 所有 Agent 的 `_build_prompt` 改为调用 `PromptSpec.build_context()`
- Architect/Writer/Sociologist Prompt 纳入注册表
- 平台规则参数化

### Phase 2：效果量化（6h）
- 为每个 Prompt 添加版本号
- 记录 Prompt 版本 → 审计通过率的关联数据
- 实现简单的 A/B 对比（同章两版 Prompt 效果对比）

### Phase 3：自动优化（8h）
- 实现 `PromptOptimizer` 从审计反馈自动生成补丁
- 替换手动维护的 `learned_patches.md`
- 集成到管线后处理（Audit 完成后自动分析）

### Phase 4：DSPy 深度集成（12h）
- 引入 DSPy Signature 模式
- 用优化器自动调优 Writer Prompt
- Prompt 效果用 9维 Gacha 评分做 feedback

---

## 六、速查表：Prompt 最佳实践

### 网文创作 Prompt 黄金法则

| # | 法则 | 说明 | 示例 |
|---|------|------|------|
| 1 | **角色先行** | 先定义角色（身份/性格/目标），再推进情节 | "你是一位精通爽文节奏的网文写手" |
| 2 | **场景具象** | 每个场景都要有"在哪里、谁在、发生什么" | "【XX府大厅】张三面对…" |
| 3 | **冲突驱动** | 每段对话/描写都要服务冲突 | "这段对话揭示了什么矛盾？" |
| 4 | **节奏控制** | 明确定义快慢节奏段落 | "此处为战斗段，节奏要快" |
| 5 | **爽点排布** | 提前规划每章的爽点位置 | "第3段 (约800字处) 安排打脸爽点" |
| 6 | **禁止AI套话** | 列出具体禁用的句式 | 禁用"然而/此外/总而言之" |
| 7 | **输出格式** | 明确要求输出完整章节（不要总结） | "直接输出完整正文，不要带任何说明" |
| 8 | **风格约束** | 给出具体风格参数 | "句式长短交替，段落3-5行" |
| 9 | **钩子闭环** | 每章开头收上一章钩子，结尾抛新钩子 | "开头: 回应上章悬念 / 结尾: 制造新冲突" |
| 10 | **去模板化** | 每次用 param_variator 随机化参数 | temperature/word_count/hook_type 随机微调 |

### DeepSeek 特定优化（昆仑主力模型）

| 技巧 | 说明 |
|------|------|
| `top_p=0.9` | 比默认 1.0 更有创造性，减少重复 |
| `presence_penalty=0.3` | 鼓励引入新词汇，减少重复短语 |
| `frequency_penalty=0.5` | 减少高频词重复（对 deepseek-reasoner 效果明显） |
| `stop=["\\n\\n\\n"]` | 用三空行作为停止标志 |
| 最大 tokens = 字数目标 × 2.5 | 中文每字约需 2 tokens 空间 |
