"""
变现系统 — 订阅/打赏/付费章节

支持:
- 订阅计划 (SubscriptionPlan) — 免费/基础/专业/旗舰
- 虚拟货币 (VirtualCurrency) — 平台内流通代币
- 打赏 (Tip) — 读者对作者的单次打赏
- 付费章节 (PaidChapter) — 按章付费解锁
- 收益统计 (RevenueStats) — 日/周/月/总计收益
- 提现 (Withdrawal) — 收益提现到微信/支付宝

用法:
    from kunlun.monetize import MonetizeEngine, SubscriptionTier

    engine = MonetizeEngine()
    engine.create_plan("premium", price=29.9, currency="CNY")
    engine.record_tip("book_001", "reader_001", "author_001", 500)
    stats = engine.get_revenue_stats("author_001")
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class SubscriptionTier(StrEnum):
    """订阅等级"""

    FREE = "free"  # 免费
    BASIC = "basic"  # 基础 (9.9/月)
    PREMIUM = "premium"  # 专业 (29.9/月)
    ULTIMATE = "ultimate"  # 旗舰 (99.9/月)


class TipType(StrEnum):
    """打赏类型"""

    ONE_TIME = "one_time"  # 一次性打赏
    CHAPTER_TIP = "chapter_tip"  # 章末打赏


@dataclass
class SubscriptionPlan:
    """订阅计划"""

    plan_id: str = ""
    tier: SubscriptionTier = SubscriptionTier.FREE
    name: str = ""
    price: float = 0.0
    currency: str = "CNY"
    features: list[str] = field(default_factory=list)
    daily_chapter_limit: int = 0  # 0=无限
    is_active: bool = True


@dataclass
class UserSubscription:
    """用户订阅"""

    user_id: str = ""
    plan_id: str = ""
    tier: SubscriptionTier = SubscriptionTier.FREE
    started_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    auto_renew: bool = False
    is_active: bool = True


@dataclass
class VirtualCurrency:
    """虚拟货币"""

    name: str = "灵石"
    symbol: str = "灵"
    exchange_rate: float = 100.0  # 1 CNY = 100 灵石
    min_tip: int = 10
    max_tip: int = 100000


@dataclass
class TipRecord:
    """打赏记录"""

    id: str = ""
    book_id: str = ""
    from_user: str = ""
    to_user: str = ""
    amount: int = 0
    message: str = ""
    tip_type: TipType = TipType.ONE_TIME
    created_at: float = field(default_factory=time.time)


@dataclass
class PaidChapter:
    """付费章节"""

    book_id: str = ""
    chapter_num: int = 0
    price: int = 0  # 灵石
    unlock_count: int = 0
    revenue: int = 0


@dataclass
class RevenueStats:
    """收益统计"""

    user_id: str = ""
    total_revenue_cny: float = 0.0  # 总收益 (元)
    subscriptions: float = 0.0  # 订阅收入
    tips: float = 0.0  # 打赏收入
    paid_chapters: float = 0.0  # 付费章节收入
    daily: dict[str, float] = field(default_factory=dict)
    monthly: dict[str, float] = field(default_factory=dict)


@dataclass
class Withdrawal:
    """提现记录"""

    id: str = ""
    user_id: str = ""
    amount_cny: float = 0.0
    method: str = "wechat"  # wechat / alipay
    status: str = "pending"  # pending / processing / completed / failed
    created_at: float = field(default_factory=time.time)
    processed_at: float = 0.0


class MonetizeEngine:
    """变现引擎

    核心职责:
    - 订阅计划管理
    - 虚拟货币系统
    - 打赏/付费章节
    - 收益统计
    - 提现管理

    用法:
        engine = MonetizeEngine()
        engine.setup_default_plans()
        stats = engine.get_revenue_stats("author_001")
    """

    def __init__(self, _db_path: str = "data/monetize.db"):
        # 内存缓存
        self._plans: dict[str, SubscriptionPlan] = {}
        self._subscriptions: dict[str, list[UserSubscription]] = {}
        self._tips: list[TipRecord] = []
        self._paid_chapters: dict[str, dict[int, PaidChapter]] = {}
        self._withdrawals: list[Withdrawal] = []
        self._currency = VirtualCurrency()

        # SQLite 持久化
        self._db_path = _db_path
        try:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._init_db()
            self._db_available = True
        except Exception:
            self._db_available = False

    def _get_conn(self) -> sqlite3.Connection:
        """获取 SQLite 连接（WAL 模式）"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    start_date REAL NOT NULL,
                    end_date REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    auto_renew INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id, status);

                CREATE TABLE IF NOT EXISTS tips (
                    id TEXT PRIMARY KEY,
                    book_id TEXT NOT NULL,
                    from_user TEXT NOT NULL,
                    to_user TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    message TEXT DEFAULT '',
                    tip_type TEXT DEFAULT 'one_time',
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tips_to_user ON tips(to_user);
                CREATE INDEX IF NOT EXISTS idx_tips_book ON tips(book_id);

                CREATE TABLE IF NOT EXISTS paid_chapters (
                    book_id TEXT NOT NULL,
                    chapter_num INTEGER NOT NULL,
                    price INTEGER NOT NULL DEFAULT 0,
                    unlock_count INTEGER NOT NULL DEFAULT 0,
                    revenue INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (book_id, chapter_num)
                );

                CREATE TABLE IF NOT EXISTS chapter_unlocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id TEXT NOT NULL,
                    chapter_num INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    unlocked_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chapter_unlocks
                    ON chapter_unlocks(book_id, chapter_num);

                CREATE TABLE IF NOT EXISTS withdrawals (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    method TEXT NOT NULL DEFAULT 'wechat',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id, status);
            """)

    @property
    def currency(self) -> VirtualCurrency:
        return self._currency

    # ── 订阅管理 ────────────────────────────────

    def setup_default_plans(self) -> None:
        """初始化默认订阅计划"""
        defaults = [
            SubscriptionPlan(
                "free", SubscriptionTier.FREE, "免费版", 0.0, "CNY", ["基础写作", "5章/天"], 5
            ),
            SubscriptionPlan(
                "basic",
                SubscriptionTier.BASIC,
                "基础版",
                9.9,
                "CNY",
                ["无限写作", "基础审计", "EPUB导出"],
                0,
            ),
            SubscriptionPlan(
                "premium",
                SubscriptionTier.PREMIUM,
                "专业版",
                29.9,
                "CNY",
                ["无限写作", "53维审计", "去AI化", "多平台发布", "优先支持"],
                0,
            ),
            SubscriptionPlan(
                "ultimate",
                SubscriptionTier.ULTIMATE,
                "旗舰版",
                99.9,
                "CNY",
                ["全部功能", "专属模型", "API访问", "优先支持", "定制开发"],
                0,
            ),
        ]
        for plan in defaults:
            self._plans[plan.plan_id] = plan

    def create_plan(
        self,
        plan_id: str,
        tier: SubscriptionTier,
        name: str,
        price: float,
        currency: str = "CNY",
        features: list[str] | None = None,
        daily_limit: int = 0,
    ) -> SubscriptionPlan:
        """创建自定义订阅计划"""
        plan = SubscriptionPlan(
            plan_id=plan_id,
            tier=tier,
            name=name,
            price=price,
            currency=currency,
            features=features or [],
            daily_chapter_limit=daily_limit,
        )
        self._plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> SubscriptionPlan | None:
        return self._plans.get(plan_id)

    def list_plans(self) -> list[SubscriptionPlan]:
        return list(self._plans.values())

    def subscribe(
        self,
        user_id: str,
        plan_id: str,
        duration_days: int = 30,
        auto_renew: bool = False,
    ) -> UserSubscription | None:
        """用户订阅"""
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        now = time.time()
        end_date = now + duration_days * 86400
        sub = UserSubscription(
            user_id=user_id,
            plan_id=plan_id,
            tier=plan.tier,
            expires_at=end_date,
            auto_renew=auto_renew,
        )
        # 内存缓存
        self._subscriptions.setdefault(user_id, []).append(sub)

        # SQLite 持久化
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    conn.execute(
                        "INSERT INTO subscriptions "
                        "(user_id, plan_id, tier, start_date, "
                        "end_date, status, auto_renew) "
                        "VALUES (?, ?, ?, ?, ?, 'active', ?)",
                        (user_id, plan_id, plan.tier.value, now, end_date, int(auto_renew)),
                    )
            except Exception:
                pass
        return sub

    def get_active_subscription(self, user_id: str) -> UserSubscription | None:
        """获取用户当前活跃订阅"""
        now = time.time()
        # 优先从数据库读取
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    row = conn.execute(
                        "SELECT * FROM subscriptions "
                        "WHERE user_id = ? AND status = 'active' "
                        "AND (end_date > ? OR end_date = 0) "
                        "ORDER BY id DESC LIMIT 1",
                        (user_id, now),
                    ).fetchone()
                    if row:
                        return UserSubscription(
                            user_id=row["user_id"],
                            plan_id=row["plan_id"],
                            tier=SubscriptionTier(row["tier"]),
                            started_at=row["start_date"],
                            expires_at=row["end_date"],
                            auto_renew=bool(row["auto_renew"]),
                            is_active=True,
                        )
            except Exception:
                pass
        # fallback: 内存缓存
        subs = self._subscriptions.get(user_id, [])
        for sub in reversed(subs):
            if sub.is_active and (sub.expires_at == 0 or sub.expires_at > now):
                return sub
        return None

    def cancel_subscription(self, user_id: str) -> bool:
        """取消订阅"""
        # 更新数据库
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    cursor = conn.execute(
                        "UPDATE subscriptions SET status = 'cancelled', auto_renew = 0 "
                        "WHERE user_id = ? AND status = 'active'",
                        (user_id,),
                    )
                    if cursor.rowcount == 0:
                        return False
            except Exception:
                pass
        # 更新内存缓存
        sub = self.get_active_subscription(user_id)
        if sub:
            sub.is_active = False
            sub.auto_renew = False
            return True
        return False

    # ── 打赏系统 ──────────────────────────────────

    def tip(
        self,
        book_id: str,
        from_user: str,
        to_user: str,
        amount: int,
        message: str = "",
        tip_type: TipType = TipType.ONE_TIME,
    ) -> TipRecord | None:
        """打赏"""
        if amount < self._currency.min_tip or amount > self._currency.max_tip:
            return None

        import uuid

        record = TipRecord(
            id=str(uuid.uuid4())[:12],
            book_id=book_id,
            from_user=from_user,
            to_user=to_user,
            amount=amount,
            message=message,
            tip_type=tip_type,
        )
        # 内存缓存
        self._tips.append(record)

        # SQLite 持久化
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    conn.execute(
                        "INSERT INTO tips (id, book_id, from_user, "
                        "to_user, amount, message, tip_type, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            record.id,
                            book_id,
                            from_user,
                            to_user,
                            amount,
                            message,
                            tip_type.value,
                            record.created_at,
                        ),
                    )
            except Exception:
                pass
        return record

    def get_tips_for_book(self, book_id: str) -> list[TipRecord]:
        return [t for t in self._tips if t.book_id == book_id]

    def get_tips_for_author(self, author_id: str) -> list[TipRecord]:
        # 优先从数据库读取
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    rows = conn.execute(
                        "SELECT * FROM tips WHERE to_user = ? ORDER BY created_at DESC",
                        (author_id,),
                    ).fetchall()
                    return [
                        TipRecord(
                            id=row["id"],
                            book_id=row["book_id"],
                            from_user=row["from_user"],
                            to_user=row["to_user"],
                            amount=row["amount"],
                            message=row["message"],
                            tip_type=TipType(row["tip_type"]),
                            created_at=row["created_at"],
                        )
                        for row in rows
                    ]
            except Exception:
                pass
        # fallback: 内存缓存
        return [t for t in self._tips if t.to_user == author_id]

    def get_tip_total(self, author_id: str) -> int:
        # 优先从数据库读取
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    row = conn.execute(
                        "SELECT COALESCE(SUM(amount), 0) AS total FROM tips WHERE to_user = ?",
                        (author_id,),
                    ).fetchone()
                    if row:
                        return row["total"]
            except Exception:
                pass
        # fallback: 内存缓存
        return sum(t.amount for t in self.get_tips_for_author(author_id))

    # ── 付费章节 ──────────────────────────────────

    def set_paid_chapter(
        self,
        book_id: str,
        chapter_num: int,
        price: int,
    ) -> PaidChapter:
        """设置付费章节"""
        chapter = PaidChapter(book_id=book_id, chapter_num=chapter_num, price=price)
        # 内存缓存
        self._paid_chapters.setdefault(book_id, {})[chapter_num] = chapter

        # SQLite 持久化
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO paid_chapters "
                        "(book_id, chapter_num, price, unlock_count, "
                        "revenue, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (book_id, chapter_num, price, 0, 0, time.time()),
                    )
            except Exception:
                pass
        return chapter

    def unlock_chapter(self, book_id: str, chapter_num: int, user_id: str = "") -> bool:
        """解锁付费章节"""
        chapter = self._paid_chapters.get(book_id, {}).get(chapter_num)

        # 更新数据库
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    book_chapters = conn.execute(
                        "SELECT price FROM paid_chapters WHERE book_id = ? AND chapter_num = ?",
                        (book_id, chapter_num),
                    ).fetchone()
                    if not book_chapters:
                        return False
                    price = book_chapters["price"]
                    conn.execute(
                        "UPDATE paid_chapters SET unlock_count = unlock_count + 1, "
                        "revenue = revenue + ? "
                        "WHERE book_id = ? AND chapter_num = ?",
                        (price, book_id, chapter_num),
                    )
                    conn.execute(
                        "INSERT INTO chapter_unlocks (book_id, chapter_num, user_id, unlocked_at) "
                        "VALUES (?, ?, ?, ?)",
                        (book_id, chapter_num, user_id, time.time()),
                    )
                    # 同步更新内存缓存
                    if chapter:
                        chapter.unlock_count += 1
                        chapter.revenue += price
                    return True
            except Exception:
                pass
        # fallback: 内存缓存
        if not chapter:
            return False
        chapter.unlock_count += 1
        chapter.revenue += chapter.price
        return True

    def get_paid_chapters(self, book_id: str) -> list[PaidChapter]:
        return list(self._paid_chapters.get(book_id, {}).values())

    # ── 收益统计 ──────────────────────────────────

    def get_revenue_stats(self, user_id: str) -> RevenueStats:
        """获取用户收益统计"""
        stats = RevenueStats(user_id=user_id)

        # 优先从数据库聚合查询
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    # 订阅收入
                    sub_row = conn.execute(
                        "SELECT COALESCE(SUM(p.price), 0) AS total "
                        "FROM subscriptions s "
                        "JOIN (SELECT 'free' AS plan_id, 0.0 AS price "
                        "      UNION ALL SELECT 'basic', 9.9 "
                        "      UNION ALL SELECT 'premium', 29.9 "
                        "      UNION ALL SELECT 'ultimate', 99.9) p "
                        "ON s.plan_id = p.plan_id "
                        "WHERE s.user_id = ? AND s.tier != 'free'",
                        (user_id,),
                    ).fetchone()
                    if sub_row:
                        stats.subscriptions = sub_row["total"]

                    # 打赏收入
                    tip_row = conn.execute(
                        "SELECT COALESCE(SUM(amount), 0) AS total FROM tips WHERE to_user = ?",
                        (user_id,),
                    ).fetchone()
                    if tip_row:
                        stats.tips = tip_row["total"] / self._currency.exchange_rate

                    # 付费章节收入 (按作者关联的书籍)
                    pc_row = conn.execute(
                        "SELECT COALESCE(SUM(revenue), 0) AS total FROM paid_chapters",
                    ).fetchone()
                    if pc_row:
                        stats.paid_chapters = pc_row["total"] / self._currency.exchange_rate

                    stats.total_revenue_cny = round(
                        stats.subscriptions + stats.tips + stats.paid_chapters, 2
                    )
                    return stats
            except Exception:
                pass

        # fallback: 内存缓存
        subs = self._subscriptions.get(user_id, [])
        for sub in subs:
            if sub.tier != SubscriptionTier.FREE:
                plan = self._plans.get(sub.plan_id)
                if plan:
                    stats.subscriptions += plan.price

        currency_amount = sum(t.amount for t in self.get_tips_for_author(user_id))
        stats.tips = currency_amount / self._currency.exchange_rate

        for chapters in self._paid_chapters.values():
            for ch in chapters.values():
                if ch.revenue > 0:
                    stats.paid_chapters += ch.revenue / self._currency.exchange_rate

        stats.total_revenue_cny = stats.subscriptions + stats.tips + stats.paid_chapters
        return stats

    # ── 提现 ──────────────────────────────────────

    def request_withdrawal(
        self,
        user_id: str,
        amount_cny: float,
        method: str = "wechat",
    ) -> Withdrawal | None:
        """申请提现"""
        stats = self.get_revenue_stats(user_id)
        if amount_cny > stats.total_revenue_cny:
            return None

        import uuid

        now = time.time()
        withdrawal = Withdrawal(
            id=str(uuid.uuid4())[:12],
            user_id=user_id,
            amount_cny=amount_cny,
            method=method,
            created_at=now,
        )
        # 内存缓存
        self._withdrawals.append(withdrawal)

        # SQLite 持久化
        if self._db_available:
            try:
                with self._get_conn() as conn:
                    conn.execute(
                        "INSERT INTO withdrawals (id, user_id, amount, method, status, created_at) "
                        "VALUES (?, ?, ?, ?, 'pending', ?)",
                        (withdrawal.id, user_id, amount_cny, method, now),
                    )
            except Exception:
                pass
        return withdrawal

    def get_withdrawals(self, user_id: str) -> list[Withdrawal]:
        return [w for w in self._withdrawals if w.user_id == user_id]

    # ── 统计 ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "plans": len(self._plans),
            "active_subscriptions": sum(
                1 for subs in self._subscriptions.values() for s in subs if s.is_active
            ),
            "total_tips": len(self._tips),
            "paid_chapters": sum(len(v) for v in self._paid_chapters.values()),
            "withdrawals": len(self._withdrawals),
            "currency": {
                "name": self._currency.name,
                "symbol": self._currency.symbol,
                "rate": self._currency.exchange_rate,
            },
        }


# 全局单例
monetize_engine = MonetizeEngine()
