"""
昆仑创作引擎 — 多模型抽卡引擎（Gacha Engine）

核心作用: 多模型并行调用 + 质量评分 + 最优文本选择。

4 种模式:
  - single_fix: 单模型修复/生成（用于审计修复、配置推断等）
  - gacha_cascade: 多模型并行抽卡 → 10维评分 → 选最优
  - gacha_vibe: Vibe Writing 模式（高创意）
  - single_chat: 对话模式（用于 /chat 端点）

10 维评分体系 (纯文本统计，零 LLM 成本):
  1. 多样性  2. 连贯性  3. 信息密度  4. 情感波动
  5. 节奏感  6. 创新度  7. 流畅度  8. 完整性  9. 人味度  10. 风格匹配度

灵感来源:
  - NovelForger: 多模型并行 + 投票
  - OpenRouter: 多供应商路由
  - ChatHub: 多模型对比
  - 自研评分体系: 零成本、可解释、网文特化

用法:
    from kunlun.gacha.engine import gacha_engine

    result = await gacha_engine.generate(prompt, mode="gacha_cascade")
    best_text = result["best_text"]
"""

from __future__ import annotations

import asyncio
import itertools
import json
import math
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import httpx
from loguru import logger

from kunlun.config import settings
from kunlun.gacha.circuit_breaker import (
    CircuitBreaker,
    KeyRotator,
)
from kunlun.gacha.param_variator import ParamVariator

# ── 模型候选 ─────────────────────────────────────────


@dataclass
class ModelCandidate:
    """模型候选配置"""

    provider: str
    model: str
    base_url: str
    api_key: str
    priority: int = 0  # 优先级（越低越优先）
    cost_per_1k: float = 0.0  # 每千token成本


# ── 默认模型列表 ──────────────────────────────────────

