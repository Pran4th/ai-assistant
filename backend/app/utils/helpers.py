from datetime import datetime, timedelta, date
import re
from typing import Optional, Tuple


def parse_relative_date(text: str) -> Optional[str]:
    text = text.lower().strip()
    today = date.today()

    if text in ("today", "now"):
        return today.isoformat()
    if text == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if text == "day after tomorrow":
        return (today + timedelta(days=2)).isoformat()
    if text == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    match = re.match(r"(next|this|last)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", text)
    if match:
        direction, day_name = match.groups()
        target_day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(day_name)
        current_day = today.weekday()
        days_ahead = target_day - current_day
        if direction == "next":
            days_ahead += 7 if days_ahead <= 0 else 0
        elif direction == "last":
            days_ahead -= 7 if days_ahead > 0 else 0
        return (today + timedelta(days=days_ahead)).isoformat()

    match = re.match(r"in\s+(\d+)\s+(day|days|week|weeks|month|months)", text)
    if match:
        count, unit = int(match.group(1)), match.group(2)
        if "day" in unit:
            return (today + timedelta(days=count)).isoformat()
        if "week" in unit:
            return (today + timedelta(weeks=count)).isoformat()
        if "month" in unit:
            return (today + timedelta(days=count * 30)).isoformat()

    return None


def parse_time(text: str) -> Optional[str]:
    text = text.lower().strip()
    match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3) if match.group(3) else None
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}:00"
    return None


def format_datetime_for_api(date_str: str, time_str: Optional[str] = None) -> str:
    if time_str:
        return f"{date_str}T{time_str}"
    return f"{date_str}T00:00:00"


def sanitize_input(text: str) -> str:
    return re.sub(r"[<>\"]", "", text)


def truncate_text(text: str, max_length: int = 2000) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
