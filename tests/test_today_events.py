from datetime import datetime, timedelta, timezone

from book_timer import build_calendar_event_row
from modules.google_calendar import CalendarEvent


JAPAN_TIMEZONE = timezone(timedelta(hours=9))


def test_build_calendar_event_row_formats_all_day_event():
    event = CalendarEvent(
        summary="祝日",
        start=None,
        end=None,
        is_all_day=True,
    )

    assert build_calendar_event_row(event) == ("終日", "祝日")


def test_build_calendar_event_row_formats_timed_event():
    event = CalendarEvent(
        summary="朝会",
        start=datetime(2026, 7, 11, 10, 0, tzinfo=JAPAN_TIMEZONE),
        end=datetime(2026, 7, 11, 10, 30, tzinfo=JAPAN_TIMEZONE),
        is_all_day=False,
    )

    assert build_calendar_event_row(event) == ("10:00-10:30", "朝会")


def test_build_calendar_event_row_includes_dates_for_overnight_event():
    event = CalendarEvent(
        summary="夜間作業",
        start=datetime(2026, 7, 11, 23, 0, tzinfo=JAPAN_TIMEZONE),
        end=datetime(2026, 7, 12, 1, 0, tzinfo=JAPAN_TIMEZONE),
        is_all_day=False,
    )

    assert build_calendar_event_row(event) == (
        "07/11 23:00-07/12 01:00",
        "夜間作業",
    )