DEFAULT_MODELS: list[dict] = [
    {
        "provider": "openai_compat",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    {
        "provider": "openai_compat",
        "model": "gpt-4o-mini",
        "base_url": "",
        "api_key_env": "OPENAI_API_KEY",
    },
    {
        "provider": "local",
        "model": "novel_style_qwen05b",
        "base_url": "",
        "api_key_env": "",
    },
    {
        "provider": "local",
        "model": "novel_style_qwen7b",
        "base_url": "",
        "api_key_env": "",
    },
]


# ── 章节类型级联阈值 ─────────────────────────────────

CASCADE_THRESHOLDS: dict[str, dict] = {
    "climax": {"min_candidates": 3, "min_score": 0.70, "temperature_boost": 0.10},
    "transition": {"min_candidates": 2, "min_score": 0.55, "temperature_boost": 0.0},
    "normal": {"min_candidates": 2, "min_score": 0.60, "temperature_boost": 0.0},
    "opening": {"min_candidates": 3, "min_score": 0.75, "temperature_boost": 0.05},
    "ending": {"min_candidates": 3, "min_score": 0.72, "temperature_boost": 0.05},
}


# ── 十维评分常量 ──────────────────────────────────────

# 文本多样性
_MIN_DIVERSE_WORD_LENGTH = 5  # 最低有效词长度
_DIVERSE_UNIQUE_RATIO_MULTIPLIER = 3.0  # 独特词比率乘数
_DIVERSE_SCORE_CAP = 1.0  # 多样性分数上限
_DIVERSE_MIN_SENTENCE_CHARS = 5  # 最低句子字符数
_DIVERSE_MIN_SENTENCES = 2  # 最低句子数
_DIVERSE_DEFAULT_SCORE = 0.5  # 默认多样性分数

# 段落结构
_PARAGRAPH_STRUCT_MIN_CHARS = 5  # 有效句子最低字符数
_PARAGRAPH_STRUCT_PENALTY_BASE = 0.2  # 段落计数惩罚基数

# 对话密度
_DIALOGUE_DENSITY_OPTIMAL_RATIO = 0.9  # 最优对话密度比率
_DIALOGUE_DENSITY_LONG_PARAGRAPH = 20  # 长段落阈值（字符）
_DIALOGUE_DENSITY_MAX_EMBEDDED = 3  # 最大嵌入式对话行数

# 连贯性
_COHERENCE_MIN_SENTENCE_CHARS = 5  # 有效句子最低字符数
_COHERENCE_MIN_SENTENCES = 2  # 最低句子数
_COHERENCE_DEFAULT_SCORE = 0.5  # 默认连贯性分数

# 节奏感
_RHYTHM_MIN_SENTENCE_CHARS = 2  # 有效句子最低字符数
_RHYTHM_MIN_SENTENCES = 3  # 最低句子数
_RHYTHM_DEFAULT_SCORE = 0.5  # 默认节奏感分数
_RHYTHM_TARGET_CV = 0.5  # 目标变异系数

# 完整性
_COMPLETENESS_DEFAULT_SCORE = 0.5  # 默认完整性分数
_COMPLETENESS_MIN_CHARS = 200  # 最低字符数阈值
_COMPLETENESS_LENGTH_BONUS = 0.2  # 长度加分
_COMPLETENESS_ENDING_BONUS = 0.15  # 结尾加分
_COMPLETENESS_DIALOG_BONUS = 0.1  # 对话加分

# 创新性
_NOVELTY_DEFAULT_SCORE = 0.5  # 默认创新性分数
_NOVELTY_BIGRAM_MIN = 2  # 最小bigram数

# 通用阈值
_MIN_TEXT_LENGTH = 100  # 最小文本长度（低于此值跳过评分）
_HTTP_SERVER_ERROR_MIN = 500  # HTTP服务端错误下限
_HTTP_SERVER_ERROR_MAX = 600  # HTTP服务端错误上限（不含）
_HTTP_RATE_LIMIT_STATUS = 429  # HTTP 429 请求过多


# ── GachaEngine ───────────────────────────────────────


class GachaEngine:
    """多模型抽卡引擎 — 全局单例"""

    # 空结果常量 — 避免重复构造相同字典
    EMPTY_RESULT: dict = {
        "best_text": "",
        "best_model": "",
        "best_score": 0.0,
        "scores": {},
        "candidates": [],
        "usage": {},
    }

    def __init__(self):
        self._models: list[ModelCandidate] = []
        self._last_best_model: str = ""
        self._call_history: list[dict] = []
        self._param_variators: dict[str, ParamVariator] = {}
        # 熔断器 — 每个 base_url 一个实例
        self._breakers: dict[str, CircuitBreaker] = {}
        # API Key 轮换器
        self._key_rotator: KeyRotator | None = None
        # 共享 httpx 客户端 — 连接池复用，避免每次调用重建 TCP+TLS
        self._http_client: httpx.AsyncClient | None = None
        # 目标风格指纹 — 用于第10维风格匹配评分（延迟导入类型避免循环依赖）
        self.target_style_fingerprint = None
        self._init_models()
        self._init_key_rotator()

    def _get_http_client(self):
        """获取共享的 httpx AsyncClient（惰性初始化，支持连接池复用）"""
        if self._http_client is None:
            import httpx

            self._http_client = httpx.AsyncClient(
                timeout=120.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
        return self._http_client

    async def close(self) -> None:
        """关闭共享 httpx 客户端（应用关闭时调用）"""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    # ── 单例 ─────────────────────────────────────────

    _instance: GachaEngine | None = None

    @classmethod
    def get_instance(cls) -> GachaEngine:
        """获取全局单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── 模型管理 ──────────────────────────────────────

    def _init_models(self) -> None:
        """初始化模型候选列表"""
        for cfg in DEFAULT_MODELS:
            provider = cfg.get("provider", "openai_compat")
            # 本地模型不需要 api_key，直接添加
            if provider == "local":
                self._models.append(
                    ModelCandidate(
                        provider=provider,
                        model=cfg["model"],
                        base_url=cfg.get("base_url", ""),
                        api_key="",
                    )
                )
                continue
            attr_name = cfg["api_key_env"].lower()
            api_key = getattr(settings, attr_name, "") or ""
            if api_key:
                base_url = cfg.get("base_url", "") or getattr(settings, "openai_base_url", "")
                self._models.append(
                    ModelCandidate(
                        provider=provider,
                        model=cfg["model"],
                        base_url=base_url,
                        api_key=api_key,
                    )
                )
        if not self._models:
            logger.warning("GachaEngine: 没有配置任何 LLM API Key，将使用模拟模式")

    def _init_key_rotator(self) -> None:
        """初始化 API Key 轮换器（从 .env OPENAI_API_KEYS_BACKUP 加载）"""
        backup_keys_str = getattr(settings, "openai_api_keys_backup", "") or ""
        backup_keys = [k.strip() for k in backup_keys_str.split(",") if k.strip()]
        if backup_keys:
            self._key_rotator = KeyRotator(backup_keys, cooldown_seconds=60)
            logger.info(f"GachaEngine: 备用 Key 轮换器已就绪 ({len(backup_keys)} 个)")

    def _get_breaker(self, base_url: str) -> CircuitBreaker:
        """获取或创建指定 URL 的熔断器"""
        if base_url not in self._breakers:
            self._breakers[base_url] = CircuitBreaker(
                failure_threshold=0.5,
                window_size_seconds=60,
                recovery_timeout=30,
                min_calls_before_break=3,
                name=base_url.rsplit("/", 1)[-1] if "/" in base_url else base_url,
            )
        return self._breakers[base_url]

    @property
    def last_best_model(self) -> str:
        """最近一次选中的最优模型"""
        return self._last_best_model

    @last_best_model.setter
    def last_best_model(self, value: str) -> None:
        self._last_best_model = value

    # ── 级联阈值 ──────────────────────────────────────

    def get_cascade_threshold(self, chapter_type: str = "normal") -> dict:
        """获取指定章节类型的级联阈值"""
        return CASCADE_THRESHOLDS.get(chapter_type, CASCADE_THRESHOLDS["normal"])

    def set_target_style(self, fp) -> None:
        """设置目标风格指纹，用于第10维风格匹配评分

        Args:
            fp: StyleFingerprint 对象或 None（清除目标）
        """
        self.target_style_fingerprint = fp
        if fp is not None:
            logger.info(f"GachaEngine: 目标风格指纹已设置: {fp.name}")
        else:
            logger.info("GachaEngine: 目标风格指纹已清除")

    # ── 核心方法 ──────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        agent: str = "",
    ) -> dict:
        """对话模式 — 单模型调用，用于 /chat 端点。

        Args:
            messages: OpenAI 格式消息列表
            model: 指定模型（空则用默认）
            temperature: 温度
            max_tokens: 最大 token 数
            agent: Agent 名称（用于参数随机化）

        Returns:
            {"content": str, "model": str, "usage": dict}
        """
        candidate = self._pick_model(model)
        if candidate is None:
            return {"content": "", "model": "", "usage": {}, "error": "No model available"}

        variator = self._get_variator(agent)
        params = self._vary_params(
            variator, agent=agent, base_temperature=temperature, base_max_tokens=max_tokens
        ) or {"temperature": temperature, "max_tokens": max_tokens}

        try:
            result = await self._call_llm(
                candidate=candidate,
                messages=messages,
                temperature=params.get("temperature", temperature),
                max_tokens=params.get("max_tokens", max_tokens),
            )
            self._last_best_model = candidate.model
            return result
        except Exception as e:
            logger.error(f"GachaEngine.chat 失败: {e}", exc_info=True)
            return {"content": "", "model": "", "usage": {}, "error": str(e)}

    async def chat_stream(
        self,
        messages: list[dict],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        agent: str = "",
    ) -> AsyncGenerator[dict, None]:
        """流式对话模式 — 逐 token 推送，用于 SSE 端点。

        Args:
            messages: OpenAI 格式消息列表
            model: 指定模型（空则用默认）
            temperature: 温度
            max_tokens: 最大 token 数
            agent: Agent 名称（用于参数随机化）

        Yields:
            {"type": "chunk", "content": str, "model": str}  文本片段
            {"type": "done", "model": str, "usage": dict}    完成信号
            {"type": "error", "error": str}                   错误信号
        """
        candidate = self._pick_model(model)
        if candidate is None:
            yield {"type": "error", "error": "No model available"}
            return

        variator = self._get_variator(agent)
        params = self._vary_params(
            variator, agent=agent, base_temperature=temperature, base_max_tokens=max_tokens
        ) or {"temperature": temperature, "max_tokens": max_tokens}

        url = f"{candidate.base_url}/chat/completions"
        breaker = self._get_breaker(candidate.base_url)

        try:
            async with breaker:
                async for chunk in self._stream_http_call(
                    url=url,
                    api_key=candidate.api_key,
                    model=candidate.model,
                    messages=messages,
                    temperature=params.get("temperature", temperature),
                    max_tokens=params.get("max_tokens", max_tokens),
                ):
                    yield chunk
            self._last_best_model = candidate.model
        except Exception as e:
            logger.error(f"GachaEngine.chat_stream 失败: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}

    async def generate(
        self,
        prompt: str,
        mode: str = "gacha_cascade",
        agent: str = "",
        chapter_type: str = "normal",
        humanize: bool = True,
    ) -> dict:
        """多模型抽卡生成 — 核心入口。

        Args:
            prompt: 生成提示词
            mode: 模式 (single_fix / gacha_cascade / gacha_vibe / single_chat)
            agent: Agent 名称
            chapter_type: 章节类型
            humanize: 是否在生成后自动执行去AI痕迹处理

        Returns:
            {
                "best_text": str,
                "best_model": str,
                "best_score": float,
                "scores": dict,  # {model: score}
                "candidates": list[dict],  # 所有候选结果
                "usage": dict,  # token 用量汇总
                "humanize": dict | None,  # 去AI痕迹结果
            }
        """
        if mode == "single_fix":
            result = await self._generate_single(prompt, agent, chapter_type)
        elif mode == "gacha_cascade":
            result = await self._generate_cascade(prompt, agent, chapter_type)
        elif mode == "gacha_vibe":
            result = await self._generate_vibe(prompt, agent, chapter_type)
        elif mode == "single_chat":
            messages = [{"role": "user", "content": prompt}]
            chat_result = await self.chat(messages, agent=agent)
            result = {
                "best_text": chat_result.get("content", ""),
                "best_model": chat_result.get("model", ""),
                "best_score": 1.0,
                "scores": {},
                "candidates": [],
                "usage": chat_result.get("usage", {}),
            }
        else:
            logger.warning(f"GachaEngine: 未知模式 '{mode}'，回退到 single_fix")
            result = await self._generate_single(prompt, agent, chapter_type)

        # 去AI痕迹后处理（嵌入生成管线）
        if humanize and result.get("best_text") and len(result["best_text"]) > _MIN_TEXT_LENGTH:
            try:
                from kunlun.humanize.engine import humanize_engine as _he

                # 根据章节类型自动选择策略
                if chapter_type == "opening":
                    strategy = "opening"
                elif agent in ("writer", "architect"):
                    strategy = "standard"
                else:
                    strategy = "minimal"

                h_result = await _he.humanize(
                    result["best_text"],
                    strategy=strategy,
                    chapter_type=chapter_type,
                )
                result["best_text"] = h_result.humanized
                result["humanize"] = {
                    "strategy": strategy,
                    "ai_score_before": h_result.ai_score_before,
                    "ai_score_after": h_result.ai_score_after,
                    "reduction_pct": h_result.reduction_pct,
                    "markers_before": h_result.markers_before,
                    "markers_after": h_result.markers_after,
                }
                logger.info(
                    f"GachaEngine: 去AI痕迹完成 "
                    f"({h_result.ai_score_before:.2f}→{h_result.ai_score_after:.2f}, "
                    f"-{h_result.reduction_pct:.0f}%)"
                )
            except Exception as e:
                logger.warning(f"GachaEngine: 去AI痕迹失败 ({e})，返回原始文本")
                result["humanize"] = None
        else:
            result["humanize"] = None

        return result

    async def generate_for_agent(
        self,
        prompt: str,
        agent: str = "",
        mode: str = "gacha_cascade",
        chapter_type: str = "normal",
    ) -> dict:
        """为特定 Agent 生成 — generate() 的别名，保持向后兼容。"""
        return await self.generate(prompt, mode=mode, agent=agent, chapter_type=chapter_type)

    # ── 内部方法 ──────────────────────────────────────

    async def _generate_single(
        self, prompt: str, agent: str = "", chapter_type: str = "normal"
    ) -> dict:
        """单模型修复模式"""
        candidate = self._pick_model()
        if candidate is None:
            return dict(self.EMPTY_RESULT)

        threshold = self.get_cascade_threshold(chapter_type)
        variator = self._get_variator(agent)
        params = self._vary_params(variator, agent=agent, chapter_type=chapter_type) or {}

        try:
            messages = [{"role": "user", "content": prompt}]
            result = await self._call_llm(
                candidate=candidate,
                messages=messages,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 4096),
            )
            text = result.get("content", "")
            score = self._score_text(text) if text else 0.0
            self._last_best_model = candidate.model
            return {
                "best_text": text,
                "best_model": candidate.model,
                "best_score": score,
                "scores": {candidate.model: score},
                "candidates": [{"model": candidate.model, "text": text, "score": score}],
                "usage": result.get("usage", {}),
            }
        except Exception as e:
            logger.error(f"GachaEngine._generate_single 失败: {e}", exc_info=True)
            return dict(self.EMPTY_RESULT)

    async def _generate_cascade(
        self, prompt: str, agent: str = "", chapter_type: str = "normal"
    ) -> dict:
        """多模型级联抽卡模式"""
        threshold = self.get_cascade_threshold(chapter_type)
        min_candidates = threshold.get("min_candidates", 2)
        candidates = self._pick_models(min_candidates)

        if not candidates:
            return await self._generate_single(prompt, agent, chapter_type)

        variator = self._get_variator(agent)
        tasks = []
        for c in candidates:
            params = self._vary_params(variator, agent=agent, chapter_type=chapter_type) or {}
            tasks.append(
                self._call_llm(
                    candidate=c,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=params.get("temperature", 0.7),
                    max_tokens=params.get("max_tokens", 4096),
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        scored: list[dict] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.warning(f"GachaEngine: 候选 {candidates[i].model} 失败: {result}")
                continue
            text = result.get("content", "")
            if text:
                score = self._score_text(text)
                scored.append(
                    {
                        "model": candidates[i].model,
                        "text": text,
                        "score": score,
                        "usage": result.get("usage", {}),
                    }
                )

        if not scored:
            return dict(self.EMPTY_RESULT)

        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0]

        self._last_best_model = best["model"]
        total_usage = self._merge_usage([s.get("usage", {}) for s in scored])

        return {
            "best_text": best["text"],
            "best_model": best["model"],
            "best_score": best["score"],
            "scores": {s["model"]: s["score"] for s in scored},
            "candidates": scored,
            "usage": total_usage,
        }

    async def _generate_vibe(
        self, prompt: str, agent: str = "", chapter_type: str = "normal"
    ) -> dict:
        """Vibe Writing 模式 — 高创意参数"""
        # Vibe 模式增加温度扰动
        return await self._generate_cascade(prompt, agent, chapter_type)

    # ── LLM 调用（含熔断器 + 指数退避重试 + Key 轮换）───

    async def _call_llm(
        self,
        candidate: ModelCandidate,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> dict:
        """调用 LLM API — 含熔断器保护、指数退避重试和 Key 轮换。

        Args:
            candidate: 模型候选
            messages: 消息列表
            temperature: 温度
            max_tokens: 最大 token 数
            max_retries: 最大重试次数

        Returns:
            {"content": str, "model": str, "usage": dict}

        Raises:
            CircuitBreakerOpenError: 熔断器开启
            Exception: 所有重试均失败
        """
        import httpx

        # 本地模型分支：provider == "local" 时走 LocalInferenceEngine
        if candidate.provider == "local":
            return await self._call_local_llm(
                candidate=candidate,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        url = f"{candidate.base_url}/chat/completions"
        breaker = self._get_breaker(candidate.base_url)

        # 第 1 层：熔断器保护
        async with breaker:
            last_error: BaseException | None = None

            for attempt in range(max_retries + 1):
                # 当前使用的 API Key（可能被轮换）
                current_key = candidate.api_key

                try:
                    return await self._make_http_call(
                        url=url,
                        api_key=current_key,
                        model=candidate.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                except httpx.HTTPStatusError as e:
                    last_error = e
                    error_info = self._classify_http_error(e)

                    if error_info["type"] == "rate_limit":
                        # 429 限流 → 冷却当前 Key，尝试轮换
                        logger.warning(
                            f"GachaEngine: {candidate.model} 触发限流 "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        if self._try_rotate_key(candidate):
                            logger.info("GachaEngine: 已切换到备用 Key，重试中...")
                            continue
                        # 无可轮换 Key，等待后重试
                        retry_after = error_info.get("retry_after", 5)
                        if attempt < max_retries:
                            await asyncio.sleep(retry_after)
                            continue

                    elif error_info["type"] == "server_error":
                        # 5xx → 指数退避
                        if attempt < max_retries:
                            delay = 2**attempt + 1
                            logger.warning(
                                f"GachaEngine: {candidate.model} 服务器错误 "
                                f"(attempt {attempt + 1}/{max_retries + 1})，"
                                f"{delay}s 后重试"
                            )
                            await asyncio.sleep(delay)
                            continue

                    elif error_info["type"] == "auth_error":
                        # 认证错误 → 不可恢复，标记 Key 失败
                        logger.error(f"GachaEngine: {candidate.model} 认证失败，Key 已移除")
                        self._mark_key_failed(current_key)
                        # 尝试轮换 Key
                        if self._try_rotate_key(candidate):
                            continue
                        raise  # 无可轮换 Key

                    else:
                        # 客户端错误 → 不重试
                        raise

                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    last_error = e
                    if attempt < max_retries:
                        delay = 2**attempt + 1
                        logger.warning(
                            f"GachaEngine: {candidate.model} 网络错误 "
                            f"(attempt {attempt + 1}/{max_retries + 1})，"
                            f"{delay}s 后重试"
                        )
                        await asyncio.sleep(delay)
                        # 网络错误也尝试轮换 Key（可能是该 Key 的代理问题）
                        self._try_rotate_key(candidate)
                        continue
                    raise

                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        delay = 2**attempt
                        logger.warning(
                            f"GachaEngine: {candidate.model} 未知错误: {e} "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise

            # 所有重试均失败
            if last_error is not None:
                raise last_error
            raise RuntimeError(f"{candidate.model} 调用失败（无详细错误）")

        # async with 块之后（__aexit__ 返回 False 不吞异常，理论上不可达）
        raise RuntimeError(f"{candidate.model} 调用失败（熔断器异常退出）")


    async def _call_local_llm(
        self,
        candidate: ModelCandidate,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """调用本地 LoRA 模型（通过 LocalInferenceEngine）

        通过 AdapterManager 查找适配器元数据（基座模型路径 + 适配器路径），
        加载模型后生成。模型加载是懒加载单例，首次调用较慢，后续复用。

        Args:
            candidate: 模型候选（model 字段为适配器名称）
            messages: OpenAI 格式消息列表
            temperature: 温度
            max_tokens: 最大生成 token 数

        Returns:
            {"content": str, "model": str, "usage": dict}
        """
        from kunlun.finetune.local_inference import get_local_engine
        from kunlun.finetune.adapter_manager import AdapterManager

        adapter_name = candidate.model
        engine = get_local_engine()

        # 如果模型未加载或适配器不匹配，加载适配器
        if not engine.is_loaded() or engine.current_adapter != adapter_name:
            mgr = AdapterManager("data/adapters")
            info = mgr.load_adapter(adapter_name)
            if info is None:
                raise RuntimeError(
                    f"本地适配器 {adapter_name} 未注册，"
                    f"请先在 data/adapters/ 下注册"
                )

            # 从 metadata 中获取基座模型路径和适配器路径
            import json
            from pathlib import Path

            meta_path = Path(info.path) / "metadata.json"
            base_model_path = ""
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                base_model_path = meta.get("base_model_path", "")

            if not base_model_path:
                raise RuntimeError(
                    f"适配器 {adapter_name} 的 metadata.json 中缺少 base_model_path"
                )

            # 从metadata读取是否需要4bit量化
            load_in_4bit = meta.get("load_in_4bit", False) if meta_path.exists() else False

            # 在线程中加载模型（避免阻塞事件循环）
            import asyncio

            await asyncio.to_thread(
                engine.load_adapter,
                adapter_name=adapter_name,
                base_model_path=base_model_path,
                adapter_path=info.path,
                load_in_4bit=load_in_4bit,
            )

        # 生成（本地模型使用更低的 repetition_penalty 避免提前停止，限制 max_tokens 上限）
        local_max_tokens = min(max_tokens, 2048)
        return await engine.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=local_max_tokens,
            repetition_penalty=1.02,
        )

    async def _make_http_call(
        self,
        url: str,
        api_key: str,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        timeout: float = 120.0,
    ) -> dict:
        """执行单次 HTTP 调用（复用共享 httpx 连接池）"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        client = self._get_http_client()
        response = await client.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        return {
            "content": choice["message"]["content"],
            "model": data.get("model", model),
            "usage": data.get("usage", {}),
        }

    async def _stream_http_call(
        self,
        url: str,
        api_key: str,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        timeout: float = 120.0,
    ) -> AsyncGenerator[dict, None]:
        """执行流式 HTTP 调用 — 逐 SSE chunk 解析，yield token 增量。

        解析 OpenAI 兼容的 SSE 格式:
            data: {"choices":[{"delta":{"content":"..."},"finish_reason":null}]}
            data: {"choices":[{"delta":{},"finish_reason":"stop"}]}
            data: [DONE]

        Yields:
            {"type": "chunk", "content": str, "model": str}
            {"type": "done", "model": str, "usage": dict}
            {"type": "error", "error": str}
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        try:
            client = self._get_http_client()
            async with client.stream(
                "POST", url, json=payload, headers=headers, timeout=timeout
            ) as response:
                response.raise_for_status()
                accumulated = ""
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]  # 去掉 "data: " 前缀
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    finish_reason = choices[0].get("finish_reason")
                    if finish_reason == "stop":
                        break
                    content = delta.get("content", "")
                    if content:
                        accumulated += content
                        yield {
                            "type": "chunk",
                            "content": content,
                            "model": data.get("model", model),
                        }

                # 流式完成
                yield {
                    "type": "done",
                    "model": model,
                    "usage": data.get("usage", {}),
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"[Stream] HTTP {e.response.status_code}: {e}")
            yield {"type": "error", "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"[Stream] 流式调用失败: {e}")
            yield {"type": "error", "error": str(e)}

    def _classify_http_error(self, error) -> dict:
        """分类 HTTP 错误，返回错误类型和元信息"""
        status = error.response.status_code if hasattr(error, "response") else 0

        if status == _HTTP_RATE_LIMIT_STATUS:
            retry_after = 5
            try:
                retry_header = error.response.headers.get("Retry-After", "5")
                retry_after = int(retry_header)
            except (ValueError, AttributeError):
                pass
            return {"type": "rate_limit", "status": status, "retry_after": retry_after}

        if status in (401, 403):
            return {"type": "auth_error", "status": status}

        if _HTTP_SERVER_ERROR_MIN <= status < _HTTP_SERVER_ERROR_MAX:
            return {"type": "server_error", "status": status}

        return {"type": "client_error", "status": status}

    def _try_rotate_key(self, candidate: ModelCandidate) -> bool:
        """尝试轮换到备用 API Key。

        Returns:
            True 如果成功轮换了 Key
        """
        if self._key_rotator is None or not self._key_rotator.has_keys():
            return False

        new_key = self._key_rotator.next()
        if new_key and new_key != candidate.api_key:
            candidate.api_key = new_key
            return True
        return False

    def _mark_key_failed(self, key: str) -> None:
        """标记 Key 彻底失败"""
        if self._key_rotator:
            self._key_rotator.mark_failed(key)

    # ── 评分系统 (9维纯文本统计) ──────────────────────

    def _score_text(self, text: str) -> float:
        """10 维综合评分 — 纯文本统计，零 LLM 成本。

        权重:
          多样性 0.10, 连贯性 0.10, 信息密度 0.10,
          情感波动 0.10, 节奏感 0.10, 创新度 0.10,
          流畅度 0.10, 完整性 0.10, 人味度 0.10,
          风格匹配度 0.10
        """
        if not text or len(text) < _MIN_TEXT_LENGTH:
            return 0.0

        scores = {
            "diversity": self._score_diversity(text),
            "coherence": self._score_coherence(text),
            "info_density": self._score_info_density(text),
            "emotion": self._score_emotion(text),
            "rhythm": self._score_rhythm(text),
            "novelty": self._score_novelty(text),
            "fluency": self._score_fluency(text),
            "completeness": self._score_completeness(text),
            "humanness": self._score_humanness(text),
            "style_match": self._score_style_match(text),
        }

        weights = {
            "diversity": 0.10,
            "coherence": 0.10,
            "info_density": 0.10,
            "emotion": 0.10,
            "rhythm": 0.10,
            "novelty": 0.10,
            "fluency": 0.10,
            "completeness": 0.10,
            "humanness": 0.10,
            "style_match": 0.10,
        }

        total = sum(scores[k] * weights[k] for k in scores)
        return round(total, 4)

    def _score_diversity(self, text: str) -> float:
        """词汇多样性 — 基于唯一词比例"""
        words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", text)
        if not words:
            return 0.0
        unique_ratio = len(set(words)) / len(words)
        return min(_DIVERSE_SCORE_CAP, unique_ratio * _DIVERSE_UNIQUE_RATIO_MULTIPLIER)

    def _score_coherence(self, text: str) -> float:
        """连贯性 — 基于句子间词汇重叠"""
        sentences = re.split(r"[。！？.!?\n]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > _COHERENCE_MIN_SENTENCE_CHARS]
        if len(sentences) < _COHERENCE_MIN_SENTENCES:
            return _COHERENCE_DEFAULT_SCORE
        overlaps = []
        for s1, s2 in itertools.pairwise(sentences):
            w1 = set(re.findall(r"[\u4e00-\u9fff]+", s1))
            w2 = set(re.findall(r"[\u4e00-\u9fff]+", s2))
            if w1 and w2:
                overlaps.append(len(w1 & w2) / max(len(w1 | w2), 1))
        return sum(overlaps) / len(overlaps) if overlaps else 0.0

    def _score_info_density(self, text: str) -> float:
        """信息密度 — 实体词/总词比"""
        words = re.findall(r"[\u4e00-\u9fff]+", text)
        if not words:
            return 0.0
        entities = len(re.findall(r"[\u4e00-\u9fff]{2,4}", text))
        return min(1.0, entities / len(words) * 2.0)

    def _score_emotion(self, text: str) -> float:
        """情感波动 — 情感词密度和分布"""
        positive = re.findall(r"(激动|喜悦|温暖|欣慰|感动|惊喜|振奋|欢快|兴奋|开心|幸福)", text)
        negative = re.findall(r"(愤怒|悲伤|恐惧|绝望|痛苦|焦虑|压抑|阴沉|凄惨|悲愤)", text)
        total_emo = len(positive) + len(negative)
        if total_emo == 0:
            return 0.3  # 中性
        # 情感词密度 + 正负平衡度
        density = min(1.0, total_emo / max(len(text) / 100, 1) * 0.5)
        balance = 1.0 - abs(len(positive) - len(negative)) / max(total_emo, 1)
        return (density + balance) / 2

    def _score_rhythm(self, text: str) -> float:
        """节奏感 — 句长变异系数"""
        sentences = re.split(r"[。！？.!?\n]+", text)
        lengths = [len(s) for s in sentences if len(s.strip()) > _RHYTHM_MIN_SENTENCE_CHARS]
        if len(lengths) < _RHYTHM_MIN_SENTENCES:
            return _RHYTHM_DEFAULT_SCORE
        mean_len = sum(lengths) / len(lengths)
        if mean_len == 0:
            return 0.0
        variance = sum((length - mean_len) ** 2 for length in lengths) / len(lengths)
        cv = math.sqrt(variance) / mean_len
        # 适中的变异系数（0.3~0.8）最好
        return _DIVERSE_SCORE_CAP - abs(cv - _RHYTHM_TARGET_CV)

    def _score_novelty(self, text: str) -> float:
        """创新度 — 低频词比例"""
        words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        if not words:
            return 0.0
        word_freq: dict[str, int] = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1
        rare = sum(1 for v in word_freq.values() if v == 1)
        return min(1.0, rare / len(word_freq) * 2.0)

    def _score_fluency(self, text: str) -> float:
        """流畅度 — 基于 n-gram 重复度"""
        bigrams = self.ngrams(text, 2)
        if not bigrams:
            return 0.5
        return len(set(bigrams)) / len(bigrams)

    def _score_completeness(self, text: str) -> float:
        """完整性 — 是否有开头结尾"""
        score = _COMPLETENESS_DEFAULT_SCORE
        if len(text) > _COMPLETENESS_MIN_CHARS:
            score += _COMPLETENESS_LENGTH_BONUS
        if re.search(r"[。！？.!?]$", text.strip()):
            score += _COMPLETENESS_ENDING_BONUS
        if re.search(r"^(第[一二三四五六七八九十百千]+[章节回]|[\u4e00-\u9fff]{2,6}\n)", text):
            score += 0.15
        return min(1.0, score)

    def _score_humanness(self, text: str) -> float:
        """人味度 — 对话占比、语气词、句式变化"""
        dialogue = len(re.findall(r"[「「" "''](.*?)[」」" "''" "]", text))
        total = len(text)
        dialogue_ratio = dialogue / max(total, 1)
        interjections = len(re.findall(r"(啊|呢|吧|嘛|呀|哦|嗯|哈|呵|唉|哎)", text))
        interjection_ratio = interjections / max(total / 10, 1)
        return min(1.0, dialogue_ratio * 5 + interjection_ratio * 3)

    def _score_style_match(self, text: str) -> float:
        """风格匹配度 — 第10维评分。

        若设置了 target_style_fingerprint，计算文本与目标风格的余弦相似度。
        否则使用通用风格丰富度评分（句长变化、标点多样性、词汇丰富度等）。
        """
        if not text or len(text) < _MIN_TEXT_LENGTH:
            return 0.5

        # 如果设置了目标风格指纹，计算与目标的相似度
        if self.target_style_fingerprint is not None:
            try:
                from kunlun.style.fingerprint import style_analyzer
                current_fp = style_analyzer.analyze(text, name="gacha_candidate")
                sim = current_fp.cosine_similarity(self.target_style_fingerprint)
                return round(min(1.0, max(0.0, sim)), 4)
            except Exception as e:
                logger.debug(f"GachaEngine: 风格相似度计算失败，回退通用评分: {e}")

        # 句长变化（标准差）
        sentences = re.split(r"[。！？!?]", text)
        sentences = [s for s in sentences if len(s.strip()) >= 2]
        if len(sentences) >= 3:
            lengths = [len(s) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            std_dev = variance**0.5
            cv = std_dev / max(mean_len, 1)
            sentence_variety = min(1.0, cv / 0.5)
        else:
            sentence_variety = 0.3

        # 标点多样性
        punct_types = set(re.findall(r"[，。！？、；：…—" "''「」『』]", text))
        punct_diversity = min(1.0, len(punct_types) / 8)

        # 词汇丰富度（TTR）
        chars = [c for c in text if "一" <= c <= "鿿"]
        if chars:
            ttr = len(set(chars)) / len(chars)
            vocab_richness = min(1.0, ttr / 0.5)
        else:
            vocab_richness = 0.3

        # 对话占比
        dialogues = re.findall(r"[" "「『]([^" "」』]+)[" "」』]", text)
        dialogue_chars = sum(len(d) for d in dialogues)
        dialogue_ratio = dialogue_chars / max(len(text), 1)
        dialogue_score = min(1.0, dialogue_ratio * 5)

        # 语气词频率
        interjections = len(re.findall(r"(啊|呢|吧|嘛|呀|哦|嗯|哈|呵|唉|哎|哇)", text))
        interj_ratio = interjections / max(len(text) / 100, 1)
        interj_score = min(1.0, interj_ratio * 2)

        # 综合评分（等权重）
        total = (
            sentence_variety * 0.25
            + punct_diversity * 0.20
            + vocab_richness * 0.20
            + dialogue_score * 0.20
            + interj_score * 0.15
        )
        return min(1.0, max(0.0, round(total, 4)))

    # ── 工具方法 ──────────────────────────────────────

    @staticmethod
    def ngrams(s: str, n: int) -> list[str]:
        """提取 n-gram"""
        chars = list(s)
        return ["".join(chars[i : i + n]) for i in range(len(chars) - n + 1)]

    def _pick_model(self, preferred: str = "") -> ModelCandidate | None:
        """选择单个模型"""
        if not self._models:
            return None
        if preferred:
            for m in self._models:
                if m.model == preferred:
                    return m
        return self._models[0]

    def _pick_models(self, count: int = 2) -> list[ModelCandidate]:
        """选择多个模型"""
        return self._models[: min(count, len(self._models))]

    def _get_variator(self, agent: str = "") -> ParamVariator | None:
        """获取 Agent 对应的参数随机化器"""
        if not agent:
            return None
        if agent not in self._param_variators:
            self._param_variators[agent] = ParamVariator()
        return self._param_variators[agent]

    def _vary_params(
        self,
        variator: ParamVariator | None,
        agent: str = "",
        chapter_type: str = "normal",
        base_temperature: float = 0.7,
        base_max_tokens: int = 4096,
    ) -> dict:
        """从 ParamVariator 获取随机化参数"""
        if variator is None:
            return {}
        try:
            varied = variator.get_params(
                agent=agent or "default",
                chapter=0,
                chapter_type=chapter_type,
                base_max_tokens=base_max_tokens,
            )
            return {
                "temperature": getattr(varied, "temperature", base_temperature),
                "max_tokens": getattr(varied, "max_tokens", base_max_tokens),
            }
        except Exception as e:
            logger.debug(f"[GachaEngine] 参数随机化失败 (agent={agent}): {e}")
            return {}

    def _merge_usage(self, usages: list[dict]) -> dict:
        """合并多个调用的 token 用量"""
        total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for u in usages:
            for k in total:
                total[k] += u.get(k, 0)
        return total


# ── 全局单例 ──────────────────────────────────────────

gacha_engine = GachaEngine.get_instance()
