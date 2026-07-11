from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta

DATE_FORMAT = "%Y-%m-%d"
START_PAGE_LABEL = "開始ページ"
END_PAGE_LABEL = "終了ページ"
PAGE_INCREMENT_LABEL = "加算ページ"


@dataclass(frozen=True)
class SessionProgress:
    """A structured snapshot of reading-session progress."""

    state: str
    message: str
    progress: float
    current_page: int


def parse_time_on_date(time_text: str, reference: datetime) -> datetime:
    """Parse HH:MM text on the reference date, allowing hours beyond 24."""
    normalized = time_text.strip()

    try:
        hour_text, minute_text = normalized.split(":", maxsplit=1)
        hours = int(hour_text)
        minutes = int(minute_text)
    except ValueError as exc:
        raise ValueError("Invalid time format") from exc

    if hours < 0 or minutes < 0 or minutes > 59:
        raise ValueError("Invalid time format")

    midnight = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight + timedelta(hours=hours, minutes=minutes)


def parse_session_date(date_text: str) -> datetime:
    """Parse YYYY-MM-DD text and return the date at midnight."""
    try:
        parsed = datetime.strptime(date_text.strip(), DATE_FORMAT)
    except ValueError as exc:
        raise ValueError("日付は YYYY-MM-DD 形式で入力してください。") from exc

    return parsed.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_page(page_text: str, label: str) -> int:
    """Convert page input to an integer with a readable validation message."""
    try:
        return int(page_text.strip())
    except ValueError as exc:
        raise ValueError(f"{label}は整数で入力してください。") from exc


def parse_book_title(
    book_text: str,
    *,
    missing_message: str = "書名を入力してください。",
) -> str:
    """Require a non-empty book title and return the normalized value."""
    title = book_text.strip()
    if not title:
        raise ValueError(missing_message)
    return title


def has_same_reading_entry(
    reading_history: list[dict[str, str]],
    session_date: str,
    book_title: str,
) -> bool:
    """Return whether the same normalized title is registered on the same date."""
    normalized_title = book_title.casefold()
    return any(
        entry["session_date"] == session_date
        and entry["book_title"].casefold() == normalized_title
        for entry in reading_history
    )


def add_months(value: datetime, month_count: int) -> datetime:
    """Return a date shifted by whole calendar months."""
    month_index = value.month - 1 + month_count
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def is_less_than_one_month_apart(first_date: str, second_date: str) -> bool:
    """Return whether two YYYY-MM-DD dates are separated by less than one month."""
    first_dt = parse_session_date(first_date)
    second_dt = parse_session_date(second_date)
    earlier_dt, later_dt = sorted((first_dt, second_dt))
    return add_months(earlier_dt, 1) > later_dt


def has_recent_same_book_title(
    reading_history: list[dict[str, str]],
    session_date: str,
    book_title: str,
) -> bool:
    """Return whether the same title was read less than one month apart."""
    normalized_title = book_title.casefold()
    return any(
        entry["book_title"].casefold() == normalized_title
        and is_less_than_one_month_apart(entry["session_date"], session_date)
        for entry in reading_history
    )


def has_same_book_title(
    reading_history: list[dict[str, str]],
    book_title: str,
) -> bool:
    """Return whether the same normalized title exists anywhere in history."""
    normalized_title = book_title.casefold()
    return any(
        entry["book_title"].casefold() == normalized_title
        for entry in reading_history
    )


def normalize_session_date(date_text: str) -> str:
    """Normalize a supported date input to YYYY-MM-DD."""
    return parse_session_date(date_text).strftime(DATE_FORMAT)


def format_current_start_values(now: datetime) -> tuple[str, str]:
    """Return date and HH:MM values for setting a session start to now."""
    return now.strftime(DATE_FORMAT), now.strftime("%H:%M")


def sync_end_date_for_start_change(
    previous_start_date: str,
    current_start_date: str,
    current_end_date: str,
) -> str:
    """Return the end date adjusted by the same date delta as the start date."""
    normalized_current_start = normalize_session_date(current_start_date)
    normalized_current_end = current_end_date.strip()

    try:
        previous_start_dt = parse_session_date(previous_start_date)
        current_start_dt = parse_session_date(normalized_current_start)
        current_end_dt = parse_session_date(normalized_current_end)
    except ValueError:
        return normalized_current_start

    shifted_end_dt = current_end_dt + (current_start_dt - previous_start_dt)
    return shifted_end_dt.strftime(DATE_FORMAT)


