"""
昆仑创作引擎 — 状态文件导出器

对标 AI_NovelGenerator 的 global_summary.txt / character_state.txt / plot_arcs.txt 状态管理。
将昆仑知识图谱中的创作状态导出为可读文本文件，供外部工具和人工审阅使用。

导出文件:
  - global_summary.txt      — 全书概览
  - world_setting.txt        — 世界观设定
  - character_state.txt      — 角色状态
  - plot_arcs.txt            — 情节弧线
  - chapter_outlines.txt     — 章节大纲
  - foreshadowing.txt        — 伏笔追踪
  - consistency_report.txt   — 一致性报告

数据源优先级: KG (Neo4j) → SQLite 图降级 → 文件系统 (truth/snapshots) → 空标注

Author: 昆仑创作引擎
"""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 导出目标目录
# ══════════════════════════════════════════════════════

DEFAULT_EXPORT_BASE = settings.PROJECT_ROOT / "output"
UNAVAILABLE_MARKER = "[数据不可用]"


def _state_dir(book_id: str) -> Path:
    """获取导出目标目录，自动创建。"""
    d = DEFAULT_EXPORT_BASE / book_id / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _header(title: str) -> str:
    """生成带时间戳的文件头。"""
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"# {'=' * 60}\n# {title}\n# 生成时间: {ts}\n# 昆仑创作引擎 — 状态导出\n# {'=' * 60}\n"


def _section(title: str) -> str:
    return f"\n{'─' * 60}\n  {title}\n{'─' * 60}\n"


def _subsection(title: str) -> str:
    return f"\n  ▸ {title}\n  {'─' * 50}\n"


# ══════════════════════════════════════════════════════
# 数据采集 — 多层降级
# ══════════════════════════════════════════════════════


def _get_kg_snapshot(book_id: str) -> dict | None:
    """从 KG 快照管理器获取最新快照（dict 形式）。"""
    try:
        from kunlun.kg.snapshot import snapshot_manager

        snap = snapshot_manager.get_latest(book_id)
        if snap:
            return snap.to_context_dict()
    except Exception as e:
        logger.debug(f"[StateExporter] KG 快照获取失败: {e}")
    return None


def _get_kg_raw_entities(_book_id: str) -> dict | None:
    """从 KG 直接查询实体（Neo4j 或 SQLite 图降级）。"""
    try:
        from kunlun.kg.client import kg_client

        result: dict[str, list] = {}
        entity_types = ["Character", "Item", "Location", "Skill", "Event", "Organization"]
        for etype in entity_types:
            try:
                rows = kg_client.query_cypher(f"MATCH (e:{etype}) RETURN e LIMIT 200")
                result[etype] = rows
            except Exception:
                result[etype] = []
        # 伏笔
        try:
            result["Foreshadowing_planted"] = kg_client.query_cypher(
                "MATCH (f:Foreshadowing) WHERE f.status = 'planted' RETURN f ORDER BY f.priority"
            )
            result["Foreshadowing_revealed"] = kg_client.query_cypher(
                "MATCH (f:Foreshadowing) WHERE f.status = 'revealed' "
                "RETURN f ORDER BY f.revealedChapter DESC LIMIT 50"
            )
            result["Foreshadowing_overdue"] = kg_client.query_cypher(
                "MATCH (f:Foreshadowing) WHERE f.status = 'planted' "
                "AND f.expectedRevealChapter <= toInteger($ch) RETURN f",
                {"ch": 9999},
            )
        except Exception:
            result["Foreshadowing_planted"] = []
            result["Foreshadowing_revealed"] = []
            result["Foreshadowing_overdue"] = []
        # 关系
        try:
            result["Relationships"] = kg_client.query_cypher(
                "MATCH (a)-[r]->(b) RETURN a.name AS start, "
                "type(r) AS type, b.name AS end, r LIMIT 200"
            )
        except Exception:
            result["Relationships"] = []
        return result
    except Exception as e:
        logger.debug(f"[StateExporter] KG 原始查询失败: {e}")
    return None


