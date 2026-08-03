"""推荐业务编排：加载数据、控制事务、调用纯算法并持久化结果。

本模块是数据库世界与纯 recommendation_service 之间的应用边界：它负责
用户锁、查询窗口、刷新状态、事务提交和 ORM/领域对象转换，但不重新实现
过滤、评分或组合公式。任何推荐规则变化都应留在纯算法模块，任何事务
生命周期变化都应在这里和 Repository 的协作合同中审查。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.clock import current_app_date
from app.errors import ResourceConflictError, ResourceNotFoundError
from app.models import (
    Recommendation,
    RecommendationFeedback,
    RecommendationItem,
    User,
)
from app.repositories import (
    fruit_repository,
    recommendation_repository,
    user_repository,
)
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationFeedbackCreate,
    RecommendationFeedbackRead,
)
from app.services.api_mapper import recommendation_to_detail
from app.services.recommendation_mapper import (
    build_recommendation_context,
    fruit_to_recommendation_input,
    user_to_recommendation_input,
)
from app.services.recommendation_service import (
    RecommendationError,
    recommend_fruits,
)
from app.services.recommendation_types import RecommendationResult


# 这些是数据库查询和短期冷却窗口，不是 recommendation_service 中历史/反馈
# 指数衰减的 tau；扩大查询窗口会改变输入事件集合，但不会自动改变算法衰减常数。
HISTORY_DAYS = 30
PAIR_COOLDOWN_DAYS = 3
FRUIT_COOLDOWN_DAYS = 1
FEEDBACK_DAYS = 180
DEFAULT_HISTORY_LIMIT = 30


@dataclass(frozen=True, slots=True)
class FeedbackSubmission:
    feedback: RecommendationFeedbackRead
    created: bool


class RecommendationInvariantError(RuntimeError):
    """推荐核心违反必须始终成立的内部约束。"""


def get_today_recommendation(
    session: Session,
    user_id: int,
    *,
    today: date | None = None,
) -> RecommendationDetail:
    """复用当天 active 推荐；不存在时在用户锁内创建一组。

    生命周期是：获取用户级 transaction advisory lock → 读取用户及当天
    active → 有则提交当前只读事务并返回 → 无则查询刷新序号、加载算法
    上下文、flush 新推荐 → commit → 重新加载完整详情。锁的持续范围由
    外层数据库事务决定，目标是让同一用户同一天的并发请求不会各自创建
    active 记录；数据库 partial unique index 仍是最后一道约束。
    """

    recommendation_date = today or current_app_date()
    # 锁必须在读取 active、计算 refresh_number 和插入新推荐之前取得；
    # 只锁查询或只锁插入都无法保护“当天是否已有 active”的检查。
    recommendation_repository.acquire_user_lock(session, user_id)
    user = user_repository.get_user(
        session,
        user_id,
        include_preferences=True,
    )
    if user is None:
        raise ResourceNotFoundError("用户不存在")

    existing = recommendation_repository.get_active_recommendation(
        session,
        user_id,
        recommendation_date,
    )
    if existing is not None:
        # 页面刷新复用同一 active 结果，不重新运行算法；因此当天展示保持
        # 稳定，主动 refresh 必须走单独的状态转换路径。
        detail = recommendation_to_detail(existing)
        session.commit()
        return detail

    refresh_number = recommendation_repository.next_refresh_number(
        session,
        user_id,
        recommendation_date,
    )
    result = _calculate_recommendation(
        session,
        user,
        recommendation_date,
        refresh_number,
    )
    recommendation = _persist_recommendation(
        session,
        user_id,
        recommendation_date,
        refresh_number,
        result,
    )
    # add_recommendation 只 flush 取得数据库 ID；commit 在这里统一完成。
    recommendation_id = recommendation.id
    session.commit()
    return _load_detail(session, recommendation_id)


def refresh_recommendation(
    session: Session,
    user_id: int,
    *,
    today: date | None = None,
) -> RecommendationDetail:
    """把旧组标记 replaced，并生成不同组合。

    刷新在同一个用户锁内完成：锁定 active → 改为 ``replaced`` → flush
    → 递增 refresh_number → 排除上一组并计算新组合 → 持久化 active
    → commit。如果核心抛出推荐错误或不变量异常，
    本事务不会 commit；FastAPI Session 依赖会回滚已 flush 的 ``replaced``
    状态和刷新事件，使原 active 推荐保持不变。
    """

    recommendation_date = today or current_app_date()
    # 与 get_today_recommendation 使用同一用户级 advisory transaction lock，
    # 保证状态变更、刷新序号和新 active 插入属于一个串行化临界区。
    recommendation_repository.acquire_user_lock(session, user_id)
    user = user_repository.get_user(
        session,
        user_id,
        include_preferences=True,
    )
    if user is None:
        raise ResourceNotFoundError("用户不存在")

    active = recommendation_repository.get_active_recommendation(
        session,
        user_id,
        recommendation_date,
        for_update=True,
    )
    if active is None:
        raise ResourceConflictError("今天还没有可更换的 active 推荐")

    previous_ids = {item.fruit_id for item in active.items}
    # 旧推荐仍保留在历史中，只改变生命周期状态；items/feedback 不删除。
    active.status = "replaced"
    # flush 让 replaced 状态在生成新组合前落入当前事务，
    # 但此时仍可由后续异常整体 rollback；commit 只在新推荐成功后执行。
    session.flush()

    refresh_number = recommendation_repository.next_refresh_number(
        session,
        user_id,
        recommendation_date,
    )
    result = _calculate_recommendation(
        session,
        user,
        recommendation_date,
        refresh_number,
        previous_ids=previous_ids,
    )
    recommendation = _persist_recommendation(
        session,
        user_id,
        recommendation_date,
        refresh_number,
        result,
    )
    recommendation_id = recommendation.id
    session.commit()
    return _load_detail(session, recommendation_id)


def list_recommendation_history(
    session: Session,
    user_id: int,
    *,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[RecommendationDetail]:
    """读取当前用户的推荐历史，具体预加载由 Repository 负责。

    历史同时包含 active 与 replaced 记录，排序和数量限制由 Repository
    定义；本函数只做用户存在性检查和 API 映射，不参与推荐评分。
    """

    if user_repository.get_user(session, user_id) is None:
        raise ResourceNotFoundError("用户不存在")
    return [
        recommendation_to_detail(item)
        for item in recommendation_repository.list_history(
            session,
            user_id,
            limit=limit,
        )
    ]


def submit_feedback(
    session: Session,
    item_id: int,
    payload: RecommendationFeedbackCreate,
    *,
    expected_user_id: int | None = None,
) -> FeedbackSubmission:
    """校验 item 所属用户后幂等写入反馈，防止跨用户提交。

    ``get_item`` 先加载推荐归属，``expected_user_id`` 来自已验证身份；
    同一 item/user/type 已存在时直接返回 ``created=False``，否则 flush 后
    commit 一条事件。查询、归属校验和写入必须在同一 session 边界内完成。
    """

    item = recommendation_repository.get_item(session, item_id)
    if item is None:
        raise ResourceNotFoundError("推荐项不存在")
    user_id = item.recommendation.user_id
    if expected_user_id is not None and user_id != expected_user_id:
        raise ResourceNotFoundError("推荐项不存在")
    existing = recommendation_repository.get_feedback(
        session,
        item_id=item_id,
        user_id=user_id,
        feedback_type=payload.feedback_type,
    )
    if existing is not None:
        return FeedbackSubmission(
            feedback=RecommendationFeedbackRead.model_validate(existing),
            created=False,
        )

    feedback = recommendation_repository.add_feedback(
        session,
        RecommendationFeedback(
            recommendation_item_id=item_id,
            user_id=user_id,
            feedback_type=payload.feedback_type,
            comment=payload.comment,
        ),
    )
    session.commit()
    return FeedbackSubmission(
        feedback=RecommendationFeedbackRead.model_validate(feedback),
        created=True,
    )


def _calculate_recommendation(
    session: Session,
    user: User,
    recommendation_date: date,
    refresh_number: int,
    *,
    previous_ids: set[int] | None = None,
) -> RecommendationResult:
    """把数据库快照组装成纯算法上下文，并转换领域错误为 API 冲突。

    历史窗口按推荐日期取最近 ``HISTORY_DAYS`` 天，另外用
    ``PAIR_COOLDOWN_DAYS`` 天窗口提供短期组合硬冷却；反馈窗口按当前 UTC
    时间取最近 ``FEEDBACK_DAYS`` 天。它们分别提供事件、聚合反馈、长期
    新颖度和短期去重输入。``stable_seed`` 由用户、业务日期和刷新序号组成，
    所以刷新会改变近优选择，而同一上下文的重复计算仍可复现。这里仍然只
    加载 active 水果，购买条件字段不会被映射到 RecommendationUser。
    """

    fruits = fruit_repository.list_active_fruits(session)
    domain_fruits = [
        fruit_to_recommendation_input(fruit) for fruit in fruits
    ]
    domain_user = user_to_recommendation_input(user)
    # 查询窗口至少覆盖跨天水果冷却；通常由更长的 30 天历史窗口决定。
    since_date = recommendation_date - timedelta(
        days=max(HISTORY_DAYS, FRUIT_COOLDOWN_DAYS)
    )
    # 反馈查询使用真实当前时刻；推荐日期只作为历史/结果业务日期，不能
    # 用它伪造反馈事件发生时间，否则衰减会失去意义。
    now = datetime.now(UTC)
    recent_ids = recommendation_repository.recent_fruit_ids(
        session,
        user.id,
        since=since_date,
        until=recommendation_date,
    )
    history_events = recommendation_repository.history_events(
        session,
        user.id,
        since=since_date,
        until=recommendation_date,
    )
    previous_pairs = recommendation_repository.previous_pairs(
        session,
        user.id,
        since=since_date,
        until=recommendation_date,
    )
    # previous_pairs 保留 30 天窗口，只服务组合新颖度；短期硬冷却必须
    # 单独查询，否则“最近 3 天不能重复”会意外扩大为整整 30 天。
    pair_cooldown_since = recommendation_date - timedelta(
        days=PAIR_COOLDOWN_DAYS
    )
    cooldown_pairs = recommendation_repository.previous_pairs(
        session,
        user.id,
        since=pair_cooldown_since,
        until=recommendation_date,
    )
    feedback_events = recommendation_repository.feedback_events(
        session,
        user.id,
        since=now - timedelta(days=FEEDBACK_DAYS),
        until=now,
    )
    feedback = recommendation_repository.feedback_by_fruit(
        session,
        user.id,
        since=now - timedelta(days=FEEDBACK_DAYS),
        until=now,
    )
    context = build_recommendation_context(
        month=recommendation_date.month,
        today=recommendation_date,
        recent_fruit_ids=recent_ids,
        feedback_by_fruit=feedback,
        history_events=history_events,
        feedback_events=feedback_events,
        cooldown_pairs=cooldown_pairs,
        previous_pairs=previous_pairs,
        excluded_pair=(
            frozenset(previous_ids) if previous_ids else None
        ),
        random_seed=_stable_seed(
            user.id,
            recommendation_date,
            refresh_number,
        ),
    )
    try:
        result = recommend_fruits(domain_fruits, domain_user, context)
    except RecommendationError as error:
        raise ResourceConflictError(str(error)) from error

    # excluded_pair 是推荐核心必须遵守的硬约束。
    # 如果核心仍返回旧组合，说明算法不变量被破坏；应用层不再改变候选集
    # 或偷偷重算，而是暴露内部错误，避免把错误结果持久化成新推荐。
    if previous_ids is not None and _result_ids(result) == previous_ids:
        raise RecommendationInvariantError(
            "手动换组后推荐核心仍返回原水果组合"
        )
    return result


def _persist_recommendation(
    session: Session,
    user_id: int,
    recommendation_date: date,
    refresh_number: int,
    result: RecommendationResult,
) -> Recommendation:
    """把算法结果和 JSONB reasons 映射为 ORM，等待外层事务提交。

    Repository 的 ``add_recommendation`` 只负责 ``flush``，这里不提前
    commit，确保推荐主记录、两条 item 和 JSONB 理由作为一个事务图一起
    成功或失败。字段 fallback 仅兼容旧算法结果，不能被用来隐藏缺失分数。
    """

    recommendation = Recommendation(
        user_id=user_id,
        recommendation_date=recommendation_date,
        refresh_number=refresh_number,
        total_score=_score_decimal(result.total_score),
        status="active",
        items=[
            RecommendationItem(
                fruit_id=item.fruit.id,
                score=_score_decimal(item.score),
                individual_score=_score_decimal(
                    item.individual_score
                    if item.individual_score is not None
                    else item.score
                ),
                pair_score=_score_decimal(
                    item.pair_score
                    if item.pair_score is not None
                    else result.total_score
                ),
                nutrition_pair_score=_score_decimal(
                    item.nutrition_pair_score
                    if item.nutrition_pair_score is not None
                    else 0
                ),
                rank=item.rank,
                reasons=[
                    reason.model_dump(mode="json")
                    for reason in item.reasons
                ],
                selection_option_id=(
                    item.resolved_candidate.resolved_option_id
                    if item.resolved_candidate is not None
                    else None
                ),
                selection_option_name_snapshot=(
                    item.resolved_candidate.resolved_option_name
                    if item.resolved_candidate is not None
                    else None
                ),
                selection_option_code_snapshot=(
                    item.resolved_candidate.resolved_option_code
                    if item.resolved_candidate is not None
                    else None
                ),
                selection_resolution_source=(
                    item.resolved_candidate.resolution_source
                    if item.resolved_candidate is not None
                    else None
                ),
                effective_sweet_score_snapshot=(
                    _score_decimal(item.resolved_candidate.effective_sweet_score)
                    if item.resolved_candidate is not None
                    else None
                ),
                effective_sour_score_snapshot=(
                    _score_decimal(item.resolved_candidate.effective_sour_score)
                    if item.resolved_candidate is not None
                    else None
                ),
                effective_soft_score_snapshot=(
                    _score_decimal(item.resolved_candidate.effective_soft_score)
                    if item.resolved_candidate is not None
                    else None
                ),
                effective_crisp_score_snapshot=(
                    _score_decimal(item.resolved_candidate.effective_crisp_score)
                    if item.resolved_candidate is not None
                    else None
                ),
            )
            for item in result.items
        ],
    )
    return recommendation_repository.add_recommendation(
        session,
        recommendation,
    )


def _load_detail(
    session: Session,
    recommendation_id: int,
) -> RecommendationDetail:
    """提交后重新加载完整水果/反馈关系，生成 API 详情。

    ``expire_all`` 避免继续使用 commit 前的部分 ORM 快照；Repository 的
    eager-load 选项负责一次性补齐 API 需要的水果、营养、季节和反馈关系。
    """

    session.expire_all()
    recommendation = recommendation_repository.get_recommendation(
        session,
        recommendation_id,
    )
    if recommendation is None:
        raise ResourceNotFoundError("推荐记录不存在")
    return recommendation_to_detail(recommendation)


def _stable_seed(
    user_id: int,
    recommendation_date: date,
    refresh_number: int,
) -> int:
    """由用户、日期和刷新序号构成可复现的近优组合 seed。

    这是稳定选择用的普通整数，不是安全随机数，也不需要跨部署保密；
    refresh_number 刻意参与公式，使“换一组”能得到不同的近优选择。
    """

    return (
        recommendation_date.toordinal() * 1_000_003
        + user_id * 101
        + refresh_number
    )


def _score_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def _result_ids(result: RecommendationResult) -> set[int]:
    return {item.fruit.id for item in result.items}


__all__ = [
    "FeedbackSubmission",
    "get_today_recommendation",
    "list_recommendation_history",
    "refresh_recommendation",
    "submit_feedback",
]
