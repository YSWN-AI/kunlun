"""
昆仑创作引擎 — StyleEngineer (风格润色)

职责: 执行去AI味后处理 + 语感优化 + 风格一致性校验
输入: 通过的正文草稿
输出: 发布就绪的润色版本
"""

from __future__ import annotations

import re

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent


class StyleEngineer(BaseAgent):
    """
    风格润色师

    能力边界:
    - ✅ 句式CV调整 (长短交错)
    - ✅ AI味连词替换/删除
    - ✅ 段落节奏优化 (不均匀段落)
    - ✅ 句首多样性增强
    - ✅ 风格标签一致性检查
    - ❌ 不改情节/角色/信息
    - ❌ 不做内容审计 (那是Auditor的活)
    """

    agent_name = "style_engineer"
    capabilities = [
        "sentence_variation",
        "conjunction_replacement",
        "paragraph_rhythm",
        "opening_diversity",
        "style_consistency",
    ]

    # AI感的标志性连词 → 自然替换
    CONJUNCTION_REPLACEMENTS = {
        "然而": ["但", "可是", "不过", "偏偏", ""],
        "此外": ["另外", "还有", "再加上", ""],
        "因此": ["所以", "于是", "就这样", ""],
        "综上所述": [""],  # 直接删除
        "首先": ["先", ""],
        "其次": ["然后", "接着", ""],
        "总而言之": [""],
        "不可否认": ["说实话", "确实", ""],
        "值得注意的是": ["注意", "关键是", ""],
    }

    # 句首词库，用于增强多样性（随机替换句首）
    OPENING_VARIANTS = {
        "他": ["那人", "此人", ""],
        "她": ["那女子", "她身形一转，", ""],
        "它": ["那东西", "那物", ""],
        "这": ["眼前的", "眼下的", ""],
        "那": ["远处的", "那边的", ""],
        "但": ["可是", "不过", ""],
        "可": ["然而", "偏偏", ""],
        "而": ["同时", "另一方面，", ""],
        "于": ["在", "就在", ""],
        "因为": ["由于", "因着", ""],
        "所以": ["因此", "于是", ""],
        "如果": ["倘若", "假如", ""],
        "虽然": ["尽管", "虽说", ""],
        "当": ["在", "正当", ""],
        "每当": ["每次", "每逢", ""],
        "在": ["就在", "正值", ""],
        "经过": ["历经", "几经", ""],
    }

    # 高频人名动词模式检测
    NAME_VERB_PATTERN = re.compile(
        r"([\u4e00-\u9fff]{2,4})(挥|打|走|看|说|想|站|坐|转|点|笑|叹|摇|拍|拉|推|踢|跃|跳|飞|冲|闪|躲|避)"
    )

    async def execute(self, task: dict) -> dict:
        """润色正文"""
        draft = task.get("draft", "")
        kg_snapshot_id = task.get("kg_snapshot_id", "")

        if not draft or len(draft) < 50:
            return {"success": True, "polished_draft": draft, "changes": 0}

        polished = draft

        # 1. AI味连词替换
        polished, conj_changes = self._replace_ai_conjunctions(polished)

        # 2. 句首多样性增强
        polished, opening_changes = self._enhance_openings(polished)

        # 3. 段落节奏调整
        polished, para_changes = self._adjust_paragraph_rhythm(polished)

        # 4. 文本精炼（去高频套路词、过度描写、冗余表达）
        try:
            from kunlun.style.refiner import text_refiner

            polished, refiner_report = text_refiner.refine(polished)
            refiner_changes = refiner_report.total_fixes
            if refiner_changes > 0:
                logger.info(
                    f"TextRefiner: {refiner_changes}处精炼 (节省{refiner_report.savings}字)"
                )
        except Exception:
            refiner_changes = 0

        # 5. 去AI痕迹后处理（统计指纹优化 + AI模式检测替换）
        humanize_changes = 0
        try:
            from kunlun.humanize.engine import humanize_engine as _he

            chapter_type = task.get("chapter_type", "normal")
            h_result = await _he.humanize(
                polished,
                strategy="minimal",
                chapter_type=chapter_type,
            )
            polished = h_result.humanized
            humanize_changes = h_result.markers_before - h_result.markers_after
            if humanize_changes > 0:
                logger.info(
                    f"HumanizeEngine: {humanize_changes}处AI痕迹移除 "
                    f"(得分 {h_result.ai_score_before:.2f}→{h_result.ai_score_after:.2f})"
                )
        except Exception as e:
            logger.warning(f"HumanizeEngine 后处理跳过: {e}")

        total_changes = (
            conj_changes + opening_changes + para_changes + refiner_changes + humanize_changes
        )

        logger.info(f"StyleEngineer: {total_changes}处润色完成")

        return {
            "success": True,
            "polished_draft": polished,
            "changes": total_changes,
            "details": {
                "conjunction_replacements": conj_changes,
                "opening_enhancements": opening_changes,
                "paragraph_adjustments": para_changes,
                "humanize_changes": humanize_changes,
            },
            "kg_snapshot_id": kg_snapshot_id,
        }

    def _replace_ai_conjunctions(self, text: str) -> tuple[str, int]:
        """替换AI感连词（逐个替换确保计数精确）"""
        import random
        import re as _re

        changes = 0
        result = text

        for target, alternatives in self.CONJUNCTION_REPLACEMENTS.items():
            if target not in result:
                continue
            replacement = random.choice(alternatives)
            # 逐个替换以精确计数（替代全部替换后统一计数的方式）
            actual_count = 0
            parts = result.split(target)
            if len(parts) > 1:
                actual_count = len(parts) - 1
                result = replacement.join(parts)
            changes += actual_count

        # 清理替换为空字符串后残留的前导逗号/空格
        # 例: "其次，我们" → 替换后 ""+"，我们" → 清理为 "我们"
        if changes > 0 and "" in [
            alt for alts in self.CONJUNCTION_REPLACEMENTS.values() for alt in alts
        ]:
            result = _re.sub(r"^[，,、。]+\s*", "", result)
            result = _re.sub(r"([。！？])[，,、]+\s*", r"\1 ", result)

        return result, changes

    def _enhance_openings(self, text: str) -> tuple[str, int]:
        """句首多样性增强 — 扩展覆盖 + 自适应阈值 + 实体代词检测"""
        import random

        sentences = re.split(r"(?<=[。！？!?\n])", text)
        if len(sentences) < 3:
            return text, 0

        # 自适应阈值：短文20%，长文25%
        char_count = len(text)
        threshold = 0.25 if char_count > 1500 else 0.20
        changes = 0

        # 统计各句首模式的命中数
        opening_counts = {}
        for s in sentences:
            stripped = s.strip()
            if not stripped:
                continue
            for opener in self.OPENING_VARIANTS:
                if stripped.startswith(opener):
                    opening_counts[opener] = opening_counts.get(opener, 0) + 1
                    break

        # 对超过阈值的句首进行替换
        for opener, count in opening_counts.items():
            if count > len(sentences) * threshold and opener in self.OPENING_VARIANTS:
                variants = self.OPENING_VARIANTS[opener]
                for i, s in enumerate(sentences):
                    stripped = s.strip()
                    if stripped.startswith(opener) and random.random() < 0.35 and len(stripped) > 4:
                        replacement = random.choice(variants)
                        if replacement == "":
                            # 省略主语：去掉句首词
                            sentences[i] = s.replace(opener, "", 1).lstrip("，,")
                        else:
                            sentences[i] = s.replace(opener, replacement, 1)
                        changes += 1

        # 实体代词检测：提取文本中的人物名，替换重复的"人名+动词"模式
        text_after = "".join(sentences)
        name_verb_matches = self.NAME_VERB_PATTERN.findall(text)
        if name_verb_matches:
            name_counts = {}
            for name, _verb in name_verb_matches:
                name_counts[name] = name_counts.get(name, 0) + 1

            for name, count in name_counts.items():
                if count > 3 and len(name) >= 2:
                    # 该名字出现超过3次，替换部分实例（每个替换独立计数）
                    replacement_map = {
                        2: ["他", "她"],
                        3: ["这人", "此人"],
                        4: ["他", "她", ""],
                    }
                    opts = replacement_map.get(len(name), ["他", "她"])
                    pattern = re.escape(name)
                    # 使用闭包捕获 opts，逐个替换精确计数
                    name_count = [0]

                    def _replace_name(m, _opts=opts, _cnt=name_count):
                        import random as _r

                        if _r.random() < 0.3:
                            _cnt[0] += 1
                            return _r.choice(_opts)
                        return m.group(0)

                    text_after = re.sub(pattern, _replace_name, text_after, count=count)
                    changes += name_count[0]

        if changes > 0:
            return text_after, changes
        return text, 0

    def _adjust_paragraph_rhythm(self, text: str) -> tuple[str, int]:
        """段落节奏调整 — 倒序遍历避免索引漂移"""
        paragraphs = text.split("\n\n")
        if len(paragraphs) < 3:
            return text, 0

        changes = 0
        # 倒序遍历：避免合并修改后索引漂移
        for i in range(len(paragraphs) - 2, -1, -1):
            p1, p2 = paragraphs[i], paragraphs[i + 1]
            if abs(len(p1) - len(p2)) < 50 and len(p1) > 100:
                merged = p1 + "\n" + p2
                mid = len(merged) // 2
                # 找断点（优先句号/感叹号/问号，再逗号/分号）
                split_idx = merged.rfind("。", mid - 80, mid + 80)
                if split_idx <= 0:
                    for sep in ["！", "？", "……", "；"]:
                        split_idx = merged.rfind(sep, mid - 80, mid + 80)
                        if split_idx > 0:
                            break
                if split_idx <= 0:
                    split_idx = merged.rfind("，", mid - 80, mid + 80)
                if split_idx > 0 and split_idx < len(merged) - 1:
                    paragraphs[i] = merged[: split_idx + 1]
                    paragraphs[i + 1] = merged[split_idx + 1 :]
                    changes += 1

        return "\n\n".join(paragraphs), changes

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        if msg.msg_type == "POLISH":
            result = await self.execute(msg.payload)
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="POLISH_DONE",
                payload={
                    "polished_draft": result["polished_draft"],
                    "changes": result["changes"],
                    "details": result.get("details", {}),
                },
                correlation_id=msg.correlation_id,
                kg_snapshot_id=msg.kg_snapshot_id,
            )
        return None