def _get_truth_data() -> dict:
    """从 truth 文件读取数据。"""
    truth_dir = settings.DATA_DIR / "truth"
    data: dict = {}
    files = [
        "character_matrix.json",
        "chapter_summaries.json",
        "current_state.json",
        "pending_hooks.json",
        "subplot_board.json",
        "emotional_arcs.json",
        "book_rules.json",
    ]
    for fname in files:
        fp = truth_dir / fname
        if fp.exists():
            try:
                data[fname] = json.loads(fp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data[fname] = None
        else:
            data[fname] = None
    return data


def _get_story_files(book_id: str) -> dict[str, str]:
    """从 data/story/{book_id}/ 读取控制文档。"""
    story_dir = settings.DATA_DIR / "story" / book_id
    files = ["author_intent.md", "current_focus.md", "book_rules.md", "story_bible.md"]
    result: dict[str, str] = {}
    for fname in files:
        fp = story_dir / fname
        if fp.exists():
            try:
                result[fname] = fp.read_text(encoding="utf-8")
            except OSError:
                result[fname] = ""
        else:
            result[fname] = ""
    return result


def _get_world_settings(book_id: str) -> list[dict]:
    """从文件系统读取世界观设定。"""
    fp = settings.DATA_DIR / "worlds" / book_id / "settings.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return []


def _get_character_states(book_id: str) -> dict:
    """从 state machine 文件读取角色动态状态。"""
    fp = settings.DATA_DIR / "state" / book_id / "state_machine.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _get_snapshot_files(book_id: str) -> list[dict]:
    """从文件系统读取所有快照 JSON。"""
    snapshots_dir = settings.DATA_DIR / "snapshots"
    results: list[dict] = []
    for fp in sorted(snapshots_dir.glob(f"{book_id}_ch*.json"), key=lambda p: p.stat().st_mtime):
        with contextlib.suppress(OSError, json.JSONDecodeError):
            results.append(json.loads(fp.read_text(encoding="utf-8")))
    return results


def _get_version_index(book_id: str) -> dict | None:
    """从版本管理读取章节版本信息。"""
    fp = settings.DATA_DIR / "versions" / book_id / "index.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════
# 导出函数
# ══════════════════════════════════════════════════════


def _export_global_summary(
    book_id: str, story: dict[str, str], truth: dict, snapshots: list[dict]
) -> str:
    """生成 global_summary.txt"""
    lines = [_header("全书概览 — Global Summary")]

    lines.append(_section("基本信息"))
    lines.append(f"  书籍ID:     {book_id}")

    # 书名 — 从 author_intent 提取或使用 book_id
    intent = story.get("author_intent.md", "")
    title = book_id
    genre = ""
    if intent:
        for line in intent.splitlines():
            line_s = line.strip()
            if line_s.startswith("# "):
                title = line_s[2:].strip()
            elif line_s.startswith("类型") or line_s.startswith("题材"):
                genre = (
                    line_s.split("：", 1)[-1].strip()
                    if "：" in line_s
                    else line_s.split(":", 1)[-1].strip()
                )

    lines.append(f"  书名:       {title}")
    lines.append(f"  题材/类型:  {genre or UNAVAILABLE_MARKER}")

    # 字数统计
    total_words = 0
    total_chapters = 0
    if snapshots:
        total_chapters = max(s.get("chapter", 0) for s in snapshots)
    else:
        ch_data = truth.get("chapter_summaries.json", {}) or {}
        total_chapters = ch_data.get("total_chapters", 0)

    # 尝试从版本管理获取字数
    ver = _get_version_index(book_id)
    if ver:
        for ch_data in ver.values():
            if isinstance(ch_data, dict):
                total_words += ch_data.get("word_count", 0)

    lines.append(f"  总章节数:   {total_chapters}")
    lines.append(f"  总字数:     {total_words if total_words else UNAVAILABLE_MARKER}")

    lines.append(_section("核心梗概"))
    synopsis_text = ""
    if intent:
        synopsis_text = intent
    elif story.get("story_bible.md", ""):
        synopsis_text = story["story_bible.md"]
    lines.append(f"  {synopsis_text[:2000] if synopsis_text else UNAVAILABLE_MARKER}")

    # 创作焦点
    lines.append(_section("近期创作焦点"))
    focus = story.get("current_focus.md", "")
    lines.append(f"  {focus[:1000] if focus else UNAVAILABLE_MARKER}")

    # 作品规则
    lines.append(_section("作品规则"))
    rules = story.get("book_rules.md", "")
    if not rules:
        br = truth.get("book_rules.json", {}) or {}
        hard = br.get("hard_constraints", [])
        soft = br.get("soft_guidelines", [])
        if hard or soft:
            rules = "硬性约束:\n" + "\n".join(f"  - {r}" for r in hard)
            rules += "\n\n软性指南:\n" + "\n".join(f"  - {r}" for r in soft)
    lines.append(f"  {rules[:1500] if rules else UNAVAILABLE_MARKER}")

    return "\n".join(lines)


def _export_world_setting(book_id: str, world_settings: list[dict], kg_data: dict | None) -> str:  # noqa: PLR0912
    """生成 world_setting.txt"""
    lines = [_header("世界观设定 — World Setting")]

    dimension_labels: dict[str, str] = {
        "power_system": "力量体系",
        "geography": "地理空间",
        "culture_rules": "文化规则",
        "economy": "经济体系",
        "magic_tech": "魔法/科技",
        "creature_species": "生物种族",
        "item_artifact": "道具神器",
    }

    # 从文件系统获取
    if world_settings:
        lines.append(_section("世界观维度"))
        for dim_key, dim_label in dimension_labels.items():
            entries = [ws for ws in world_settings if ws.get("dimension") == dim_key]
            if entries:
                lines.append(_subsection(dim_label))
                for entry in entries:
                    desc = entry.get("description", "")
                    if desc:
                        lines.append(f"    {entry.get('name', '?')}: {desc}")
                    rules = entry.get("rules", [])
                    if rules:
                        lines.extend(f"      规则: {r}" for r in rules)
                    refs = entry.get("references", [])
                    if refs:
                        lines.append(f"      关联: {', '.join(refs)}")
    else:
        lines.append(_section("世界观维度"))
        lines.append(f"  {UNAVAILABLE_MARKER}")

    # 从 KG 补充位置/组织数据
    if kg_data:
        lines.append(_section("KG — 地点"))
        locs = kg_data.get("Location", [])
        if locs:
            for loc in locs[:30]:
                node = loc.get("e", loc.get("l", {}))
                name = node.get("name", "?")
                desc = node.get("description", "")
                lines.append(f"  - {name}" + (f": {desc}" if desc else ""))
        else:
            lines.append(f"  {UNAVAILABLE_MARKER}")

        lines.append(_section("KG — 组织/势力"))
        orgs = kg_data.get("Organization", [])
        if orgs:
            for org in orgs[:20]:
                node = org.get("e", org.get("o", {}))
                name = node.get("name", "?")
                desc = node.get("description", "")
                lines.append(f"  - {name}" + (f": {desc}" if desc else ""))
        else:
            lines.append(f"  {UNAVAILABLE_MARKER}")

        lines.append(_section("KG — 技能/能力"))
        skills = kg_data.get("Skill", [])
        if skills:
            for sk in skills[:20]:
                node = sk.get("e", sk.get("s", {}))
                name = node.get("name", "?")
                desc = node.get("description", "")
                lines.append(f"  - {name}" + (f": {desc}" if desc else ""))
        else:
            lines.append(f"  {UNAVAILABLE_MARKER}")

        lines.append(_section("KG — 神器/道具"))
        items = kg_data.get("Item", [])
        if items:
            for it in items[:20]:
                node = it.get("e", it.get("i", {}))
                name = node.get("name", "?")
                desc = node.get("description", "")
                lines.append(f"  - {name}" + (f": {desc}" if desc else ""))
        else:
            lines.append(f"  {UNAVAILABLE_MARKER}")

    # 从 story_bible 补充
    story_dir = settings.DATA_DIR / "story" / book_id
    bible_fp = story_dir / "story_bible.md"
    if bible_fp.exists():
        try:
            bible = bible_fp.read_text(encoding="utf-8")
            lines.append(_section("世界观圣经 (story_bible.md)"))
            lines.append(f"  {bible[:2000]}")
        except OSError:
            pass

    return "\n".join(lines)


def _export_character_state(  # noqa: PLR0912
    _book_id: str, kg_data: dict | None, char_states: dict, truth: dict
) -> str:
    """生成 character_state.txt"""
    lines = [_header("角色状态 — Character State")]

    # 从 KG 获取角色档案
    kg_chars = kg_data.get("Character", []) if kg_data else []
    char_matrix = truth.get("character_matrix.json", {}) or {}
    matrix_chars = char_matrix.get("characters", {})

    lines.append(_section("角色列表"))

    if kg_chars:
        for c in kg_chars[:50]:
            node = c.get("e", c.get("c", {}))
            name = node.get("name", "?")
            role = node.get("role", "")
            traits = node.get("traits", "")
            arc_type = node.get("arcType", "")
            lines.append(f"\n  【{name}】")
            if role:
                lines.append(f"    定位: {role}")
            if traits:
                lines.append(f"    特征: {traits}")
            if arc_type:
                lines.append(f"    弧线类型: {arc_type}")

            # 动态状态
            uid = node.get("uid", node.get("character_uid", ""))
            if uid and uid in char_states:
                st = char_states[uid]
                lines.append(f"    当前情绪: {st.get('current_emotion', '?')}")
                lines.append(f"    心理状态: {st.get('psychological_state', '?')}")
                lines.append(
                    f"    弧光阶段: {st.get('arc_phase', '?')} ({st.get('arc_progress', 0)})"
                )
                lines.append(f"    能力等级: {st.get('current_ability_level', '?')}")
                lines.append(f"    位置: {st.get('current_location_uid', '?')}")
                if st.get("surface_motivation"):
                    lines.append(f"    表层动机: {st['surface_motivation']}")
                if st.get("deep_need"):
                    lines.append(f"    深层需求: {st['deep_need']}")

                # 关系
                rels = st.get("relationships", {})
                if rels:
                    lines.append("    关系亲密度:")
                    for target, affinity in rels.items():
                        lines.append(f"      → {target}: {affinity:.2f}")

                # 持有物品
                held = st.get("held_items", [])
                if held:
                    lines.append(f"    持有物品: {', '.join(held[:10])}")

                # 能力成长日志
                growth = st.get("ability_growth_log", [])
                if growth:
                    lines.append("    能力成长:")
                    lines.extend(
                        f"      第{g.get('chapter', '?')}章: {g.get('event', '?')}"
                        for g in growth[-5:]
                    )
            else:
                lines.append(f"    状态: {UNAVAILABLE_MARKER}")

    elif matrix_chars:
        for cid, cdata in matrix_chars.items():
            lines.append(f"\n  【{cdata.get('name', cid)}】")
            for key in ("role", "personality", "background", "abilities"):
                val = cdata.get(key, "")
                if val:
                    if isinstance(val, list):
                        lines.append(f"    {key}: {', '.join(val)}")
                    else:
                        lines.append(f"    {key}: {val}")
    else:
        lines.append(f"  {UNAVAILABLE_MARKER}")

    # 角色关系图（KG）
    if kg_data:
        rels = kg_data.get("Relationships", [])
        if rels:
            lines.append(_section("角色关系图"))
            seen = set()
            for r in rels[:100]:
                start = r.get("start", r.get("a.name", "?"))
                end = r.get("end", r.get("b.name", "?"))
                rtype = r.get("type", r.get("type(r)", "?"))
                key = (start, end, rtype)
                if key not in seen:
                    seen.add(key)
                    lines.append(f"  {start} ──[{rtype}]──▶ {end}")

    # 互动记录
    interactions = char_matrix.get("interactions", [])
    if interactions:
        lines.append(_section("角色互动记录"))
        lines.extend(
            f"  第{inter.get('chapter', '?')}章: {inter.get('description', '?')}"
            for inter in interactions[-20:]
        )

    return "\n".join(lines)


def _export_plot_arcs(
    _book_id: str, kg_data: dict | None, truth: dict, _snapshots: list[dict]
) -> str:
    """生成 plot_arcs.txt"""
    lines = [_header("情节弧线 — Plot Arcs")]

    # 主线/支线
    lines.append(_section("叙事线程概览"))

    subplot_board = truth.get("subplot_board.json", {}) or {}
    subplots = subplot_board.get("subplots", [])
    if subplots:
        for sp in subplots:
            lines.append(f"\n  ▣ {sp.get('name', '?')}")
            lines.append(f"    类型: {sp.get('type', '?')}")
            lines.append(f"    状态: {sp.get('status', '?')}")
            lines.append(f"    进度: {sp.get('progress', '?')}")
            desc = sp.get("description", "")
            if desc:
                lines.append(f"    描述: {desc}")
    else:
        lines.append(f"  {UNAVAILABLE_MARKER}")

    # 停滞警告
    stag_warnings = subplot_board.get("stagnation_warnings", [])
    if stag_warnings:
        lines.append(_section("停滞警告"))
        lines.extend(f"  ⚠ {w}" for w in stag_warnings)

    # KG 事件因果链
    if kg_data:
        events = kg_data.get("Event", [])
        if events:
            lines.append(_section("KG — 事件因果链"))
            for ev in events[:50]:
                node = ev.get("e", ev.get("ev", {}))
                name = node.get("name", "?")
                ch = node.get("chapter", node.get("chapter_num", "?"))
                cause = node.get("cause", "")
                effect = node.get("effect", "")
                decision = node.get("decision", "")
                tension = node.get("tension_level", "")
                lines.append(f"\n  ◆ 第{ch}章: {name}")
                if cause:
                    lines.append(f"    因: {cause}")
                if effect:
                    lines.append(f"    果: {effect}")
                if decision:
                    lines.append(f"    决: {decision}")
                if tension:
                    lines.append(f"    张力: {tension}/5")
    else:
        lines.append(_section("因果链"))
        lines.append(f"  {UNAVAILABLE_MARKER}")

    # 情感弧线
    emotional = truth.get("emotional_arcs.json", {}) or {}
    arcs = emotional.get("arcs", {})
    if arcs:
        lines.append(_section("情感弧线"))
        for arc_id, arc_data in arcs.items():
            lines.append(f"\n  ~ {arc_id}")
            for k, v in arc_data.items():
                lines.append(f"    {k}: {v}")
    else:
        lines.append(_section("情感弧线"))
        lines.append(f"  {UNAVAILABLE_MARKER}")

    return "\n".join(lines)


def _export_chapter_outlines(
    book_id: str, truth: dict, snapshots: list[dict], _kg_data: dict | None
) -> str:
    """生成 chapter_outlines.txt"""
    lines = [_header("章节大纲 — Chapter Outlines")]

    ch_data = truth.get("chapter_summaries.json", {}) or {}
    chapters = ch_data.get("chapters", {})
    total = ch_data.get("total_chapters", 0)

    lines.append(_section("章节摘要链"))
    lines.append(f"  总章节数: {total}")

    if chapters:
        for ch_num in sorted(chapters.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
            ch_info = chapters[ch_num]
            if isinstance(ch_info, dict):
                lines.append(f"\n  ── 第{ch_num}章 ──")
                title = ch_info.get("title", "")
                summary = ch_info.get("summary", "")
                word_count = ch_info.get("word_count", "")
                key_events = ch_info.get("key_events", [])
                if title:
                    lines.append(f"  标题: {title}")
                if summary:
                    lines.append(f"  摘要: {summary}")
                if word_count:
                    lines.append(f"  字数: {word_count}")
                if key_events:
                    lines.append(f"  关键事件: {', '.join(key_events)}")
    elif snapshots:
        # 从快照推断章节
        for snap in sorted(snapshots, key=lambda s: s.get("chapter", 0)):
            ch = snap.get("chapter", 0)
            entity_cnt = snap.get("entity_count", 0)
            lines.append(f"\n  ── 第{ch}章快照 ──")
            lines.append(f"  实体数: {entity_cnt}")
            lines.append(f"  关系数: {snap.get('relationship_count', 0)}")
            planted = snap.get("foreshadowing_planted", [])
            if planted:
                lines.append(f"  活跃伏笔: {len(planted)}")
    else:
        lines.append(f"\n  {UNAVAILABLE_MARKER}")

    # 版本管理信息
    ver = _get_version_index(book_id)
    if ver:
        lines.append(_section("版本记录"))
        for ch_key, ch_info in ver.items():
            if isinstance(ch_info, dict):
                lines.append(
                    f"  第{ch_key}章: {ch_info.get('word_count', '?')}字 | "
                    f"评分: {ch_info.get('audit_score', '?')}"
                )

    return "\n".join(lines)


def _export_foreshadowing(_book_id: str, kg_data: dict | None, truth: dict) -> str:  # noqa: PLR0912
    """生成 foreshadowing.txt"""
    lines = [_header("伏笔追踪 — Foreshadowing")]

    # 从 KG
    planted = []
    revealed = []
    overdue = []
    if kg_data:
        planted = kg_data.get("Foreshadowing_planted", [])
        revealed = kg_data.get("Foreshadowing_revealed", [])
        overdue = kg_data.get("Foreshadowing_overdue", [])

    if planted or revealed or overdue:
        lines.append(_section("已埋设伏笔"))
        if planted:
            for f in planted[:50]:
                node = f.get("f", f.get("e", {}))
                lines.append(
                    f"  ◈ {node.get('name', '?')}"
                    f"  [优先级: {node.get('priority', '?')}]"
                    f"  (第{node.get('plantedChapter', node.get('planted_chapter', '?'))}章埋设"
                    f" → 预计第{node.get('expectedRevealChapter', node.get('target_chapter', '?'))}"
                    f"章揭示)"
                )
                desc = node.get("description", "")
                if desc:
                    lines.append(f"     {desc}")
        else:
            lines.append("  无")

        lines.append(_section("已回收伏笔"))
        if revealed:
            for f in revealed[:30]:
                node = f.get("f", f.get("e", {}))
                lines.append(
                    f"  ✓ {node.get('name', '?')}"
                    f"  (第{node.get('revealedChapter', node.get('recycled_at', '?'))}章回收)"
                )
        else:
            lines.append("  无")

        lines.append(_section("逾期未回收"))
        if overdue:
            for f in overdue[:20]:
                node = f.get("f", f.get("e", {}))
                lines.append(
                    f"  ⚠ {node.get('name', '?')}"
                    f"  (应于第{node.get('expectedRevealChapter', '?')}章揭示)"
                )
        else:
            lines.append("  无")

        lines.append(_section("统计"))
        lines.append(f"  已埋设: {len(planted)}")
        lines.append(f"  已回收: {len(revealed)}")
        lines.append(f"  逾期:   {len(overdue)}")
        if planted:
            recycle_rate = len(revealed) / max(len(planted) + len(revealed), 1) * 100
            lines.append(f"  回收率: {recycle_rate:.1f}%")
    else:
        # 从 truth pending_hooks 获取
        hooks_data = truth.get("pending_hooks.json", {}) or {}
        all_hooks = hooks_data.get("hooks", [])
        resolved = hooks_data.get("resolved", [])
        overdue_hooks = hooks_data.get("overdue", [])

        if all_hooks or resolved:
            lines.append(_section("已埋设伏笔"))
            if all_hooks:
                lines.extend(
                    f"  ◈ {h.get('name', h.get('description', '?'))}  (第{h.get('chapter', '?')}章)"
                    for h in all_hooks[:50]
                )
            else:
                lines.append("  无")

            lines.append(_section("已回收伏笔"))
            if resolved:
                lines.extend(f"  ✓ {h.get('name', '?')}" for h in resolved[:30])
            else:
                lines.append("  无")

            if overdue_hooks:
                lines.append(_section("逾期未回收"))
                lines.extend(f"  ⚠ {h.get('name', '?')}" for h in overdue_hooks[:20])

            lines.append(_section("统计"))
            lines.append(f"  已埋设: {len(all_hooks)}")
            lines.append(f"  已回收: {len(resolved)}")
            lines.append(f"  逾期:   {len(overdue_hooks)}")
        else:
            lines.append(f"  {UNAVAILABLE_MARKER}")

    return "\n".join(lines)


def _export_consistency_report(
    book_id: str, kg_data: dict | None, world_settings: list[dict]
) -> str:
    """生成 consistency_report.txt"""
    lines = [_header("一致性报告 — Consistency Report")]

    lines.append(_section("世界观一致性"))

    if world_settings:
        # 检查是否有实际设定的维度
        active_dims = [ws for ws in world_settings if ws.get("description") or ws.get("rules")]
        if active_dims:
            for ws in world_settings:
                name = ws.get("name", "?")
                dim = ws.get("dimension", "?")
                desc = ws.get("description", "")
                rules = ws.get("rules", [])
                status = "✓ 已设定" if (desc or rules) else "○ 未设定"
                lines.append(f"  [{dim}] {name}: {status}")
                if rules:
                    lines.extend(f"    规则: {r}" for r in rules)
        else:
            lines.append("  所有维度均未设定具体内容")
    else:
        lines.append("  未找到世界观设定文件")

    lines.append(_section("KG — 实体统计"))
    if kg_data:
        for etype in ["Character", "Item", "Location", "Skill", "Event", "Organization"]:
            entities = kg_data.get(etype, [])
            lines.append(f"  {etype}: {len(entities)} 个")
        rels = kg_data.get("Relationships", [])
        lines.append(f"  Relationships: {len(rels)} 条")
        lines.append(f"  Foreshadowing (planted): {len(kg_data.get('Foreshadowing_planted', []))}")
        lines.append(
            f"  Foreshadowing (revealed): {len(kg_data.get('Foreshadowing_revealed', []))}"
        )
    else:
        lines.append(f"  {UNAVAILABLE_MARKER}")

    lines.append(_section("数据完整性"))
    checks: list[tuple[str, bool]] = []
    checks.append(("KG 快照", _get_kg_snapshot(book_id) is not None))
    checks.append(("KG 直连 (Neo4j/SQLite)", kg_data is not None))
    checks.append(("世界观设定", len(world_settings) > 0))
    checks.append(("Truth 文件", (settings.DATA_DIR / "truth").exists()))
    checks.append(("角色状态机", len(_get_character_states(book_id)) > 0))
    checks.append(
        ("章节快照文件", any((settings.DATA_DIR / "snapshots").glob(f"{book_id}_ch*.json")))
    )
    checks.append(("控制文档", (settings.DATA_DIR / "story" / book_id).exists()))

    for label, ok in checks:
        icon = "✓" if ok else "✗"
        lines.append(f"  {icon} {label}")

    all_ok = all(ok for _, ok in checks)
    lines.append(f"\n  综合状态: {'✓ 所有数据源正常' if all_ok else '⚠ 部分数据源不可用'}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════
# 公开 API
# ══════════════════════════════════════════════════════


def _collect_data(book_id: str) -> dict:
    """收集所有可用数据源（多层降级）。"""
    data: dict = {}

    # KG 快照
    data["kg_snapshot"] = _get_kg_snapshot(book_id)
    # KG 直连（Neo4j → SQLite 图降级自动处理）
    data["kg_raw"] = _get_kg_raw_entities(book_id)
    # Truth 文件
    data["truth"] = _get_truth_data()
    # 控制文档
    data["story"] = _get_story_files(book_id)
    # 世界观设定
    data["world_settings"] = _get_world_settings(book_id)
    # 角色状态
    data["character_states"] = _get_character_states(book_id)
    # 快照文件
    data["snapshots"] = _get_snapshot_files(book_id)

    return data


def export_state(book_id: str, output_dir: str | None = None) -> dict[str, Path]:
    """导出单个书籍的完整状态文件。

    Args:
        book_id: 书籍 ID
        output_dir: 自定义输出目录（默认 output/{book_id}/state/）

    Returns:
        {文件名: 文件路径} 映射
    """
    target = Path(output_dir) if output_dir else _state_dir(book_id)
    target.mkdir(parents=True, exist_ok=True)

    logger.info(f"[StateExporter] 开始导出: {book_id} → {target}")

    data = _collect_data(book_id)

    exporters: dict[str, callable] = {
        "global_summary.txt": _export_global_summary,
        "world_setting.txt": _export_world_setting,
        "character_state.txt": _export_character_state,
        "plot_arcs.txt": _export_plot_arcs,
        "chapter_outlines.txt": _export_chapter_outlines,
        "foreshadowing.txt": _export_foreshadowing,
        "consistency_report.txt": _export_consistency_report,
    }

    # 各导出函数需要的参数
    export_args: dict[str, dict] = {
        "global_summary.txt": {
            "story": data["story"],
            "truth": data["truth"],
            "snapshots": data["snapshots"],
        },
        "world_setting.txt": {
            "kg_data": data["kg_raw"],
            "world_settings": data["world_settings"],
        },
        "character_state.txt": {
            "kg_data": data["kg_raw"],
            "char_states": data["character_states"],
            "truth": data["truth"],
        },
        "plot_arcs.txt": {
            "kg_data": data["kg_raw"],
            "truth": data["truth"],
            "snapshots": data["snapshots"],
        },
        "chapter_outlines.txt": {
            "truth": data["truth"],
            "snapshots": data["snapshots"],
            "kg_data": data["kg_raw"],
        },
        "foreshadowing.txt": {
            "kg_data": data["kg_raw"],
            "truth": data["truth"],
        },
        "consistency_report.txt": {
            "kg_data": data["kg_raw"],
            "world_settings": data["world_settings"],
        },
    }

    results: dict[str, Path] = {}
    for fname, func in exporters.items():
        args = export_args[fname]
        try:
            content = func(book_id, **args)
            fp = target / fname
            fp.write_text(content, encoding="utf-8")
            results[fname] = fp
            logger.info(f"[StateExporter]   ✓ {fname}")
        except Exception as e:
            logger.error(f"[StateExporter]   ✗ {fname}: {e}")

    logger.info(f"[StateExporter] 导出完成: {len(results)}/{len(exporters)} 个文件")
    return results


def export_all(output_dir: str | None = None) -> dict[str, dict[str, Path]]:
    """导出所有书籍的状态文件。

    Returns:
        {book_id: {文件名: 文件路径}}
    """
    results: dict[str, dict[str, Path]] = {}

    # 扫描所有可能的书籍来源
    book_ids: set[str] = set()

    # data/books/
    books_dir = settings.DATA_DIR / "books"
    if books_dir.exists():
        book_ids.update(d.name for d in books_dir.iterdir() if d.is_dir())

    # data/story/
    story_dir = settings.DATA_DIR / "story"
    if story_dir.exists():
        book_ids.update(d.name for d in story_dir.iterdir() if d.is_dir())

    # data/snapshots/ 中提取 book_id
    snapshots_dir = settings.DATA_DIR / "snapshots"
    if snapshots_dir.exists():
        for fp in snapshots_dir.glob("*_ch*.json"):
            stem = fp.stem
            # 格式: {book_id}_ch{N}_{hash}
            parts = stem.rsplit("_ch", 1)
            if parts:
                book_ids.add(parts[0])

    # data/worlds/
    worlds_dir = settings.DATA_DIR / "worlds"
    if worlds_dir.exists():
        book_ids.update(d.name for d in worlds_dir.iterdir() if d.is_dir())

    # data/state/
    state_dir = settings.DATA_DIR / "state"
    if state_dir.exists():
        book_ids.update(d.name for d in state_dir.iterdir() if d.is_dir())

    if not book_ids:
        logger.warning("[StateExporter] 未找到任何书籍")
        return results

    logger.info(f"[StateExporter] 发现 {len(book_ids)} 本书籍: {book_ids}")

    for bid in sorted(book_ids):
        if bid:  # 排除空 book_id
            try:
                results[bid] = export_state(bid, output_dir)
            except Exception as e:
                logger.error(f"[StateExporter] 导出 {bid} 失败: {e}")

    return results
