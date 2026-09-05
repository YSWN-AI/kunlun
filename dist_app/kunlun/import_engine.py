"""
章节导入引擎 — 从已有小说文本逆向工程真相文件

对应 inkos import chapters 命令

功能:
  1. 章节分割 — 自动检测分割模式(第X章 / Chapter X / 自定义)
  2. 逆向工程 — 通过LLM从文本提取角色/地点/物品/伏笔/力量体系
  3. 真相文件写入 — 将提取的结构化信息写入7个真相文件
  4. 断点续导 — 支持从指定章节开始,避免重复导入
  5. 同人创作 — 基于原作初始化同人创作模式

使用方式:
    from kunlun.import_engine import chapter_importer, fanfic_initializer

    # 导入章节
    importer = chapter_importer
    result = await importer.import_chapters("book_id", novel_text, start_chapter=1)

    # 同人初始化
    fanfic = await fanfic_initializer.init_fanfic("book_id", source_text, mode="canon")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from loguru import logger

from kunlun.config import settings


@dataclass
class ImportResult:
    """章节导入结果"""

    book_id: str
    chapters_imported: int
    characters_extracted: list[str]
    locations_found: list[str]
    items_found: list[str]
    hooks_detected: list[str]
    total_words: int
    errors: list[str] = field(default_factory=list)


class ChapterImporter:
    """章节导入器

    核心流程:
    1. read_file(filepath) — 从文件路径读取文本，自动检测 .txt/.md/.docx 格式
    2. detect_chapter_pattern(text) — 自动检测章节分割模式
    3. split_chapters(text, pattern) — 按检测到的模式分割为(标题,正文)列表
    4. import_chapters(book_id, text, start_chapter) — 导入并逆向工程
    """

    @staticmethod
    def read_file(filepath: str) -> str:
        """从文件路径读取文本，自动检测格式（支持 .txt/.md/.docx）"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8")
        if suffix == ".docx":
            try:
                from docx import Document

                doc = Document(str(path))
                return "\n\n".join(p.text for p in doc.paragraphs if p.text)
            except ImportError:
                raise ImportError("DOCX导入需要: pip install python-docx") from None
        else:
            raise ValueError(f"不支持的文件格式: {suffix}，支持 .txt/.md/.docx")

    # 支持的章节分割模式
    CHAPTER_PATTERNS = [
        r"第[一二三四五六七八九十百千\d]+章",
        r"Chapter\s+\d+",
        r"第\d+章",
        r"第\s*\d+\s*章",
    ]

    def detect_chapter_pattern(self, text: str) -> str:
        """自动检测章节分割模式

        按优先级尝试多种模式,返回第一个匹配到的正则表达式。

        Args:
            text: 原始文本

        Returns:
            正则表达式字符串
        """
        for pat in self.CHAPTER_PATTERNS:
            if re.search(pat, text):
                # 统计匹配次数,确认是分割模式而非偶然出现
                matches = re.findall(pat, text)
                if len(matches) >= 2:
                    logger.info(f"[Importer] 检测到章节模式: {pat} ({len(matches)}处)")
                    return pat

        # fallback: 使用短标题+正文的模式判断
        logger.info("[Importer] 未检测到标准章节模式,使用fallback分割")
        return r"\n(?=[^\n]{1,30}\n[^\n]{10,})"

    def split_chapters(self, text: str, pattern: str | None = None) -> list[tuple[str, str]]:
        """分割文本为章节列表

        Args:
            text: 原始文本
            pattern: 分割正则表达式 (None则自动检测)

        Returns:
            [(标题, 正文), ...] 的列表
        """
        if not pattern:
            pattern = self.detect_chapter_pattern(text)

        # 找所有分割点
        matches = list(re.finditer(pattern, text))
        if not matches:
            logger.info("[Importer] 未找到章节分割点,整文作为单章导入")
            return [("第1章", text.strip())]

        chapters = []
        for i, m in enumerate(matches):
            title = m.group(0).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            # 跳过空章节
            if content:
                chapters.append((title, content))

        logger.info(f"[Importer] 分割完成: {len(chapters)}章")
        return chapters

    async def import_chapters(
        self, book_id: str, text: str, start_chapter: int = 1
    ) -> ImportResult:
        """导入章节并逆向工程真相文件

        流程:
        1. 分割章节
        2. 逐章添加摘要到chapter_summaries
        3. 汇总全文,通过LLM提取结构化信息
        4. 将角色/地点/物品/伏笔写入对应真相文件

        LLM调用: 使用 gacha_engine.generate() 的真实模型推断,
        不使用mock数据。

        Args:
            book_id: 作品ID
            text: 原始文本
            start_chapter: 起始章节号 (用于断点续导)

        Returns:
            ImportResult 导入结果
        """
        from kunlun.gacha.engine import gacha_engine
        from kunlun.truth import get_truth_manager

        chapters = self.split_chapters(text)
        if start_chapter > 1:
            chapters = chapters[start_chapter - 1 :]
            logger.info(f"[Importer] 跳过前{start_chapter - 1}章,从第{start_chapter}章开始")

        result = ImportResult(
            book_id=book_id,
            chapters_imported=0,
            characters_extracted=[],
            locations_found=[],
            items_found=[],
            hooks_detected=[],
            total_words=0,
        )

        tm = get_truth_manager(book_id)

        # 逐章处理（使用列表收集避免 O(n²) 字符串拼接）
        all_parts: list[str] = []
        for i, (_title, content) in enumerate(chapters):
            ch_num = start_chapter + i
            all_parts.append(content)
            result.total_words += len(content)

            # 将本章摘要写入 chapter_summaries.json
            cast(Any, tm).add_chapter_summary(ch_num, content[:200], [], [], [])
            result.chapters_imported += 1

            # 每10章输出一次进度
            if (i + 1) % 10 == 0:
                logger.info(f"[Importer] 进度: {i + 1}/{len(chapters)}章")

        all_text = "\n\n".join(all_parts)

        logger.info(f"[Importer] 全部{len(chapters)}章摘要已写入,开始LLM逆向工程...")

        # ── LLM逆向工程（分块策略）──
        # 长篇取首部+中部+尾部各4000字作为分析样本，覆盖全文角色和设定
        text_len = len(all_text)
        if text_len <= 12000:
            analysis_sample = all_text
        else:
            head = all_text[:4000]
            mid_start = text_len // 2 - 2000
            mid = all_text[mid_start : mid_start + 4000]
            tail = all_text[-4000:]
            analysis_sample = head + "\n\n...\n\n" + mid + "\n\n...\n\n" + tail

        if len(analysis_sample) < 100:
            result.errors.append("文本过短(<100字),无法进行有效分析")
            logger.warning("[Importer] 文本过短,跳过LLM逆向工程")
            return result

        prompt = f"""你是小说结构分析师。请从以下小说文本中提取结构化信息。\
输出纯净JSON（不要markdown代码块,不要```json```包裹）：

{{
  "characters": [
    {{"name":"角色名","role":"protagonist/antagonist/supporting","traits":["性格1","性格2"]}}
  ],
  "locations": ["地点1","地点2"],
  "items": ["重要物品1","重要物品2"],
  "hooks": ["未解决伏笔1","未解决伏笔2"],
  "power_system": {{"name":"力量体系名","levels":["等级1","等级2"]}},
  "world_setting": "世界观简述(50字内)"
}}

规则:
- 仅提取在文本中明确出现的信息,不要臆测
- 角色role必须是 protagonist/antagonist/supporting 之一
- traits 尽量从文本中推断角色的性格特征
- hooks 指文中提到但尚未解决的悬念/谜团/承诺
- 如果某项信息在文本中未被提及,返回空数组/空对象

小说文本（前8000字）:
{analysis_sample}"""

        try:
            logger.info("[Importer] 向LLM发送逆向工程请求...")
            res = await gacha_engine.generate(prompt, mode="single_fix")
            text_out = res.get("best_text", "")

            if not text_out:
                result.errors.append("LLM返回空内容")
                logger.error("[Importer] LLM返回空内容")
                return result

            # 提取JSON (处理可能包裹在```json```或```中的情况)
            json_start = text_out.find("{")
            json_end = text_out.rfind("}")

            if json_start < 0 or json_end <= json_start:
                result.errors.append(f"LLM输出中未找到JSON: {text_out[:100]}...")
                logger.error(f"[Importer] 未在LLM输出中找到JSON: {text_out[:200]}")
                return result

            json_str = text_out[json_start : json_end + 1]
            data = json.loads(json_str)

            # 提取结果
            result.characters_extracted = [
                c.get("name", "") for c in data.get("characters", []) if c.get("name")
            ]
            result.locations_found = data.get("locations", [])
            result.items_found = data.get("items", [])
            result.hooks_detected = data.get("hooks", [])

            # ── 写入真相文件 ──

            # 1. 角色状态 → current_state.json
            for char in data.get("characters", []):
                name = char.get("name", "")
                if not name:
                    continue
                cast(Any, tm).update_character_state(
                    name,
                    start_chapter,
                    role=char.get("role", ""),
                    traits=char.get("traits", []),
                )

            # 2. 角色到 character_matrix.json
            characters_list = data.get("characters", [])
            for i, c1 in enumerate(characters_list):
                for c2 in characters_list[i + 1 :]:
                    name1, name2 = c1.get("name", ""), c2.get("name", "")
                    if name1 and name2:
                        cast(Any, tm).update_character_interaction(
                            name1, name2, start_chapter, "introduction", []
                        )

            # 3. 伏笔 → pending_hooks.json
            total_chapters = len(chapters)
            for hook in data.get("hooks", []):
                if hook:
                    cast(Any, tm).register_hook(
                        hook,
                        start_chapter,
                        start_chapter + total_chapters + 10,  # 预期在后续揭示
                        priority="medium",
                        description=hook,
                    )

            # 4. 力量体系 → book_rules.json
            power_system = data.get("power_system", {})
            if power_system and power_system.get("name"):
                cast(Any, tm).add_book_rule(
                    f"力量体系: {power_system['name']} - "
                    f"等级: {', '.join(power_system.get('levels', []))}",
                    rule_type="hard",
                )

            # 5. 世界观 → book_rules.json
            world_setting = data.get("world_setting", "")
            if world_setting:
                cast(Any, tm).add_book_rule(f"世界观: {world_setting}", rule_type="soft")

            logger.info(
                f"[Importer] 逆向工程完成: "
                f"{len(result.characters_extracted)}角色, "
                f"{len(result.locations_found)}地点, "
                f"{len(result.items_found)}物品, "
                f"{len(result.hooks_detected)}伏笔"
            )

        except json.JSONDecodeError as e:
            result.errors.append(f"JSON解析失败: {e}")
            logger.error(f"[Importer] JSON解析失败: {e}\n原始输出: {text_out[:300]}")
        except Exception as e:
            result.errors.append(f"LLM逆向工程失败: {e}")
            logger.error(f"[Importer] 逆向工程失败: {e}")

        return result


