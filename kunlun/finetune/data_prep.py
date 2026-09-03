"""
数据准备模块 — 从写作历史构建 LoRA 微调数据集

纯规则实现，不依赖 LLM。支持：
- 从 data/books/ 提取章节文本
- 按风格分组
- 生成 instruction-tuning (Alpaca) 格式
- 生成续写训练格式
- JSONL/JSON 保存与加载
- 数据集统计
- 文本风格特征分析
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

# 默认风格关键词映射
DEFAULT_STYLE_KEYWORDS: dict[str, list[str]] = {
    "xianxia": ["仙侠", "修真", "灵气", "飞剑", "丹药", "宗门", "渡劫", "元婴", "金丹", "道侣"],
    "xuanhuan": ["玄幻", "斗气", "武魂", "魔法", "魔兽", "斗气大陆", "斗帝", "魂环", "灵力"],
    "dushi": ["都市", "总裁", "校花", "职场", "公司", "都市重生", "异能", "神医", "兵王"],
    "lishi": ["历史", "穿越", "古代", "王朝", "皇帝", "将军", "科举", "朝堂", "三国", "大唐"],
    "kehuan": ["科幻", "星际", "机甲", "宇宙", "飞船", "基因", "赛博", "未来", "人工智能"],
}

# 句子结束标点
_SENTENCE_END = re.compile(r"[。！？!?…]+")
# 对话引号匹配（中文引号）
_DIALOGUE_PATTERN = re.compile(r"[“\"]([^”\"]*)[”\"]")
# 描写性用词
_DESCRIPTION_WORDS = {"的", "了", "着", "地", "得", "仿佛", "宛如", "犹如", "似乎", "好像"}


class DatasetBuilder:
    """数据集构建器

    从本地书籍目录提取章节，构建多种格式的微调数据集。

    用法:
        builder = DatasetBuilder(books_dir="data/books")
        chapters = builder.extract_chapters()
        dataset = builder.build_instruction_tuning_dataset(chapters)
        builder.save_dataset(dataset, "data/finetune_datasets/train.jsonl")
    """

    def __init__(
        self,
        books_dir: str = "data/books",
        output_dir: str = "data/finetune_datasets",
    ) -> None:
        self.books_dir = Path(books_dir)
        self.output_dir = Path(output_dir)

    # ── 章节提取 ──────────────────────────────────

    def extract_chapters(
        self,
        book_id: str | None = None,
        min_chars: int = 200,
    ) -> list[dict[str, Any]]:
        """从 data/books/ 目录提取章节文本

        目录结构支持:
            data/books/book_<id>/chapters/chapter_<num>.txt
            data/books/book_<id>/project.json + chapters/

        Args:
            book_id: 指定书籍ID，None 则遍历所有书籍
            min_chars: 最小字符数，过滤过短章节

        Returns:
            章节列表，每项含 book_id/chapter/title/content/word_count
        """
        chapters: list[dict[str, Any]] = []

        if not self.books_dir.exists():
            return chapters

        # 确定要扫描的书籍目录
        if book_id:
            book_dirs = [self.books_dir / book_id]
        else:
            book_dirs = [d for d in self.books_dir.iterdir() if d.is_dir()]

        for book_dir in book_dirs:
            if not book_dir.exists():
                continue

            bid = book_dir.name
            chapters_dir = book_dir / "chapters"

            # 尝试从 project.json 获取元数据
            genre = self._read_book_genre(book_dir)

            if chapters_dir.exists():
                for ch_file in sorted(chapters_dir.glob("chapter_*.txt")):
                    try:
                        content = ch_file.read_text(encoding="utf-8").strip()
                    except (OSError, UnicodeDecodeError):
                        continue

                    if len(content) < min_chars:
                        continue

                    # 从文件名提取章节号
                    num_match = re.search(r"chapter_(\d+)", ch_file.stem)
                    chapter_num = int(num_match.group(1)) if num_match else 0

                    # 尝试从内容第一行提取标题
                    title, body = self._extract_title(content)

                    chapters.append(
                        {
                            "book_id": bid,
                            "chapter": chapter_num,
                            "title": title,
                            "content": body,
                            "word_count": len(body),
                            "genre": genre,
                        }
                    )
            else:
                # 兼容：直接在书籍目录下找 .txt 文件
                for txt_file in sorted(book_dir.glob("*.txt")):
                    try:
                        content = txt_file.read_text(encoding="utf-8").strip()
                    except (OSError, UnicodeDecodeError):
                        continue

                    if len(content) < min_chars:
                        continue

                    title, body = self._extract_title(content)
                    chapters.append(
                        {
                            "book_id": bid,
                            "chapter": 0,
                            "title": title or txt_file.stem,
                            "content": body,
                            "word_count": len(body),
                            "genre": genre,
                        }
                    )

        return chapters

    @staticmethod
    def _read_book_genre(book_dir: Path) -> str:
        """从 project.json 读取书籍类型"""
        project_file = book_dir / "project.json"
        if not project_file.exists():
            return ""
        try:
            data = json.loads(project_file.read_text(encoding="utf-8"))
            return str(data.get("genre", "") or data.get("type", ""))
        except (OSError, json.JSONDecodeError):
            return ""

    @staticmethod
    def _extract_title(content: str) -> tuple[str, str]:
        """从内容第一行提取标题"""
        lines = content.split("\n", 1)
        first = lines[0].strip()
        # 标题通常较短且不含大量标点
        if len(first) < 50 and not first.endswith(("。", "！", "？")):
            body = lines[1].strip() if len(lines) > 1 else content
            return first, body
        return "", content

    # ── 风格分组 ──────────────────────────────────

    def group_by_style(
        self,
        chapters: list[dict[str, Any]],
        style_keywords: dict[str, list[str]] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """按风格分组章节

        优先使用书籍元数据中的 genre 字段，其次用关键词匹配内容。

        Args:
            chapters: 章节列表
            style_keywords: 自定义风格关键词映射

        Returns:
            风格名 → 章节列表
        """
        keywords = style_keywords or DEFAULT_STYLE_KEYWORDS
        groups: dict[str, list[dict[str, Any]]] = {k: [] for k in keywords}
        groups["other"] = []

        for ch in chapters:
            genre = str(ch.get("genre", "")).lower()
            content = ch.get("content", "")
            assigned = False

            # 优先用 genre 元数据匹配
            if genre:
                for style, kws in keywords.items():
                    if any(kw in genre for kw in kws):
                        groups[style].append(ch)
                        assigned = True
                        break

            # 关键词匹配内容
            if not assigned:
                for style, kws in keywords.items():
                    if any(kw in content for kw in kws):
                        groups[style].append(ch)
                        assigned = True
                        break

            if not assigned:
                groups["other"].append(ch)

        # 移除空分组
        return {k: v for k, v in groups.items() if v}

    # ── Instruction-tuning 数据集 ─────────────────

    def build_instruction_tuning_dataset(
        self,
        chapters: list[dict[str, Any]],
        style_focus: bool = True,
        max_samples_per_book: int = 50,
        seq_length: int = 2048,
    ) -> list[dict[str, str]]:
        """生成 Alpaca 格式 instruction-tuning 数据集

        每章前 30% 作为 input（上下文），后 70% 作为 output（续写）。

        Args:
            chapters: 章节列表
            style_focus: 是否在 instruction 中加入风格描述
            max_samples_per_book: 每本书最多样本数
            seq_length: 最大序列长度（字符近似）

        Returns:
            [{"instruction", "input", "output"}, ...]
        """
        dataset: list[dict[str, str]] = []
        book_counter: Counter[str] = Counter()

        for ch in chapters:
            bid = ch.get("book_id", "unknown")
            if book_counter[bid] >= max_samples_per_book:
                continue

            content = ch.get("content", "")
            if len(content) < 150:
                continue

            # 按 30/70 分割
            split_idx = int(len(content) * 0.3)
            context = content[:split_idx].strip()
            continuation = content[split_idx:].strip()

            # 过滤过短输出
            if len(continuation) < 100:
                continue

            # 限制序列长度
            if len(context) + len(continuation) > seq_length:
                context = context[: int(seq_length * 0.3)]
                continuation = continuation[: int(seq_length * 0.7)]

            # 构建 instruction
            if style_focus:
                style_desc = self._infer_style_description(ch)
                instruction = f"续写以下{style_desc}风格的小说章节"
            else:
                instruction = "续写以下风格的小说章节"

            dataset.append(
                {
                    "instruction": instruction,
                    "input": context,
                    "output": continuation,
                }
            )
            book_counter[bid] += 1

        return dataset

    def _infer_style_description(self, chapter: dict[str, Any]) -> str:
        """从章节推断风格描述（中文风格名）"""
        style_map = {
            "xianxia": "仙侠",
            "xuanhuan": "玄幻",
            "dushi": "都市",
            "lishi": "历史",
            "kehuan": "科幻",
            "other": "网络小说",
        }
        genre = str(chapter.get("genre", "")).lower()
        content = chapter.get("content", "")

        for style, kws in DEFAULT_STYLE_KEYWORDS.items():
            if any(kw in genre or kw in content for kw in kws):
                return style_map.get(style, "网络小说")
        return "网络小说"

    # ── 续写数据集 ────────────────────────────────

    def build_continuation_dataset(
        self,
        chapters: list[dict[str, Any]],
        context_ratio: float = 0.3,
    ) -> list[dict[str, Any]]:
        """生成续写训练格式数据集

        Args:
            chapters: 章节列表
            context_ratio: 上下文占比 (0.0-1.0)

        Returns:
            [{"context", "continuation", "book_id", "chapter"}, ...]
        """
        context_ratio = max(0.1, min(0.9, context_ratio))
        dataset: list[dict[str, Any]] = []

        for ch in chapters:
            content = ch.get("content", "")
            if len(content) < 150:
                continue

            split_idx = int(len(content) * context_ratio)
            context = content[:split_idx].strip()
            continuation = content[split_idx:].strip()

            if len(continuation) < 100:
                continue

            dataset.append(
                {
                    "context": context,
                    "continuation": continuation,
                    "book_id": ch.get("book_id", ""),
                    "chapter": ch.get("chapter", 0),
                }
            )

        return dataset

    # ── 保存/加载 ─────────────────────────────────

    def save_dataset(
        self,
        dataset: list[dict[str, Any]],
        filepath: str,
        format: str = "jsonl",
    ) -> str:
        """保存数据集

        Args:
            dataset: 数据集列表
            filepath: 输出文件路径
            format: "jsonl" 或 "json"

        Returns:
            保存的文件路径
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with path.open("w", encoding="utf-8") as f:
                for item in dataset:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
        else:
            path.write_text(
                json.dumps(dataset, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return str(path)

    def load_dataset(self, filepath: str) -> list[dict[str, Any]]:
        """加载数据集（自动识别 JSONL 或 JSON）"""
        path = Path(filepath)
        if not path.exists():
            return []

        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return []

        # 尝试 JSON 数组
        if text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # JSONL 格式
        dataset: list[dict[str, Any]] = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if line:
                try:
                    dataset.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return dataset

    # ── 统计 ──────────────────────────────────────

    def dataset_stats(self, dataset: list[dict[str, Any]]) -> dict[str, Any]:
        """数据集统计

        Returns:
            样本数、总字数、平均输入长度、平均输出长度、风格分布
        """
        if not dataset:
            return {
                "samples": 0,
                "total_chars": 0,
                "avg_input_chars": 0,
                "avg_output_chars": 0,
                "style_distribution": {},
            }

        total_chars = 0
        total_input = 0
        total_output = 0
        style_counter: Counter[str] = Counter()

        for item in dataset:
            # 兼容两种格式
            inp = item.get("input", item.get("context", ""))
            out = item.get("output", item.get("continuation", ""))
            instr = item.get("instruction", "")

            total_input += len(inp) + len(instr)
            total_output += len(out)
            total_chars += len(inp) + len(out) + len(instr)

            # 从 instruction 推断风格
            instr_text = instr + inp
            for style, kws in DEFAULT_STYLE_KEYWORDS.items():
                if any(kw in instr_text for kw in kws):
                    style_counter[style] += 1
                    break
            else:
                style_counter["other"] += 1

        n = len(dataset)
        return {
            "samples": n,
            "total_chars": total_chars,
            "avg_input_chars": round(total_input / n, 1),
            "avg_output_chars": round(total_output / n, 1),
            "style_distribution": dict(style_counter),
        }

    # ── 风格分析 ──────────────────────────────────

    def analyze_style_from_text(self, text: str) -> dict[str, Any]:
        """从文本分析风格特征（纯规则统计方法）

        Returns:
            风格特征字典：句长、对话比例、描写比例、用词偏好、节奏指标
        """
        if not text.strip():
            return {
                "avg_sentence_length": 0,
                "dialogue_ratio": 0.0,
                "description_ratio": 0.0,
                "vocabulary_richness": 0.0,
                "pace_indicator": 0.0,
                "char_count": 0,
                "sentence_count": 0,
                "top_words": [],
            }

        # 句子分割
        sentences = [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]
        sentence_count = max(1, len(sentences))
        char_count = len(text)

        # 平均句长
        avg_sentence_length = round(char_count / sentence_count, 1)

        # 对话比例
        dialogues = _DIALOGUE_PATTERN.findall(text)
        dialogue_chars = sum(len(d) for d in dialogues)
        dialogue_ratio = round(dialogue_chars / max(1, char_count), 3)

        # 描写比例：含描写性用词的句子比例
        desc_sentences = sum(
            1 for s in sentences if any(w in s for w in _DESCRIPTION_WORDS)
        )
        description_ratio = round(desc_sentences / sentence_count, 3)

        # 词汇丰富度（不同字符数 / 总字符数）
        unique_chars = len(set(text.replace("\n", "").replace(" ", "")))
        vocabulary_richness = round(unique_chars / max(1, char_count), 3)

        # 节奏指标：短句比例（句长 < 平均句长的 0.6）
        short_sentences = sum(
            1 for s in sentences if len(s) < avg_sentence_length * 0.6
        )
        pace_indicator = round(short_sentences / sentence_count, 3)

        # 高频用词（排除标点和常见虚词）
        words = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
        stop_words = {
            "的了", "着的", "是的", "不是", "没有", "一个",
            "这个", "那个", "我们", "你们",
        }
        filtered = [w for w in words if w not in stop_words]
        top_words = [w for w, _ in Counter(filtered).most_common(10)]

        return {
            "avg_sentence_length": avg_sentence_length,
            "dialogue_ratio": dialogue_ratio,
            "description_ratio": description_ratio,
            "vocabulary_richness": vocabulary_richness,
            "pace_indicator": pace_indicator,
            "char_count": char_count,
            "sentence_count": sentence_count,
            "top_words": top_words,
        }
