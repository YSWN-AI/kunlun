"""
市场分析增强模块 — 规则+统计的市场分析框架

与 MarketIntelligence (LLM驱动) 互补，本模块提供纯规则/统计的:
  - 题材热度追踪与预测
  - 竞品分析与机会识别
  - 完读率预测模型 (加权评分)
  - 市场数据持久化
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class GenreHeat:
    """题材热度数据"""

    genre_name: str
    heat_score: float = 0.0  # 0-100
    trend: str = "stable"  # rising / stable / declining
    sample_count: int = 0
    last_updated: str = ""
    keywords: list[str] = field(default_factory=list)
    avg_completion_rate: float = 0.0
    avg_word_count: int = 0
    history: list[dict] = field(default_factory=list)  # 历史热度记录


@dataclass
class Competitor:
    """竞品数据"""

    book_title: str
    author: str
    genre: str
    platform: str
    word_count: int = 0
    chapter_count: int = 0
    rating: float = 0.0
    heat_score: float = 0.0
    update_frequency: str = "daily"  # daily / weekly / irregular
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    target_audience: str = ""


class MarketAnalyzer:
    """规则+统计的市场分析器 (零LLM)"""

    # 完读率预测模型默认权重
    DEFAULT_WEIGHTS: dict[str, float] = {
        "opening_quality": 0.20,
        "pacing": 0.15,
        "pleasure_point_density": 0.15,
        "cliffhanger_density": 0.10,
        "character_depth": 0.10,
        "plot_uniqueness": 0.10,
        "update_frequency": 0.10,
        "dialogue_description_ratio": 0.05,
    }

    # 更新频率评分映射
    UPDATE_FREQ_SCORES: dict[str, float] = {
        "daily": 90.0,
        "bimonthly": 75.0,
        "weekly": 60.0,
        "biweekly": 45.0,
        "monthly": 30.0,
        "irregular": 15.0,
    }

    def __init__(self, data_dir: str = "data/market"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._genre_heat: dict[str, GenreHeat] = {}
        self._competitors: list[Competitor] = []
        self._model_weights: dict[str, float] = dict(self.DEFAULT_WEIGHTS)
        self._calibration_data: list[dict] = []
        self.load_market_data()

    # ─── 题材热度追踪 ──────────────────────────────

    def update_genre_heat(self, genre_name: str, heat_data: dict) -> GenreHeat:
        """更新题材热度数据"""
        existing = self._genre_heat.get(genre_name)
        now = datetime.now().isoformat()

        if existing:
            # 记录历史
            existing.history.append(
                {
                    "date": existing.last_updated or now,
                    "heat_score": existing.heat_score,
                    "trend": existing.trend,
                }
            )
            # 限制历史长度
            if len(existing.history) > 90:
                existing.history = existing.history[-90:]

            existing.heat_score = float(heat_data.get("heat_score", existing.heat_score))
            existing.trend = heat_data.get("trend", existing.trend)
            existing.sample_count = int(heat_data.get("sample_count", existing.sample_count))
            existing.last_updated = now
            if "keywords" in heat_data:
                existing.keywords = list(heat_data["keywords"])
            if "avg_completion_rate" in heat_data:
                existing.avg_completion_rate = float(heat_data["avg_completion_rate"])
            if "avg_word_count" in heat_data:
                existing.avg_word_count = int(heat_data["avg_word_count"])
            return existing

        heat = GenreHeat(
            genre_name=genre_name,
            heat_score=float(heat_data.get("heat_score", 0.0)),
            trend=heat_data.get("trend", "stable"),
            sample_count=int(heat_data.get("sample_count", 0)),
            last_updated=now,
            keywords=list(heat_data.get("keywords", [])),
            avg_completion_rate=float(heat_data.get("avg_completion_rate", 0.0)),
            avg_word_count=int(heat_data.get("avg_word_count", 0)),
        )
        self._genre_heat[genre_name] = heat
        return heat

    def get_genre_heat(self, genre_name: str) -> GenreHeat | None:
        """获取题材热度"""
        return self._genre_heat.get(genre_name)

    def list_hot_genres(self, limit: int = 10, min_heat: float = 0) -> list[GenreHeat]:
        """列出热门题材 (按热度排序)"""
        genres = [g for g in self._genre_heat.values() if g.heat_score >= min_heat]
        genres.sort(key=lambda g: g.heat_score, reverse=True)
        return genres[:limit]

    def get_genre_trend(self, genre_name: str, history_days: int = 30) -> list[dict]:
        """获取题材趋势历史"""
        heat = self._genre_heat.get(genre_name)
        if not heat:
            return []
        return heat.history[-history_days:]

    def predict_genre_heat(self, genre_name: str, days_ahead: int = 7) -> dict:
        """预测题材热度 (简单加权移动平均)"""
        heat = self._genre_heat.get(genre_name)
        if not heat:
            return {"predicted_heat": 0.0, "trend": "unknown", "confidence": "low"}

        # 收集最近的热度数据点 (历史 + 当前)
        recent_heats: list[float] = [h["heat_score"] for h in heat.history[-3:]]
        recent_heats.append(heat.heat_score)

        if len(recent_heats) < 2:
            return {
                "predicted_heat": heat.heat_score,
                "trend": heat.trend,
                "confidence": "low",
                "method": "insufficient_data",
            }

        # 加权移动平均: 最近权重最高
        if len(recent_heats) >= 3:
            predicted = recent_heats[-1] * 0.5 + recent_heats[-2] * 0.3 + recent_heats[-3] * 0.2
        else:
            predicted = recent_heats[-1] * 0.6 + recent_heats[-2] * 0.4

        # 趋势调整
        if len(recent_heats) >= 2:
            delta = recent_heats[-1] - recent_heats[-2]
            # 每天按趋势的10%外推
            predicted += delta * 0.1 * days_ahead

        predicted = max(0.0, min(100.0, predicted))

        # 判断预测趋势
        if predicted > heat.heat_score + 2:
            pred_trend = "rising"
        elif predicted < heat.heat_score - 2:
            pred_trend = "declining"
        else:
            pred_trend = "stable"

        confidence = "high" if len(recent_heats) >= 4 else "medium"

        return {
            "predicted_heat": round(predicted, 2),
            "trend": pred_trend,
            "confidence": confidence,
            "current_heat": heat.heat_score,
            "method": "weighted_moving_average",
            "days_ahead": days_ahead,
        }

    # ─── 竞品分析框架 ──────────────────────────────

    def add_competitor(self, competitor: Competitor) -> None:
        """添加竞品"""
        # 避免重复 (同书名+作者)
        for i, c in enumerate(self._competitors):
            if c.book_title == competitor.book_title and c.author == competitor.author:
                self._competitors[i] = competitor
                return
        self._competitors.append(competitor)

    def get_competitors(
        self, genre: str | None = None, platform: str | None = None, limit: int = 20
    ) -> list[Competitor]:
        """获取竞品列表"""
        result = self._competitors
        if genre:
            result = [c for c in result if c.genre == genre]
        if platform:
            result = [c for c in result if c.platform == platform]
        result.sort(key=lambda c: c.heat_score, reverse=True)
        return result[:limit]

    def analyze_competitor_landscape(self, genre: str) -> dict:
        """分析竞品格局"""
        competitors = [c for c in self._competitors if c.genre == genre]
        if not competitors:
            return {
                "genre": genre,
                "total_competitors": 0,
                "market_concentration": 0.0,
                "top_books": [],
                "market_gaps": [],
                "avg_rating": 0.0,
                "avg_word_count": 0,
            }

        total_heat = sum(c.heat_score for c in competitors)
        # 市场集中度: 前3名热度占比
        sorted_by_heat = sorted(competitors, key=lambda c: c.heat_score, reverse=True)
        top3_heat = sum(c.heat_score for c in sorted_by_heat[:3])
        concentration = top3_heat / total_heat if total_heat > 0 else 0.0

        # 头部作品特征
        top_books = [
            {
                "title": c.book_title,
                "author": c.author,
                "heat_score": c.heat_score,
                "rating": c.rating,
                "word_count": c.word_count,
                "strengths": c.strengths,
                "target_audience": c.target_audience,
            }
            for c in sorted_by_heat[:5]
        ]

        # 识别市场空白: 统计弱点出现频率
        weakness_freq: dict[str, int] = {}
        for c in competitors:
            for w in c.weaknesses:
                weakness_freq[w] = weakness_freq.get(w, 0) + 1

        market_gaps = [
            {
                "gap": w,
                "frequency": count,
                "opportunity": f"多数竞品存在'{w}'短板，可作为差异化切入点",
            }
            for w, count in sorted(weakness_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # 平台分布
        platform_dist: dict[str, int] = {}
        for c in competitors:
            platform_dist[c.platform] = platform_dist.get(c.platform, 0) + 1

        return {
            "genre": genre,
            "total_competitors": len(competitors),
            "market_concentration": round(concentration, 3),
            "concentration_level": (
                "high" if concentration > 0.6 else "medium" if concentration > 0.3 else "low"
            ),
            "top_books": top_books,
            "market_gaps": market_gaps,
            "avg_rating": round(sum(c.rating for c in competitors) / len(competitors), 2),
            "avg_word_count": int(sum(c.word_count for c in competitors) / len(competitors)),
            "platform_distribution": platform_dist,
        }

    def compare_with_competitor(self, your_book_metrics: dict, competitor: Competitor) -> dict:
        """与竞品对比"""
        your_word_count = int(your_book_metrics.get("word_count", 0))
        your_chapter_count = int(your_book_metrics.get("chapter_count", 0))
        your_heat = float(your_book_metrics.get("heat_score", 0.0))
        your_rating = float(your_book_metrics.get("rating", 0.0))
        your_update_freq = your_book_metrics.get("update_frequency", "irregular")
        your_update_score = self.UPDATE_FREQ_SCORES.get(your_update_freq, 15.0)
        comp_update_score = self.UPDATE_FREQ_SCORES.get(competitor.update_frequency, 15.0)

        gaps = {
            "word_count": your_word_count - competitor.word_count,
            "chapter_count": your_chapter_count - competitor.chapter_count,
            "heat_score": round(your_heat - competitor.heat_score, 2),
            "rating": round(your_rating - competitor.rating, 2),
            "update_frequency_score": round(your_update_score - comp_update_score, 2),
        }

        # 综合优势判断
        advantages = []
        disadvantages = []
        if gaps["word_count"] > 0:
            advantages.append(f"字数领先 {gaps['word_count']} 字")
        else:
            disadvantages.append(f"字数落后 {-gaps['word_count']} 字")
        if gaps["heat_score"] > 0:
            advantages.append(f"热度领先 {gaps['heat_score']} 分")
        else:
            disadvantages.append(f"热度落后 {-gaps['heat_score']} 分")
        if gaps["rating"] > 0:
            advantages.append(f"评分领先 {gaps['rating']} 分")
        else:
            disadvantages.append(f"评分落后 {-gaps['rating']} 分")
        if gaps["update_frequency_score"] > 0:
            advantages.append("更新频率更优")
        else:
            disadvantages.append("更新频率不足")

        return {
            "your_book": {
                "word_count": your_word_count,
                "chapter_count": your_chapter_count,
                "heat_score": your_heat,
                "rating": your_rating,
                "update_frequency": your_update_freq,
            },
            "competitor": {
                "book_title": competitor.book_title,
                "author": competitor.author,
                "word_count": competitor.word_count,
                "chapter_count": competitor.chapter_count,
                "heat_score": competitor.heat_score,
                "rating": competitor.rating,
                "update_frequency": competitor.update_frequency,
            },
            "gaps": gaps,
            "advantages": advantages,
            "disadvantages": disadvantages,
            "overall": "领先" if len(advantages) > len(disadvantages) else "落后",
        }

    def identify_opportunities(self, genre: str) -> list[dict]:
        """识别市场机会"""
        opportunities: list[dict] = []
        landscape = self.analyze_competitor_landscape(genre)
        heat = self.get_genre_heat(genre)

        # 机会1: 市场集中度低 → 新进入者机会
        if landscape["market_concentration"] < 0.4:
            conc_pct = landscape["market_concentration"] * 100
            opportunities.append(
                {
                    "type": "low_concentration",
                    "title": "市场集中度低，新作品有突围空间",
                    "description": f"该题材前3名热度占比仅 {conc_pct:.1f}%，市场未被头部垄断",
                    "priority": "high",
                }
            )

        # 机会2: 题材热度上升
        if heat and heat.trend == "rising":
            opportunities.append(
                {
                    "type": "rising_trend",
                    "title": "题材热度上升期",
                    "description": f"当前热度 {heat.heat_score}，趋势上升，适合快速切入",
                    "priority": "high",
                }
            )

        # 机会3: 竞品弱点空白
        opportunities.extend(
            {
                "type": "competitor_weakness",
                "title": f"差异化机会: {gap['gap']}",
                "description": gap["opportunity"],
                "priority": "medium" if gap["frequency"] >= 2 else "low",
            }
            for gap in landscape.get("market_gaps", [])
        )

        # 机会4: 完读率偏低 → 提升空间
        if heat and 0 < heat.avg_completion_rate < 0.4:
            comp_pct = heat.avg_completion_rate * 100
            opportunities.append(
                {
                    "type": "completion_improvement",
                    "title": "题材平均完读率偏低，优质内容可脱颖而出",
                    "description": (
                        f"该题材平均完读率仅 {comp_pct:.1f}%，提升节奏和爽点密度可获得竞争优势"
                    ),
                    "priority": "medium",
                }
            )

        if not opportunities:
            opportunities.append(
                {
                    "type": "general",
                    "title": "常规竞争市场",
                    "description": "需通过内容质量和更新稳定性建立竞争优势",
                    "priority": "low",
                }
            )

        return opportunities

    # ─── 完读率预测模型 ────────────────────────────

    def predict_completion_rate(self, book_metrics: dict) -> dict:
        """预测完读率 (加权评分模型)"""
        w = self._model_weights

        # 各维度评分 (0-100)
        opening = float(book_metrics.get("opening_quality_score", 50.0))
        pacing = float(book_metrics.get("pacing_score", 50.0))
        pleasure = float(book_metrics.get("pleasure_point_density", 50.0))
        cliffhanger = float(book_metrics.get("cliffhanger_density", 50.0))
        character = float(book_metrics.get("character_depth_score", 50.0))
        uniqueness = float(book_metrics.get("plot_uniqueness_score", 50.0))

        # 更新频率映射
        update_freq = book_metrics.get("update_frequency", "irregular")
        update_score = self.UPDATE_FREQ_SCORES.get(update_freq, 15.0)

        # 对话/描写比例评分 (理想范围 30%-50% 对话)
        dialogue_ratio = float(book_metrics.get("dialogue_ratio", 0.4))
        description_ratio = float(book_metrics.get("description_ratio", 0.4))
        if 0.3 <= dialogue_ratio <= 0.5:
            ratio_score = 90.0
        elif 0.2 <= dialogue_ratio <= 0.6:
            ratio_score = 70.0
        else:
            ratio_score = 40.0
        # 描写比例过高扣分
        if description_ratio > 0.6:
            ratio_score -= 15.0
        ratio_score = max(0.0, min(100.0, ratio_score))

        dimension_scores = {
            "opening_quality": opening,
            "pacing": pacing,
            "pleasure_point_density": pleasure,
            "cliffhanger_density": cliffhanger,
            "character_depth": character,
            "plot_uniqueness": uniqueness,
            "update_frequency": update_score,
            "dialogue_description_ratio": ratio_score,
        }

        # 加权平均
        total_weight = sum(w.values())
        weighted_score = sum(dimension_scores[k] * w.get(k, 0) for k in dimension_scores)
        weighted_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # 映射到完读率 0.1-0.95
        completion_rate = 0.1 + (weighted_score / 100.0) * 0.85
        completion_rate = max(0.1, min(0.95, completion_rate))

        # 置信度
        if weighted_score >= 70:
            confidence = "high"
        elif weighted_score >= 40:
            confidence = "medium"
        else:
            confidence = "low"

        # 关键因素: 得分最低的3个维度
        sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1])
        key_factors = [
            {"dimension": dim, "score": round(score, 1), "weight": w.get(dim, 0)}
            for dim, score in sorted_dims[:3]
        ]

        # 改进建议
        recommendations = self._generate_recommendations(sorted_dims, book_metrics)

        return {
            "predicted_completion_rate": round(completion_rate, 4),
            "confidence": confidence,
            "weighted_score": round(weighted_score, 2),
            "dimension_scores": {k: round(v, 1) for k, v in dimension_scores.items()},
            "key_factors": key_factors,
            "recommendations": recommendations,
        }

    def _generate_recommendations(
        self, sorted_dims: list[tuple[str, float]], book_metrics: dict
    ) -> list[str]:
        """针对低分维度生成改进建议"""
        recs: list[str] = []
        advice_map = {
            "opening_quality": (
                "优化黄金三章：开篇300字内抛出核心冲突，"
                "第一章末设置强钩子，前三章完成世界观引入+主角目标确立"
            ),
            "pacing": (
                "调整叙事节奏：每3000字设置一个小高潮，"
                "避免连续超过2章的铺垫期，战斗/对话/描写比例控制在4:3:3"
            ),
            "pleasure_point_density": (
                "提升爽点密度：每章至少1个明确爽点（打脸/升级/揭秘/收获），爽点间隔不超过2000字"
            ),
            "cliffhanger_density": (
                "强化章末钩子：每章结尾使用悬念/反转/危机中断，避免章节平稳收尾"
            ),
            "character_depth": (
                "深化角色塑造：为主角设置明确的内在矛盾和成长弧线，配角赋予独特动机和口头禅"
            ),
            "plot_uniqueness": (
                "增强情节独特性：在经典套路中加入反套路设定，设计至少1个读者难以预测的中期反转"
            ),
            "update_frequency": ("稳定更新频率：建议日更4000字以上，固定更新时间培养读者阅读习惯"),
            "dialogue_description_ratio": (
                "优化对话描写比例：对话占比提升至30%-50%，减少大段环境描写，用动作和对话推进剧情"
            ),
        }

        for dim, score in sorted_dims[:3]:
            if score < 60 and dim in advice_map:
                recs.append(advice_map[dim])

        # 额外建议
        word_count = int(book_metrics.get("word_count", 0))
        if word_count > 0 and word_count < 100000:
            recs.append("作品字数尚少，建议积累到20万字以上再观察完读率数据")

        return recs[:5]

    def calibrate_model(self, actual_data: list[dict]) -> dict:
        """用实际数据校准模型权重 (简单线性调整)"""
        if not actual_data:
            return {"status": "no_data", "adjustments": {}}

        self._calibration_data.extend(actual_data)

        # 计算每个维度的预测误差
        dimension_errors: dict[str, list[float]] = {k: [] for k in self.DEFAULT_WEIGHTS}

        for sample in actual_data:
            prediction = self.predict_completion_rate(sample)
            actual_rate = float(sample.get("actual_completion_rate", 0.5))
            error = prediction["predicted_completion_rate"] - actual_rate

            # 误差归因到低分维度
            for dim, score in prediction["dimension_scores"].items():
                if score < 50:
                    dimension_errors[dim].append(error)

        # 调整权重: 误差大的维度增加权重
        adjustments: dict[str, float] = {}
        for dim, errors in dimension_errors.items():
            if errors:
                avg_error = sum(abs(e) for e in errors) / len(errors)
                # 误差越大，权重提升越多 (最多+0.05)
                adjustment = min(0.05, avg_error * 0.1)
                adjustments[dim] = round(adjustment, 4)
                self._model_weights[dim] = min(0.4, self._model_weights.get(dim, 0) + adjustment)

        # 归一化权重
        total = sum(self._model_weights.values())
        if total > 0:
            self._model_weights = {k: round(v / total, 4) for k, v in self._model_weights.items()}

        return {
            "status": "calibrated",
            "samples_used": len(actual_data),
            "total_samples": len(self._calibration_data),
            "adjustments": adjustments,
            "new_weights": dict(self._model_weights),
        }

    def get_model_weights(self) -> dict:
        """获取当前模型权重"""
        return dict(self._model_weights)

    # ─── 数据持久化 ────────────────────────────────

    def save_market_data(self) -> None:
        """保存市场数据到JSON"""
        genre_file = self.data_dir / "genre_heat.json"
        comp_file = self.data_dir / "competitors.json"

        genre_data = {}
        for name, heat in self._genre_heat.items():
            d = asdict(heat)
            genre_data[name] = d
        genre_file.write_text(
            json.dumps(genre_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        comp_data = [asdict(c) for c in self._competitors]
        comp_file.write_text(json.dumps(comp_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_market_data(self) -> None:
        """加载市场数据"""
        genre_file = self.data_dir / "genre_heat.json"
        comp_file = self.data_dir / "competitors.json"

        if genre_file.exists():
            try:
                data = json.loads(genre_file.read_text(encoding="utf-8"))
                for name, d in data.items():
                    self._genre_heat[name] = GenreHeat(**d)
            except Exception:
                self._genre_heat = {}

        if comp_file.exists():
            try:
                data = json.loads(comp_file.read_text(encoding="utf-8"))
                self._competitors = [Competitor(**d) for d in data]
            except Exception:
                self._competitors = []
