"""
昆仑创作引擎 — 社会学家 Agent

负责四大维度的社会深层推演：
  - 经济系统推演
  - 律法漏洞推演
  - 文化阶级推演
  - 习俗禁忌推演
  - 宏观→微观降维
  - 社会蝴蝶效应校验

使用方式：作为独立 Agent 被 Orchestrator 调度，接收 DEDUCE_SOCIETY 消息类型
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.prompts.society import SOCIETY_PROMPTS, get_prompt


@dataclass
class SocietyRequest:
    """社会推演请求"""

    dimension: str  # economy / law / culture / custom / macro_to_micro / social_ripple
    params: dict  # 对应 PROMPT_PARAMS 的参数
    model_preference: str = "auto"  # 首选模型


@dataclass
class SocietyResult:
    """社会推演结果"""

    dimension: str
    prompt_used: str
    model_used: str
    output: str
    tokens_used: int = 0


class SociologistAgent(BaseAgent):
    """
    社会学家 Agent

    按维度调度对应的推演 Prompt，通过 GachaEngine 调用 LLM 完成推演。
    支持四维度独立推演和组合推演。

    设计哲学：
    - 不与 Writer/Architect 争抢正文生成职责
    - 只做"设定骨架"推演，产出结构化分析
    - 推演结果可作为 Architect 的输入

    成本优化 (2026-06):
    - 按章节类型分组触发（战斗/感情/过渡章只用核心维）
    - 推演结果缓存（相同book_id+params的维度复用）
    - Mini模式：仅推演8个核心维度而非44个
    """

    agent_name = "sociologist"

    # ── 维度分组（按章节类型） ──────────────────────────
    # 核心维：所有章节类型都需要的根基维度
    CORE_DIMENSIONS = [
        "economy",
        "law",
        "culture",
        "custom",
        "power_system",
        "technology",
        "philosophy",
        "ecology",
    ]
    # 战斗增强：战斗/高潮章节额外触发的维度
    BATTLE_DIMENSIONS = [
        "military",
        "underworld",
        "admin",
        "clan",
        "resource_network",
        "spatial_ecology",
    ]
    # 叙事增强：关键剧情/情感章额外触发的维度
    NARRATIVE_DIMENSIONS = [
        "pleasure_engineering",
        "hook_management",
        "villain_arc",
        "reader_biochem",
        "moral_dilemma",
        "class_barrier",
        "info_blackbox",
    ]
    # 世界增强：新开篇/重要转折章额外触发的维度
    WORLD_DIMENSIONS = [
        "history",
        "propaganda",
        "astronomy",
        "mobility",
        "language",
        "forensic",
        "cult",
        "royal_monopoly",
        "espionage",
        "diplomacy",
        "medical",
        "entourage",
        "population_control",
        "inner_court",
        "serial_crisis",
        "genre_innovation",
        "compliance_audit",
        "platform_optimization",
        "reader_collab",
        "ip_derivative",
        "author_sop",
        "ecology",
        "underworld",
        "philosophy",
    ]

    # ── 缓存配置 ──────────────────────────────────────
    _deduction_cache: dict[str, dict] = {}  # cache_key → {result, timestamp}
    MAX_CACHE_AGE = 3600  # 缓存有效期1小时

    def __init__(self):
        super().__init__()
        self._results: list[SocietyResult] = []

    async def execute(self, task: dict) -> dict:
        """
        主要入口。task 格式:
        {
            "dimension": "economy",  # 或 deduce_all / macro_to_micro / social_ripple
            "params": {...}
        }
        """
        action = task.get("dimension", "")
        params = task.get("params", {})

        if action == "deduce_all":
            results = await self.deduce_all(params)
            return {
                "success": True,
                "results": {dim: r.output for dim, r in results.items()},
            }
        if action in ("macro_to_micro", "social_ripple") or action in SOCIETY_PROMPTS:
            request = SocietyRequest(dimension=action, params=params)
            result = await self.deduce(request)
            return {"success": True, "output": result.output}
        return {"success": False, "error": f"未知维度: {action}"}

    async def deduce(self, request: SocietyRequest) -> SocietyResult:
        """
        执行单维度社会推演。

        Args:
            request: SocietyRequest 包含维度和参数

        Returns:
            SocietyResult: 推演结果
        """
        dimension = request.dimension
        params = request.params

        logger.info(f"[Sociologist] 开始推演维度: {dimension}")

        # 构建 Prompt
        try:
            prompt = get_prompt(dimension, **params)
        except ValueError as e:
            logger.error(f"[Sociologist] Prompt 构建失败: {e}")
            return SocietyResult(
                dimension=dimension,
                prompt_used="",
                model_used="",
                output=f"错误: {e}",
            )

        # 选择合适的模型
        model = self._select_model(dimension, request.model_preference)

        # 调用 LLM
        try:
            from kunlun.gacha.engine import gacha_engine

            # 注入用户自定义提示词
            try:
                from kunlun.prompt_manager import prompt_manager

                final_prompt = prompt_manager.inject_into_prompt(prompt, "sociologist", "default")
            except Exception:
                final_prompt = prompt
            response = await gacha_engine.chat(
                messages=[{"role": "user", "content": final_prompt}],
                model=model,
                temperature=0.7,
                max_tokens=4096,
            )
            output = response.get("content", "")
            tokens = response.get("usage", {}).get("total_tokens", 0)
        except Exception as e:
            logger.error(f"[Sociologist] LLM 调用失败: {e}")
            return SocietyResult(
                dimension=dimension,
                prompt_used=prompt,
                model_used=model,
                output=f"LLM 调用失败: {e}",
            )

        result = SocietyResult(
            dimension=dimension,
            prompt_used=prompt,
            model_used=model,
            output=output,
            tokens_used=tokens,
        )

        self._results.append(result)
        logger.info(f"[Sociologist] 推演完成: {dimension}, tokens={tokens}")
        return result

    # ─── 成本优化：缓存 + 懒加载 ──────────────────────

    @staticmethod
    def _cache_key(dimension: str, params: dict, book_id: str = "") -> str:
        """为推演维度+参数+书籍ID生成缓存key（防止跨书污染）"""
        serialized = json.dumps(params, sort_keys=True, ensure_ascii=False)
        raw = f"{book_id}:{dimension}:{serialized}"
        return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()

    def _get_cached(self, dimension: str, params: dict, book_id: str = "") -> str | None:
        """获取缓存的推演结果"""
        key = self._cache_key(dimension, params, book_id)
        entry = self._deduction_cache.get(key)
        if entry and (time.time() - entry["timestamp"]) < self.MAX_CACHE_AGE:
            logger.debug(f"[Sociologist] 缓存命中: {dimension}")
            return entry["result"]
        return None

    def _set_cache(self, dimension: str, params: dict, result: str, book_id: str = ""):
        """缓存推演结果"""
        key = self._cache_key(dimension, params, book_id)
        self._deduction_cache[key] = {"result": result, "timestamp": time.time()}
        # 缓存上限500条，超限时清理最旧的
        if len(self._deduction_cache) > 500:
            oldest = min(
                self._deduction_cache.keys(), key=lambda k: self._deduction_cache[k]["timestamp"]
            )
            self._deduction_cache.pop(oldest, None)

    def _get_dimensions_for_chapter_type(
        self, chapter_type: str, is_first_chapter: bool = False, is_critical: bool = False
    ) -> list[str]:
        """
        根据章节类型返回需要推演的维度列表。

        成本对比:
        - FULL (44维): ~40-50次LLM调用
        - BATTLE (26维): ~20次LLM调用 (节省50%)
        - NARRATIVE (21维): ~15次LLM调用 (节省60%)
        - MINI (8维): ~8次LLM调用 (节省80%)
        - FIRST_CHAPTER (36维): ~30次LLM调用

        Args:
            chapter_type: normal/battle/climax/intro
            is_first_chapter: 是否第一章（需要更全面的世界构建）
            is_critical: 是否关键剧情章节

        Returns:
            需要推演的维度列表
        """
        if is_first_chapter:
            return list(
                set(
                    self.CORE_DIMENSIONS
                    + self.WORLD_DIMENSIONS
                    + self.NARRATIVE_DIMENSIONS
                    + self.BATTLE_DIMENSIONS
                )
            )

        if chapter_type == "battle":
            return list(
                set(
                    self.CORE_DIMENSIONS
                    + self.BATTLE_DIMENSIONS
                    + (self.NARRATIVE_DIMENSIONS if is_critical else [])
                )
            )

        if chapter_type == "climax":
            return list(
                set(self.CORE_DIMENSIONS + self.NARRATIVE_DIMENSIONS + self.BATTLE_DIMENSIONS)
            )

        if chapter_type == "intro":
            return list(set(self.CORE_DIMENSIONS + self.WORLD_DIMENSIONS[:10]))

        # normal / 默认：仅核心维度（最低成本）
        return list(self.CORE_DIMENSIONS)

    async def deduce_all_lazy(
        self,
        baseline_params: dict,
        chapter_type: str = "normal",
        is_first_chapter: bool = False,
        is_critical: bool = False,
        use_cache: bool = True,
    ) -> dict[str, SocietyResult]:
        """
        优化的批量推演：按章节类型分级触发 + 缓存复用。

        Args:
            baseline_params: 各维度所需参数
            chapter_type: 章节类型
            is_first_chapter: 是否第一章
            is_critical: 是否关键章节
            use_cache: 是否启用缓存

        Returns:
            {dimension: SocietyResult}
        """
        dimensions = self._get_dimensions_for_chapter_type(
            chapter_type, is_first_chapter, is_critical
        )
        logger.info(
            f"[Sociologist] 懒加载推演: chapter_type={chapter_type}, "
            f"维度数={len(dimensions)} (FULL=44), 并行度=3"
        )

        results = {}
        param_mapping = self._get_param_mapping()
        book_id = baseline_params.get("book_id", "")
        _semaphore = asyncio.Semaphore(3)  # 限制并发=3，防止API限流

        # 先检查缓存命中的维度
        uncached_dims = []
        for dim in dimensions:
            if dim not in param_mapping:
                continue
            needed_params = {k: baseline_params.get(k, "") for k in param_mapping[dim]}
            if use_cache:
                cached = self._get_cached(dim, needed_params, book_id)
                if cached is not None:
                    results[dim] = SocietyResult(
                        dimension=dim,
                        prompt_used="",
                        model_used="",
                        output=cached,
                        tokens_used=0,
                    )
                    continue
            uncached_dims.append((dim, needed_params))

        # 并行推演：使用 Semaphore 限制并发，避免 API 限流
        async def _deduce_dim(dim: str, needed_params: dict) -> tuple[str, SocietyResult]:
            async with _semaphore:
                request = SocietyRequest(dimension=dim, params=needed_params)
                result = await self.deduce(request)
                if use_cache and result.output and "错误" not in result.output:
                    self._set_cache(dim, needed_params, result.output, book_id)
                return dim, result

        if uncached_dims:
            parallel_tasks = [_deduce_dim(dim, params) for dim, params in uncached_dims]
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            for item in parallel_results:
                if isinstance(item, Exception):
                    logger.error(f"[Sociologist] 并行推演异常: {item}")
                    continue
                dim, result = item
                results[dim] = result

        saved = len(dimensions) - len(uncached_dims)
        if saved > 0:
            logger.info(
                f"[Sociologist] 缓存复用 {saved}/{len(dimensions)} 个维度, "
                f"并行执行 {len(uncached_dims)} 个维度"
            )
        return results

    def _get_param_mapping(self) -> dict:
        """返回维度→参数映射表"""
        return {
            "economy": ["economy_baseline"],
            "law": ["law_baseline"],
            "culture": ["culture_baseline"],
            "custom": ["custom_baseline"],
            "history": ["history_baseline"],
            "power_system": ["power_baseline"],
            "technology": ["tech_baseline"],
            "ecology": ["ecology_baseline"],
            "underworld": ["underworld_baseline"],
            "philosophy": ["philosophy_baseline"],
            "admin": ["admin_baseline"],
            "clan": ["clan_baseline"],
            "propaganda": ["propaganda_baseline"],
            "astronomy": ["astronomy_baseline"],
            "mobility": ["mobility_baseline"],
            "language": ["language_baseline"],
            "military": ["military_baseline"],
            "entourage": ["entourage_baseline"],
            "population_control": ["population_baseline"],
            "inner_court": ["inner_court_baseline"],
            "medical": ["medical_baseline"],
            "forensic": ["forensic_baseline"],
            "cult": ["cult_baseline"],
            "royal_monopoly": ["royal_monopoly_baseline"],
            "espionage": ["espionage_baseline"],
            "diplomacy": ["diplomacy_baseline"],
            "underbelly": ["underbelly_baseline"],
            "pleasure_engineering": ["pleasure_baseline"],
            "hook_management": ["hook_baseline"],
            "villain_arc": ["villain_baseline"],
            "anti_ai_style": ["author_draft", "ai_logic"],
            "resource_network": ["genre_type", "core_resource", "controller", "bottom_access"],
            "class_barrier": ["genre_type", "start_class", "target_class", "surface_channel"],
            "info_blackbox": ["genre_type", "hidden_truth", "control_medium", "info_access"],
            "spatial_ecology": ["genre_type", "core_location", "spatial_layers", "choke_points"],
            "moral_dilemma": [
                "genre_type",
                "bond_characters",
                "final_battle_context",
                "villain_profile",
            ],
            "serial_crisis": ["serial_crisis_baseline"],
            "reader_biochem": ["reader_biochem_baseline"],
            "genre_innovation": ["genre_innovation_baseline"],
            "compliance_audit": ["compliance_audit_baseline"],
            "platform_optimization": ["platform_optimization_baseline"],
            "reader_collab": ["reader_collab_baseline"],
            "ip_derivative": ["ip_derivative_baseline"],
            "author_sop": ["author_sop_baseline"],
        }

    async def deduce_all(
        self,
        baseline_params: dict,
        dimensions: list[str] | None = None,
        max_concurrency: int = 5,
    ) -> dict[str, SocietyResult]:
        """
        批量并行推演多个维度。

        Args:
            baseline_params: 包含各维度所需参数的字典
            dimensions: 要推演的维度列表，默认全部44个
            max_concurrency: 最大并发数（防止 API rate limit）

        Returns:
            {dimension: SocietyResult}
        """
        if dimensions is None:
            dimensions = list(self._get_param_mapping().keys())

        param_mapping = self._get_param_mapping()

        # 使用 Semaphore 控制并发
        sem = asyncio.Semaphore(max_concurrency)

        async def _deduce_one(dim: str) -> tuple[str, SocietyResult] | None:
            if dim not in param_mapping:
                return None
            async with sem:
                needed_params = {k: baseline_params.get(k, "") for k in param_mapping[dim]}
                request = SocietyRequest(dimension=dim, params=needed_params)
                try:
                    result = await self.deduce(request)
                    return (dim, result)
                except Exception as e:
                    logger.warning(f"[Sociologist] 维度 {dim} 推演失败: {e}")
                    return (
                        dim,
                        SocietyResult(
                            dimension=dim,
                            output="",
                            model_used="",
                            confidence=0.0,
                            tokens_used=0,
                            error=str(e),
                        ),
                    )

        tasks = [asyncio.create_task(_deduce_one(dim)) for dim in dimensions]
        gathered = await asyncio.gather(*tasks)

        results = {}
        for item in gathered:
            if item is not None:
                dim, result = item
                results[dim] = result

        logger.info(
            f"[Sociologist] 并行推演完成: {len(results)}/{len(dimensions)} 维度 "
            f"(并发={max_concurrency})"
        )
        return results

    async def macro_to_micro(self, macro_setting: str) -> SocietyResult:
        """宏观设定降维：将宏大设定转化为具体切入点"""
        request = SocietyRequest(
            dimension="macro_to_micro",
            params={"macro_setting": macro_setting},
        )
        return await self.deduce(request)

    async def social_ripple_check(
        self, world_parameters: str, proposed_change: str, chapter_context: str = "当前"
    ) -> SocietyResult:
        """社会蝴蝶效应校验"""
        request = SocietyRequest(
            dimension="social_ripple",
            params={
                "world_parameters": world_parameters,
                "proposed_change": proposed_change,
                "chapter_context": chapter_context,
            },
            model_preference="deepseek",  # 逻辑推演偏好 DeepSeek
        )
        return await self.deduce(request)

    def _select_model(self, dimension: str, preference: str = "auto") -> str:
        """根据推演维度选择合适的模型"""
        if preference != "auto":
            return preference

        # 不同维度适合不同模型
        model_map = {
            "economy": "deepseek-reasoner",  # 逻辑推演
            "law": "deepseek-reasoner",  # 律法推演
            "culture": "deepseek-chat",  # 长文本文化分析
            "custom": "deepseek-chat",  # 创意习俗设计
            "macro_to_micro": "deepseek-chat",  # 创意写作
            "social_ripple": "deepseek-reasoner",  # 逻辑推演
            # 第二阶段扩展
            "history": "deepseek-reasoner",  # 历史逻辑推演
            "power_system": "deepseek-reasoner",  # 战力体系推演
            "technology": "deepseek-reasoner",  # 科技供应链推演
            "ecology": "deepseek-chat",  # 地理生态创意
            "underworld": "deepseek-chat",  # 灰域创意设计
            "philosophy": "deepseek-chat",  # 哲学理念设计
            "iceberg": "deepseek-chat",  # 创意写作转化
            # 第三阶段扩展：6个隐秘维度
            "admin": "deepseek-reasoner",  # 行政后勤逻辑推演
            "clan": "deepseek-chat",  # 宗族社会分析
            "propaganda": "deepseek-chat",  # 舆论情报创意
            "astronomy": "deepseek-reasoner",  # 天象政治推演
            "mobility": "deepseek-chat",  # 阶层流动叙事
            "language": "deepseek-reasoner",  # 文字狱逻辑推演
            # 第四阶段扩展：微观与中观生态
            "military": "deepseek-reasoner",  # 军制逻辑推演
            "entourage": "deepseek-chat",  # 幕僚官场生态
            "population_control": "deepseek-reasoner",  # 户籍制度推演
            "inner_court": "deepseek-chat",  # 内宅后宫叙事
            "medical": "deepseek-reasoner",  # 药理防疫推演
            # 第五阶段扩展：6个边缘深度维度
            "forensic": "deepseek-chat",  # 古代司法/仵作验尸
            "cult": "deepseek-reasoner",  # 秘密宗教/帮会推演
            "royal_monopoly": "deepseek-chat",  # 皇权私产/采办贪腐
            "espionage": "deepseek-chat",  # 古代谍战/死间心理
            "diplomacy": "deepseek-reasoner",  # 外交/互市地缘推演
            "underbelly": "deepseek-chat",  # 城市贱业/底层暗战
            # 第六阶段扩展：叙事工程与商业逻辑
            "pleasure_engineering": "deepseek-reasoner",  # 爽点结构逻辑推演
            "hook_management": "deepseek-chat",  # 悬念叙事创意
            "villain_arc": "deepseek-chat",  # 角色塑造与文学性
            "anti_ai_style": "deepseek-chat",  # 文风转化与创意写作
            # 第八阶段扩展：跨题材通用底层维度
            "resource_network": "deepseek-reasoner",  # 资源垄断逻辑推演
            "class_barrier": "deepseek-chat",  # 阶层流动叙事分析
            "info_blackbox": "deepseek-reasoner",  # 信息操控逻辑推演
            "spatial_ecology": "deepseek-chat",  # 空间压迫创意设计
            "moral_dilemma": "deepseek-chat",  # 情感抉择与文学性
            # 第九阶段扩展：连载生存、读者心理与题材创新
            "serial_crisis": "deepseek-reasoner",  # 连载危机逻辑推演
            "reader_biochem": "deepseek-chat",  # 读者心理叙事分析
            "genre_innovation": "deepseek-chat",  # 题材创新与创意写作
            # 第七阶段扩展：现实运营与生态变现
            "compliance_audit": "deepseek-reasoner",  # 合规审计逻辑推演
            "platform_optimization": "deepseek-chat",  # 平台优化策略分析
            "reader_collab": "deepseek-chat",  # 读者共创叙事设计
            "ip_derivative": "deepseek-chat",  # IP衍生创意写作
            "author_sop": "deepseek-reasoner",  # 创作者SOP流程推演
        }
        return model_map.get(dimension, "deepseek-chat")

    async def iceberg_convert(self, macro_setting: str) -> SocietyResult:
        """冰山写作技法：将宏观设定转化为可直接嵌入正文的小说片段"""
        request = SocietyRequest(
            dimension="iceberg",
            params={"macro_setting": macro_setting},
        )
        return await self.deduce(request)

    async def anti_ai_style(self, author_draft: str, ai_logic: str) -> SocietyResult:
        """去AI味：将AI逻辑骨架融入作者文风草稿"""
        request = SocietyRequest(
            dimension="anti_ai_style",
            params={"author_draft": author_draft, "ai_logic": ai_logic},
        )
        return await self.deduce(request)

    # ─── 开书级全量推演（只跑一次，结果存入RAG知识库）───

    async def full_deduce_for_book(
        self,
        book_id: str,
        baseline_params: dict,
        max_concurrency: int = 5,
    ) -> dict:
        """
        开书时执行全量社会推演（并行），结果存入知识图谱 + 向量库。

        后续章节生成时通过 RAG 查询按需召回，不再重复调用 LLM。

        Args:
            book_id: 书籍ID
            baseline_params: 所有维度的 baseline 参数
            max_concurrency: 最大并发数

        Returns:
            {"dimension": output, ...} + 自动索引到 Qdrant + FTS5
        """
        from kunlun.kg.client import kg_client

        all_dims = list(self._get_param_mapping().keys())
        logger.info(f"[Sociologist] 开书全量推演: {book_id}, {len(all_dims)}个维度")

        param_mapping = self._get_param_mapping()
        sem = asyncio.Semaphore(max_concurrency)

        async def _deduce_and_index(dim: str) -> tuple[str, str] | None:
            needed_params = {k: baseline_params.get(k, "") for k in param_mapping.get(dim, [])}
            request = SocietyRequest(dimension=dim, params=needed_params)
            try:
                async with sem:
                    result = await self.deduce(request)

                # 索引到 KG + 向量库
                uid = f"{book_id}_society_{dim}"
                text = f"[{dim}] {result.output[:500]}"
                try:
                    kg_client.index_entity(uid, dim, "society_insight", text)
                    kg_client.index_entity_vector(
                        uid,
                        text,
                        {"book_id": book_id, "dimension": dim, "model": result.model_used},
                    )
                except Exception as e:
                    logger.warning(f"[Sociologist] 索引失败 {dim}: {e}")

                return (dim, result.output)
            except Exception as e:
                logger.warning(f"[Sociologist] 维度 {dim} 推演失败: {e}")
                return (dim, "")

        tasks = [asyncio.create_task(_deduce_and_index(dim)) for dim in all_dims]
        gathered = await asyncio.gather(*tasks)

        results = {}
        for item in gathered:
            if item is not None:
                dim, output = item
                results[dim] = output

        logger.info(
            f"[Sociologist] 开书推演完成: {book_id}, {len(results)}/{len(all_dims)}维已存入知识库 "
            f"(并发={max_concurrency})"
        )
        return results

    async def query_society_rag(self, book_id: str, query: str, top_k: int = 5) -> str:
        """
        RAG 查询：根据当前章节的上下文，从向量库召回相关的社会推演结果。

        替代原每章44维LLM调用。只做一次语义检索 + 拼接上下文。

        Args:
            book_id: 书籍ID
            query: 查询文本（如"主角在京城战斗，需要法律和经济背景"）
            top_k: 召回条数

        Returns:
            拼接后的相关推演上下文字符串
        """
        from kunlun.kg.client import kg_client

        try:
            results = kg_client.vector_search(f"society_insight {book_id} {query}", limit=top_k)
            if not results:
                return "（未检索到相关社会推演数据）"
            parts = []
            for r in results:
                dim = (r.get("payload") or {}).get("dimension", "unknown")
                text = (r.get("payload") or {}).get("text", "")
                if text:
                    parts.append(f"[{dim}]: {text[:300]}")
            return "\n\n".join(parts) if parts else "（未检索到相关社会推演数据）"
        except Exception as e:
            logger.warning(f"[Sociologist] RAG 查询失败: {e}")
            return "（社会推演RAG查询暂不可用）"

    # ─── 压力测试 ─────────────────────────────────

    async def stress_test_butterfly(self, kill_scenario: dict) -> dict[str, SocietyResult]:
        """
        蝴蝶效应测试：主角在京城杀了一个贪官，推演连锁反应。

        kill_scenario: {"official_name": "...", "position": "...", "crime": "..."}
        推演维度：clan / admin / underworld
        """
        name = kill_scenario.get("official_name", "某贪官")
        position = kill_scenario.get("position", "")
        crime = kill_scenario.get("crime", "")

        # 将 position/crime 注入 deduce_all 上下文以提升推演质量
        position_info = f"生前担任{position}。" if position else ""
        crime_info = f"罪名：{crime}。" if crime else ""

        return await self.deduce_all(
            {
                "clan_baseline": (
                    f"{name}的宗族背景：南方大族，族人2000+，族田3000亩，"
                    f"三代出过两个进士。"
                ),
                "admin_baseline": (
                    f"{name}生前负责督运江南漕粮进京，手下有漕帮人脉。{position_info}{crime_info}"
                ),
                "underworld_baseline": (
                    f"{name}生前暗中保护了一条从沿海到内地的私盐通道。"
                    f"{crime_info}"
                ),
            },
            dimensions=["clan", "admin", "underworld"],
        )

    async def stress_test_survival(self, disaster_scenario: dict) -> dict[str, SocietyResult]:
        """
        底层生存测试：大旱之下底层农民命运推演。

        disaster_scenario: {"disaster": "...", "region": "..."}
        推演维度：economy / clan / mobility
        """
        disaster = disaster_scenario.get("disaster", "大旱")
        region = disaster_scenario.get("region", "北方某县")
        scenario = f"{region}发生{disaster}，一个普通自耕农家庭（5口人，10亩薄田）的生存抉择。"

        return await self.deduce_all(
            {
                "economy_baseline": (
                    f"{scenario} 灾前粮价：米每石1两，"
                    f"灾后飙升至3两。借贷利率：月息3分。"
                ),
                "clan_baseline": "该县有王姓大族，掌握义仓和族田，但救济只给本族中人。",
                "mobility_baseline": (
                    "底层上升通道：科举（几乎不可能）、投军（九死一生）、"
                    "入赘（失姓）、落草（造反）。"
                ),
            },
            dimensions=["economy", "clan", "mobility"],
        )

    async def stress_test_villain(self, protagonist_info: dict) -> dict[str, SocietyResult]:
        """
        反派智商测试：验证反派是否能用制度组合拳对付主角，而非低级暗杀。

        protagonist_info: {"name": "...", "position": "...", "weakness": "..."}
        推演维度：admin / propaganda / astronomy / language
        """
        name = protagonist_info.get("name", "主角")
        position = protagonist_info.get("position", "知府")
        weakness = protagonist_info.get("weakness", "廉洁但急躁")

        scenario = f"反派欲扳倒{position}{name}（弱点：{weakness}），不使用暗杀，只用制度规则。"
        return await self.deduce_all(
            {
                "admin_baseline": f"{scenario} 可卡脖子的流程：粮草调拨、官员考核、驿站通行。",
                "propaganda_baseline": f"需要抹黑{name}的舆论武器：童谣、揭帖、戏曲影射。",
                "astronomy_baseline": "最近天象：彗星过境，钦天监可政治化解读。",
                "language_baseline": (
                    f"文字狱切入方向：{name}曾出版诗集一部，"
                    f"师从某位有争议的大儒。"
                ),
            },
            dimensions=["admin", "propaganda", "astronomy", "language"],
        )

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        """处理 Agent 消息"""
        if msg.msg_type == "DEDUCE_SOCIETY":
            payload = msg.payload
            request = SocietyRequest(**payload)
            result = await self.deduce(request)
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="SOCIETY_RESULT",
                payload={
                    "dimension": result.dimension,
                    "output": result.output,
                    "model_used": result.model_used,
                    "tokens_used": result.tokens_used,
                },
                correlation_id=msg.correlation_id,
                kg_snapshot_id=msg.kg_snapshot_id,
            )
        return None

    def get_last_result(self, dimension: str | None = None) -> SocietyResult | None:
        """获取最近一次推演结果"""
        if dimension:
            for r in reversed(self._results):
                if r.dimension == dimension:
                    return r
            return None
        return self._results[-1] if self._results else None

    def get_all_results_summary(self) -> list[dict]:
        """获取所有推演结果的摘要"""
        return [
            {
                "dimension": r.dimension,
                "model": r.model_used,
                "tokens": r.tokens_used,
                "output_preview": r.output[:200] + "..." if len(r.output) > 200 else r.output,
            }
            for r in self._results
        ]


# 全局单例
sociologist = SociologistAgent()
