"""Normalize supported source dates without substituting recency scores."""
from datetime import datetime, timezone


def parse_date(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.strptime(value, "%b %d, %Y")
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def timestamp(value: str | None) -> float:
    return parse_date(value).timestamp() if value else float("-inf")
