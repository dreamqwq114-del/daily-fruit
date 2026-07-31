from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.config import Settings, get_settings


def current_app_date(
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> date:
    active_settings = settings or get_settings()
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must include timezone information")
    return current.astimezone(
        ZoneInfo(active_settings.app_timezone)
    ).date()


__all__ = ["current_app_date"]
