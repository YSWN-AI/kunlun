# mypy: ignore-errors
"""
书名生成器 — 纯模板+规则，离线可用

根据题材、风格、关键词组合生成候选书名。
"""

from __future__ import annotations

import random

from kunlun.toolbox.models import TitleGenerateRequest, TitleResult

# ── 题材前缀/后缀词库 ────────────────────────────────────

_GENRE_PREFIX: dict[str, list[str]] = {
    "玄幻": ["万古", "九天", "苍穹", "神域", "龙", "仙", "魔", "神", "混沌", "洪荒", "太古"],
    "都市": ["极品", "超级", "最强", "绝世", "天才", "至尊", "全能", "重生之", "都市之", "我在"],
    "科幻": ["星际", "银河", "赛博", "机械", "量子", "深空", "星舰", "纪元", "废土", "末世"],
    "历史": ["大明", "大唐", "大宋", "三国", "春秋", "战国", "秦汉", "回到", "重生之", "明末"],
    "言情": ["暖婚", "霸总", "娇妻", "甜宠", "重生", "穿越", "豪门", "总裁", "契约", "闪婚"],
    "悬疑": ["诡秘", "迷雾", "深渊", "暗夜", "真相", "罪案", "推理", "灵异", "惊悚", "禁忌"],
    "游戏": ["网游之", "无限", "玩家", "副本", "领主", "召唤", "全民", "数据", "虚拟", "竞技"],
}

_GENRE_SUFFIX: dict[str, list[str]] = {
    "玄幻": ["天尊", "大帝", "神帝", "剑神", "武帝", "至尊", "战神", "不朽", "永恒", "录", "诀"],
    "都市": ["神医", "兵王", "高手", "赘婿", "大佬", "宗师", "教父", "天王", "霸主", "系统"],
    "科幻": ["文明", "纪元", "战争", "觉醒", "崛起", "编年史", "协议", "边境", "遗产", "回响"],
    "历史": ["风云", "争霸", "天下", "江山", "枭雄", "谋", "帝", "王朝", "遗梦", "春秋"],
    "言情": ["千千岁", "入骨", "心动", "上瘾", "契约", "甜妻", "暖婚", "娇妻", "宠上天", "小娇妻"],
    "悬疑": ["档案", "手记", "谜案", "实录", "事件", "调查", "密档", "卷宗", "异闻", "怪谈"],
    "游戏": ["领主", "纪元", "征途", "传说", "崛起", "之王", "无双", "霸业", "封神", "大陆"],
}

# 风格模板
_STYLE_PATTERNS: dict[str, list[str]] = {
    "番茄": [
        # 直白爽文型
        "{prefix}{keyword}{suffix}",
        "{keyword}：{prefix}{suffix}",
        "开局{keyword}，我{prefix}{suffix}",
        "{prefix}{keyword}，{suffix}",
        # 身份反差型
        "我，{keyword}，{prefix}{suffix}",
        "{keyword}的我，{prefix}{suffix}",
    ],
    "起点": [
        # 大气磅礴型
        "{prefix}{keyword}{suffix}",
        "{keyword}之{suffix}",
        "{prefix}之{keyword}{suffix}",
        "{keyword}：{prefix}{suffix}",
        # 悬念型
        "{keyword}之后",
        "当{keyword}降临",
    ],
    "晋江": [
        # 文艺细腻型
        "{keyword}与{suffix}",
        "{prefix}的{keyword}",
        "{keyword}不晚",
        "致{keyword}",
        "{keyword}未央",
        "{prefix}里的{keyword}",
    ],
}

# 通用兜底词库
_FALLBACK_PREFIX = ["最强", "绝世", "至尊", "万古", "九天", "万界", "混沌", "太古"]
_FALLBACK_SUFFIX = ["传说", "纪元", "之路", "觉醒", "崛起", "无双", "霸业", "封神"]


def _pick_genre_words(genre: str) -> tuple[list[str], list[str]]:
    """获取题材对应的前缀/后缀词库，未知题材使用兜底。"""
    prefix = _GENRE_PREFIX.get(genre)
    suffix = _GENRE_SUFFIX.get(genre)
    if prefix is None:
        # 模糊匹配
        for key, value in _GENRE_PREFIX.items():
            if key in genre or genre in key:
                prefix = value
                suffix = _GENRE_SUFFIX[key]
                break
    if prefix is None:
        prefix = _FALLBACK_PREFIX
        suffix = _FALLBACK_SUFFIX
    return prefix, suffix


def generate_titles(request: TitleGenerateRequest) -> TitleResult:
    """
    生成候选书名。

    策略：
    1. 根据风格选择模板模式
    2. 结合题材词库 + 用户关键词组合
    3. 去重后返回指定数量
    """
    prefix_words, suffix_words = _pick_genre_words(request.genre)
    patterns = _STYLE_PATTERNS.get(request.style, _STYLE_PATTERNS["番茄"])

    keywords = request.keywords if request.keywords else ["逆袭", "强者", "传说"]
    rng = random.Random(hash(request.genre + request.style + ",".join(keywords)) & 0xFFFFFFFF)

    results: list[str] = []
    seen: set[str] = set()
    attempts = 0
    max_attempts = request.count * 20

    while len(results) < request.count and attempts < max_attempts:
        attempts += 1
        pattern = rng.choice(patterns)
        prefix = rng.choice(prefix_words)
        suffix = rng.choice(suffix_words)
        keyword = rng.choice(keywords)

        title = pattern.format(prefix=prefix, keyword=keyword, suffix=suffix)
        # 清理多余字符
        title = title.strip("，：、 ")
        if title and title not in seen and len(title) <= 20:
            seen.add(title)
            results.append(title)

    # 兜底：如果模板生成不足，用简单组合补齐
    while len(results) < request.count:
        title = f"{rng.choice(prefix_words)}{rng.choice(keywords)}{rng.choice(suffix_words)}"
        if title not in seen:
            seen.add(title)
            results.append(title)

    return TitleResult(titles=results[: request.count])
