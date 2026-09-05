"""
Post-reflect learning loop — compares raw draft vs corrected output,
extracts rule deltas, and writes Patches to SKILL.md.

Architecture: Operates as a non-blocking post-pipeline hook. Results
are accumulated into skills/learned_patches.md for human review.
"""

from __future__ import annotations

import difflib
import re
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger


def _find_skills_dir() -> Path | None:
    """Locate the skills directory using config or fallback."""
    try:
        from kunlun.config import settings

        skills_dir = settings.SKILLS_DIR
        if skills_dir.exists():
            return skills_dir
    except Exception as e:
        logger.debug(f"[Reflector] 从 config 加载 skills_dir 失败: {e}")

    # fallback: locate relative to this file
    candidate = Path(__file__).resolve().parent.parent.parent / "skills"
    if candidate.exists():
        return candidate
    return None


def _extract_additions(old_text: str, new_text: str) -> list[str]:
    """Extract lines that were added or substantially changed."""
    diff = difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        lineterm="",
        n=0,
    )
    return [
        line[1:].strip() for line in diff if line.startswith("+") and not line.startswith("+++")
    ]


def _load_existing_patches(skills_dir: Path) -> set[tuple[str, str]]:
    """加载已有的规则 patch，返回 (pattern, suggestion) 集合用于去重"""
    existing: set[tuple[str, str]] = set()
    patch_file = skills_dir / "learned_patches.md"
    if not patch_file.exists():
        return existing
    try:
        content = patch_file.read_text(encoding="utf-8")
        # 提取已有规则：**规则**: `pattern` → suggestion
        for m in re.finditer(r"\*\*规则\*\*:\s*`([^`]+)`\s*→\s*(.+)", content):
            existing.add((m.group(1).strip(), m.group(2).strip()))
    except Exception as e:
        logger.debug(f"规则 patch 文件解析失败: {e}")
    return existing


def _extract_rule_from_diff(diff_lines: list[str]) -> list[dict]:
    """
    从 diff 中提取写作规则。检测连接词、句式、段落结构等模式。
    扩展版：新增句式多样性、对话标记、描写密度等检测器。
    """
    rules = []
    detectors = [
        # 连接词优化
        (r"但[^是]", "避免单独使用「但」开头，建议「但是/然而」"),
        (r"^突然[^间地]", "「突然」加「间/地」更自然"),
        (r"^然后", "减少「然后」堆砌，用动作承接"),
        (r"^于是", "「于是」适合因果，不是万能衔接"),
        (r"却[^又]", "「却」后补「又」增强语气"),
        # 句式多样性
        (
            r"(?:^|。)(?:他|她|它)(?:是|在|有|说|走|看|想|知道)",
            "避免过多「他/她+动词」句式，丰富主语和句式结构",
        ),
        (r"。\s*[^，。！？…、]{1,3}(?:说|道|问|喊)", "对话标记前应有恰当修饰，避免生硬"),
        (r"(?:好像|仿佛|似乎|犹如).*?(?:好像|仿佛|似乎|犹如)", "同一句内避免重复比喻词"),
        # 段落结构
        (r"^\s*(?:首先|其次|然后|接着|最后|此外|另外|再者)", "列举式写作过于模板化，改为自然过渡"),
        (r"(?:。|！|？)\s*(?:但是|然而|可是|不过)(?:，|,)", "转折词前应有明确标点分隔"),
        # AI 味检测
        (r"总的来说|综上所述|总而言之|简而言之", "总结性套话有AI味，改为自然收尾"),
        (r"不仅.*?而且.*?还", "「不仅…而且…还」三重递进过于工整"),
        (r"一方面.*?另一方面", "「一方面…另一方面」过于书面化"),
        # 描写密度
        (
            r"(?:黑|白|红|蓝|绿|黄|紫|金|银)(?:色|的)",
            "颜色描写后应有具体意象，如「血红色」而非「红色」",
        ),
    ]

    for line in diff_lines:
        for pattern, suggestion in detectors:
            if re.search(pattern, line):
                rules.append(
                    {
                        "pattern": pattern,
                        "suggestion": suggestion,
                        "example": line[:100],
                    }
                )

    return rules