def shift_session_dates_by_days(
    start_date: str,
    end_date: str,
    day_count: int,
) -> tuple[str, str]:
    """Return start and end dates shifted by a whole number of days."""
    start_dt = parse_session_date(start_date)
    end_dt = parse_session_date(end_date)
    date_delta = timedelta(days=day_count)
    return (
        (start_dt + date_delta).strftime(DATE_FORMAT),
        (end_dt + date_delta).strftime(DATE_FORMAT),
    )


def increment_page_range(
    start_page_text: str,
    end_page_text: str,
    increment_text: str,
) -> tuple[str, str]:
    """Return start and end page values increased by the requested amount."""
    start_page = parse_page(start_page_text, START_PAGE_LABEL)
    end_page = parse_page(end_page_text, END_PAGE_LABEL)
    increment = parse_page(increment_text, PAGE_INCREMENT_LABEL)

    if increment < 0:
        raise ValueError(f"{PAGE_INCREMENT_LABEL}は0以上の整数で入力してください。")

    return str(start_page + increment), str(end_page + increment)


def validate_session_inputs(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    start_page: int,
    end_page: int,
) -> tuple[datetime, datetime]:
    """Validate date/time/page inputs and return parsed datetimes."""
    start_reference = parse_session_date(start_date)
    end_reference = parse_session_date(end_date)

    try:
        start_dt = parse_time_on_date(start_time, start_reference)
        end_dt = parse_time_on_date(end_time, end_reference)
    except ValueError as exc:
        raise ValueError(
            "時刻は HH:MM 形式で入力してください。24:00 以降は翌日の時刻として扱います。"
        ) from exc

    if end_dt <= start_dt:
        raise ValueError("終了時刻は開始時刻より後にしてください。")

    if end_page < start_page:
        raise ValueError("終了ページは開始ページ以上にしてください。")

    return start_dt, end_dt


def collect_session_inputs(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    start_page_text: str,
    end_page_text: str,
) -> tuple[str, str, str, str, int, int]:
    """Parse and validate form values into a session tuple."""
    normalized_start_date = normalize_session_date(start_date)
    normalized_end_date = normalize_session_date(end_date)
    start_page = parse_page(start_page_text, START_PAGE_LABEL)
    end_page = parse_page(end_page_text, END_PAGE_LABEL)
    validate_session_inputs(
        normalized_start_date,
        start_time,
        normalized_end_date,
        end_time,
        start_page,
        end_page,
    )
    return (
        normalized_start_date,
        start_time,
        normalized_end_date,
        end_time,
        start_page,
        end_page,
    )


def get_session_progress(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    start_page: int,
    end_page: int,
    *,
    now: datetime | None = None,
) -> SessionProgress:
    """Return a structured progress snapshot for a valid reading session."""
    start_dt, end_dt = validate_session_inputs(
        start_date,
        start_time,
        end_date,
        end_time,
        start_page,
        end_page,
    )
    current_time = now or datetime.now()

    if current_time < start_dt:
        minutes = int((start_dt - current_time).total_seconds() // 60)
        return SessionProgress(
            state="upcoming",
            message=f"読書開始まであと {minutes} 分です。",
            progress=0.0,
            current_page=start_page,
        )

    if current_time >= end_dt:
        return SessionProgress(
            state="complete",
            message=(
                "読書セッションは終了しました。"
                f"最終ページ {end_page} を確認してください。"
            ),
            progress=1.0,
            current_page=end_page,
        )

    total_seconds = (end_dt - start_dt).total_seconds()
    elapsed_seconds = (current_time - start_dt).total_seconds()
    progress = min(max(elapsed_seconds / total_seconds, 0.0), 1.0)
    total_pages = max(end_page - start_page, 0) + 1
    current_page = start_page + int(total_pages * progress)
    current_page = min(max(current_page, start_page), end_page)
    return SessionProgress(
        state="active",
        message=f"現在の推定位置: {current_page} ページ",
        progress=progress,
        current_page=current_page,
    )


def calculate_pages(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    start_page: int,
    end_page: int,
) -> str:
    """Return a friendly status message describing current reading progress."""
    try:
        return get_session_progress(
            start_date,
            start_time,
            end_date,
            end_time,
            start_page,
            end_page,
        ).message
    except ValueError as exc:
        return str(exc)
