"""推荐历史、反馈和并发控制查询。

Repository 只负责数据访问和结果形状，不负责候选过滤、评分或推荐理由；
Application Service 负责业务流程、事务提交和异常边界。Repository 通过
selectinload/joinedload 一次加载推荐详情，避免 API 映射阶段触发 N+1 查询。
用户锁使用 PostgreSQL advisory transaction lock，保护同一用户的推荐生成
临界区；锁的生命周期由调用方事务决定，不是永久用户锁。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Recommendation,
    RecommendationFeedback,
    RecommendationItem,
)
from app.services.recommendation_types import FeedbackEvent, HistoryEvent


RECOMMENDATION_DETAIL_OPTIONS = (
    # items → fruit/nutrition/seasons/feedback 全部批量预加载，避免 N+1。
    # 这是加载策略，不改变历史/反馈的业务统计口径。
    selectinload(Recommendation.items).selectinload(
        RecommendationItem.feedback
    ),
)


def acquire_user_lock(session: Session, user_id: int) -> None:
    """在当前事务内锁住一个用户的推荐生成流程。

    ``user_id`` 是 advisory lock key；锁会在当前数据库事务结束时释放，
    因此必须在读取 active、计算刷新序号和插入新推荐之前调用。该锁不替代
    active partial unique index，而是减少并发检查-插入竞态。
    """
    session.execute(select(func.pg_advisory_xact_lock(user_id)))


def get_active_recommendation(
    session: Session,
    user_id: int,
    recommendation_date: date,
    *,
    for_update: bool = False,
) -> Recommendation | None:
    """读取当天 active 记录；刷新时可附带行锁。

    只返回当天 ``status='active'`` 的一组；返回 ``None`` 表示当天尚未有
    active 推荐，不表示数据库查询失败。``for_update`` 只用于刷新状态
    转换，普通今日读取不会额外锁行。
    """
    statement = (
        select(Recommendation)
        .where(
            Recommendation.user_id == user_id,
            Recommendation.recommendation_date == recommendation_date,
            Recommendation.status == "active",
        )
        .options(*RECOMMENDATION_DETAIL_OPTIONS)
    )
    if for_update:
        statement = statement.with_for_update()
    return session.execute(statement).scalar_one_or_none()


def get_recommendation(
    session: Session,
    recommendation_id: int,
) -> Recommendation | None:
    """按 ID 读取完整推荐详情；``None`` 表示记录不存在。"""
    statement = (
        select(Recommendation)
        .where(Recommendation.id == recommendation_id)
        .options(*RECOMMENDATION_DETAIL_OPTIONS)
    )
    return session.execute(statement).scalar_one_or_none()


def list_history(
    session: Session,
    user_id: int,
    *,
    limit: int,
) -> list[Recommendation]:
    """按日期、刷新序号和 ID 倒序读取用户历史。

    查询不筛除 ``replaced``，所以历史能展示当天多次刷新以及最终 active；
    返回是一条条 Recommendation，而不是按天或按水果聚合。``limit`` 作用
    于推荐组数量，详情关系由预加载选项补齐。
    """
    statement = (
        select(Recommendation)
        .where(Recommendation.user_id == user_id)
        .options(*RECOMMENDATION_DETAIL_OPTIONS)
        .order_by(
            Recommendation.recommendation_date.desc(),
            Recommendation.refresh_number.desc(),
            Recommendation.id.desc(),
        )
        .limit(limit)
    )
    return list(session.execute(statement).scalars())


def next_refresh_number(
    session: Session,
    user_id: int,
    recommendation_date: date,
) -> int:
    """计算当天下一刷新序号，调用方需在用户锁内使用。

    初始值为 0，之后取当天所有记录（包括 replaced）的最大值加一；锁是
    这个 max+1 过程避免并发重复的前提，唯一约束则提供最终数据库保护。
    """
    statement = select(
        func.coalesce(func.max(Recommendation.refresh_number), -1) + 1
    ).where(
        Recommendation.user_id == user_id,
        Recommendation.recommendation_date == recommendation_date,
    )
    return int(session.execute(statement).scalar_one())


def recent_fruit_ids(
    session: Session,
    user_id: int,
    *,
    since: date,
    until: date | None = None,
    limit: int = 30,
) -> tuple[int, ...]:
    """提取近期出现过的水果，供历史多样性分使用。

    日期边界是包含式 ``since <= recommendation_date <= until``；结果按
    日期、刷新序号和 item rank 倒序，``dict.fromkeys`` 去重并保留首次
    出现顺序。查询当前未筛除 replaced，因此主动换组也会计入“近期见过”。
    """
    conditions = [
        Recommendation.user_id == user_id,
        Recommendation.recommendation_date >= since,
    ]
    if until is not None:
        conditions.append(Recommendation.recommendation_date <= until)
    statement = (
        select(RecommendationItem.fruit_id)
        .join(Recommendation)
        .where(*conditions)
        .order_by(
            Recommendation.recommendation_date.desc(),
            Recommendation.refresh_number.desc(),
            RecommendationItem.rank,
        )
        .limit(limit)
    )
    ordered = session.execute(statement).scalars()
    return tuple(dict.fromkeys(ordered))


def feedback_by_fruit(
    session: Session,
    user_id: int,
    *,
    since: datetime,
    until: datetime | None = None,
    limit: int = 100,
) -> dict[int, tuple[str, ...]]:
    """按水果聚合近期反馈类型，兼容旧算法上下文。

    datetime 边界同样是包含式；返回只保留按时间倒序的类型，不保留时间戳，
    因而是旧版 fallback 而非精确衰减输入。``limit`` 在数据库原始反馈行
    层面生效，聚合后每个水果的 tuple 长度可能不同。
    """
    conditions = [
        RecommendationFeedback.user_id == user_id,
        RecommendationFeedback.created_at >= since,
    ]
    if until is not None:
        conditions.append(RecommendationFeedback.created_at <= until)
    statement = (
        select(
            RecommendationItem.fruit_id,
            RecommendationFeedback.feedback_type,
        )
        .join(
            RecommendationItem,
            RecommendationItem.id
            == RecommendationFeedback.recommendation_item_id,
        )
        .where(*conditions)
        .order_by(RecommendationFeedback.created_at.desc())
        .limit(limit)
    )
    grouped: defaultdict[int, list[str]] = defaultdict(list)
    for fruit_id, feedback_type in session.execute(statement):
        grouped[fruit_id].append(feedback_type)
    return {
        fruit_id: tuple(feedback_types)
        for fruit_id, feedback_types in grouped.items()
    }


def history_events(
    session: Session,
    user_id: int,
    *,
    since: date,
    until: date | None = None,
    limit: int = 200,
) -> tuple[HistoryEvent, ...]:
    """汇总展示次数与 eaten 次数，供指数历史衰减使用。

    查询按“推荐日期 × 水果”聚合，日期边界包含两端；展示次数来自所有
    历史推荐组，eaten_count 只统计该用户对同一 item 的 ``eaten`` 反馈。
    返回的是逐日期/水果事件，不是按水果总计；replaced 记录也会参与当前
    统计口径。``limit`` 只限制展示聚合查询，eaten 子查询仍按完整窗口统计。
    """
    conditions = [
        Recommendation.user_id == user_id,
        Recommendation.recommendation_date >= since,
    ]
    if until is not None:
        conditions.append(Recommendation.recommendation_date <= until)
    statement = (
        select(
            Recommendation.recommendation_date,
            RecommendationItem.fruit_id,
            func.count(RecommendationItem.id),
        )
        .join(RecommendationItem, RecommendationItem.recommendation_id == Recommendation.id)
        .where(*conditions)
        .group_by(Recommendation.recommendation_date, RecommendationItem.fruit_id)
        .order_by(Recommendation.recommendation_date.desc())
        .limit(limit)
    )
    eaten_statement = (
        select(
            Recommendation.recommendation_date,
            RecommendationItem.fruit_id,
            func.count(RecommendationFeedback.id),
        )
        .join(RecommendationItem, RecommendationItem.recommendation_id == Recommendation.id)
        .join(RecommendationFeedback, RecommendationFeedback.recommendation_item_id == RecommendationItem.id)
        .where(
            *conditions,
            RecommendationFeedback.user_id == user_id,
            RecommendationFeedback.feedback_type == "eaten",
        )
        .group_by(Recommendation.recommendation_date, RecommendationItem.fruit_id)
    )
    eaten = {
        (occurred_on, fruit_id): int(count)
        for occurred_on, fruit_id, count in session.execute(eaten_statement)
    }
    return tuple(
        HistoryEvent(
            fruit_id=int(fruit_id),
            occurred_on=occurred_on,
            times_shown=int(times_shown),
            eaten_count=eaten.get((occurred_on, fruit_id), 0),
        )
        for occurred_on, fruit_id, times_shown in session.execute(statement)
    )


def feedback_events(
    session: Session,
    user_id: int,
    *,
    since: datetime,
    until: datetime | None = None,
    limit: int = 200,
) -> tuple[FeedbackEvent, ...]:
    """读取带时间的反馈事件，供反馈衰减计算使用。

    每一条反馈保持独立的 ``created_at``，不在 Repository 内聚合；这样纯
    算法可以按事件类型和时间分别衰减。``user_id`` 同时约束推荐和反馈，
    防止跨用户 item 关系混入当前画像。
    """
    conditions = [
        Recommendation.user_id == user_id,
        RecommendationFeedback.user_id == user_id,
        RecommendationFeedback.created_at >= since,
    ]
    if until is not None:
        conditions.append(RecommendationFeedback.created_at <= until)
    statement = (
        select(
            RecommendationItem.fruit_id,
            RecommendationFeedback.feedback_type,
            RecommendationFeedback.created_at,
        )
        .join(Recommendation, Recommendation.id == RecommendationItem.recommendation_id)
        .join(RecommendationFeedback, RecommendationFeedback.recommendation_item_id == RecommendationItem.id)
        .where(*conditions)
        .order_by(RecommendationFeedback.created_at.desc())
        .limit(limit)
    )
    return tuple(
        FeedbackEvent(
            fruit_id=int(fruit_id),
            feedback_type=feedback_type,
            occurred_at=created_at,
        )
        for fruit_id, feedback_type, created_at in session.execute(statement)
    )


def previous_pairs(
    session: Session,
    user_id: int,
    *,
    since: date,
    until: date | None = None,
    limit: int = 30,
) -> tuple[frozenset[int], ...]:
    """获取近期水果组合，避免重复 pair。

    当前实现先按 ``limit`` 读取历史组，再在 Python 中按包含式日期范围
    过滤；返回每组水果 ID 的 frozenset，因此 A+B 与 B+A 相同。active 和
    replaced 都会被保留，刷新记录会继续参与后续 pair novelty。
    """
    recommendations = list_history(session, user_id, limit=limit)
    return tuple(
        frozenset(item.fruit_id for item in recommendation.items)
        for recommendation in recommendations
        if recommendation.recommendation_date >= since
        and (until is None or recommendation.recommendation_date <= until)
        and len(recommendation.items) >= 2
    )


def add_recommendation(
    session: Session,
    recommendation: Recommendation,
) -> Recommendation:
    """加入并 flush 推荐，不在 Repository 内提交事务。

    flush 只确保主键和关系可以在当前事务中继续使用；提交/回滚由
    Application Service 统一控制，保证 recommendation、items 和 JSONB
    reasons 作为一个事务图处理。
    """
    session.add(recommendation)
    session.flush()
    return recommendation


def get_item(
    session: Session,
    item_id: int,
) -> RecommendationItem | None:
    """读取反馈目标及其所属推荐，用于归属校验。

    ``None`` 表示 item 不存在；Repository 本身不决定当前请求用户是否有
    权限，调用方必须将已验证身份与加载出的 recommendation.user_id 比较。
    """
    statement = (
        select(RecommendationItem)
        .where(RecommendationItem.id == item_id)
        .options(
            joinedload(RecommendationItem.recommendation),
            selectinload(RecommendationItem.feedback),
        )
    )
    return session.execute(statement).scalar_one_or_none()


def get_feedback(
    session: Session,
    *,
    item_id: int,
    user_id: int,
    feedback_type: str,
) -> RecommendationFeedback | None:
    """查找同一 item/user/type 的已有反馈，实现幂等提交。

    返回对象表示可以复用已有事件，``None`` 才代表允许创建新事件；最终
    唯一约束仍负责抵御并发重复写入。
    """
    statement = select(RecommendationFeedback).where(
        RecommendationFeedback.recommendation_item_id == item_id,
        RecommendationFeedback.user_id == user_id,
        RecommendationFeedback.feedback_type == feedback_type,
    )
    return session.execute(statement).scalar_one_or_none()


def add_feedback(
    session: Session,
    feedback: RecommendationFeedback,
) -> RecommendationFeedback:
    """加入并 flush 一条反馈，事务由 Application Service 提交。"""
    session.add(feedback)
    session.flush()
    return feedback


__all__ = [
    "acquire_user_lock",
    "add_feedback",
    "add_recommendation",
    "feedback_by_fruit",
    "feedback_events",
    "get_active_recommendation",
    "get_feedback",
    "get_item",
    "get_recommendation",
    "list_history",
    "history_events",
    "next_refresh_number",
    "previous_pairs",
    "recent_fruit_ids",
]