def _format_patch_md(patches: list[dict], pipeline_id: str) -> str:
    """Format extracted rules as a markdown patch block."""
    if not patches:
        return ""

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = f"\n\n<!-- REFLECT_PATCH pipeline={pipeline_id} time={now} -->\n"
    header += "## Learned Rules\n\n"

    rules_text = ""
    seen = set()
    for p in patches:
        key = (p["pattern"], p["suggestion"])
        if key in seen:
            continue
        seen.add(key)
        rules_text += f"- **规则**: `{p['pattern']}` → {p['suggestion']}\n"
        rules_text += f"  - 示例: _{p['example']}_\n"

    if not rules_text:
        return ""

    footer = "<!-- /REFLECT_PATCH -->\n"
    return header + rules_text + footer


def post_reflect_hook(
    raw_draft: str,
    corrected_draft: str,
    pipeline_id: str = "",
    skills_dir: Path | None = None,
) -> dict:
    """
    Hook invoked after publish step to compare writer raw output
    vs final corrected output and generate SKILL.md patches.

    Returns:
        dict with patches_generated, new_rules, diffs_count, patch_md
    """
    if not raw_draft or not corrected_draft:
        return {
            "patches_generated": 0,
            "new_rules": 0,
            "diffs_count": 0,
            "message": "empty input, skipped",
        }

    # Only reflect if texts differ meaningfully (> 5% change)
    diff_ratio = difflib.SequenceMatcher(None, raw_draft, corrected_draft).ratio()
    if diff_ratio > 0.95:
        return {
            "patches_generated": 0,
            "new_rules": 0,
            "diffs_count": 0,
            "similarity": round(diff_ratio, 4),
            "message": "similarity > 95%, no meaningful diff to learn",
        }

    additions = _extract_additions(raw_draft, corrected_draft)
    rules = _extract_rule_from_diff(additions)

    if not rules:
        return {
            "patches_generated": 0,
            "new_rules": 0,
            "diffs_count": len(additions),
            "similarity": round(diff_ratio, 4),
            "message": "no recognizable writing rules extracted",
        }

    sd = skills_dir or _find_skills_dir()
    if sd is None:
        logger.warning("[Reflector] skills/ 目录未找到，无法写入 Patch")
        return {
            "patches_generated": 0,
            "new_rules": 0,
            "diffs_count": len(additions),
            "message": "skills dir not found",
        }

    # 加载已有规则，去重
    existing_patches = _load_existing_patches(sd)
    new_rules = [r for r in rules if (r["pattern"], r["suggestion"]) not in existing_patches]
    if not new_rules:
        return {
            "patches_generated": 0,
            "new_rules": 0,
            "diffs_count": len(additions),
            "similarity": round(diff_ratio, 4),
            "message": f"所有 {len(rules)} 条规则已存在，跳过",
        }

    patch_md = _format_patch_md(new_rules, pipeline_id)
    if not patch_md:
        return {
            "patches_generated": 0,
            "new_rules": 0,
            "diffs_count": len(additions),
            "similarity": round(diff_ratio, 4),
            "message": "formatted patch is empty",
        }

    # 追加写入 learned_patches.md（带去重保护）
    patch_file = sd / "learned_patches.md"
    try:
        with patch_file.open("a", encoding="utf-8") as f:
            f.write(patch_md)
        logger.info(
            f"[Reflector] {len(new_rules)} 条新规则已写入 {patch_file} "
            f"(跳过 {len(rules) - len(new_rules)} 条重复)"
        )
    except Exception as e:
        logger.error(f"[Reflector] 写入 Patch 失败: {e}")
        return {
            "patches_generated": 0,
            "new_rules": 0,
            "diffs_count": len(additions),
            "message": f"write error: {e}",
        }

    return {
        "patches_generated": 1,
        "new_rules": len(rules),
        "diffs_count": len(additions),
        "similarity": round(diff_ratio, 4),
        "patch_file": str(patch_file),
        "message": f"wrote {len(rules)} rules to learned_patches.md",
    }