class FanficInitializer:
    """同人创作初始化器 — 对应 inkos fanfic init

    支持4种模式:
    - canon: 正典延续 — 严格遵守原作设定,在原作时间线上继续创作
    - au: 架空世界 — 使用原作角色,但改变世界观设定
    - ooc: 性格重塑 — 使用原作世界观,但重塑角色性格
    - cp: CP向 — 聚焦特定角色关系的发展

    使用 gacha_engine.generate() 调用真实LLM进行分析和生成。
    """

    MODES = {
        "canon": "正典延续 — 严格遵守原作设定，在原作时间线上继续创作，不改变任何已有设定",
        "au": "架空世界 — 使用原作角色，但改变世界观设定（如从仙侠转为现代都市），保持角色核心性格",
        "ooc": "性格重塑 — 使用原作世界观，但重塑角色性格（如将懦弱主角改写为强势），保留世界规则",
        "cp": "CP向 — 聚焦特定角色关系的发展，强调感情线和互动，弱化战斗/升级元素",
    }

    async def init_fanfic(self, book_id: str, source_text: str, mode: str = "canon") -> dict:
        """初始化同人创作

        通过LLM分析原作,生成创作简报。简报包括:
        - 同人作品标题建议
        - 长期创作意图
        - 必须保留的原作元素
        - 与原作的分歧点
        - 角色修改方案
        - 世界观调整
        - 同人专属审计重点

        使用 gacha_engine.generate() 调用真实模型。

        Args:
            book_id: 作品ID
            source_text: 原作文本(前5000字作为分析样本)
            mode: 同人模式 (canon/au/ooc/cp)

        Returns:
            创作简报 dict
        """
        from kunlun.gacha.engine import gacha_engine

        mode_desc = self.MODES.get(mode, self.MODES["canon"])
        analysis_sample = source_text[:5000]

        if len(analysis_sample) < 100:
            return {
                "error": "原作文本过短(<100字),无法进行有效分析",
                "mode": mode,
            }

        prompt = f"""你是同人创作顾问。根据原作和创作模式,生成创作简报。\
输出纯净JSON（不要markdown代码块,不要```json```包裹）：

{{
  "title": "同人作品标题建议",
  "author_intent": "长期创作意图(100-200字)",
  "canon_elements_to_keep": ["必须保留的原作元素1","元素2"],
  "divergence_points": ["与原作的分歧点1","分歧点2"],
  "character_modifications": [
    {{"name":"角色名","changes":"修改说明"}}
  ],
  "world_rule_modifications": ["世界观调整1","调整2"],
  "audit_focus": ["同人专属审计重点1","重点2"]
}}

原作内容（前5000字）:
{analysis_sample}

创作模式: {mode_desc}

注意事项:
- 忠实分析原作的人物关系和世界观
- 根据创作模式合理规划分歧点
- 审计重点应针对同人创作常见问题(角色OOC/世界观矛盾/原作关系破坏)"""

        try:
            logger.info(f"[Fanfic] 向LLM发送同人初始化请求 (模式: {mode})...")
            res = await gacha_engine.generate(prompt, mode="single_fix")
            text = res.get("best_text", "")

            if not text:
                logger.error("[Fanfic] LLM返回空内容")
                return {"error": "LLM返回空内容", "mode": mode}

            # 提取JSON
            json_start = text.find("{")
            json_end = text.rfind("}")

            if json_start < 0 or json_end <= json_start:
                logger.error(f"[Fanfic] 未在LLM输出中找到JSON: {text[:200]}")
                return {
                    "error": "LLM输出解析失败",
                    "raw_output": text[:500],
                    "mode": mode,
                }

            brief = json.loads(text[json_start : json_end + 1])

            # 保存同人创作简报
            path = settings.DATA_DIR / "fanfic" / book_id
            path.mkdir(parents=True, exist_ok=True)
            (path / "brief.json").write_text(
                json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (path / "mode.txt").write_text(mode, encoding="utf-8")

            logger.info(f"[Fanfic] 同人创作简报已生成并保存: {path}")
            return brief

        except json.JSONDecodeError as e:
            logger.error(f"[Fanfic] JSON解析失败: {e}\n原始输出: {text[:300]}")
            return {
                "error": f"JSON解析失败: {e}",
                "raw_output": text[:500] if text else "",
                "mode": mode,
            }
        except Exception as e:
            logger.error(f"[Fanfic] 初始化失败: {e}")
            return {"error": f"初始化失败: {e}", "mode": mode}


# ── 全局单例 ──
chapter_importer = ChapterImporter()
fanfic_initializer = FanficInitializer()
