from datetime import datetime

import pytest

from book_timer import parse_time_on_date, validate_session_inputs


def test_parse_time_on_date_accepts_hour_beyond_24():
    reference = datetime(2026, 4, 26)

    assert parse_time_on_date("25:00", reference) == datetime(2026, 4, 27, 1, 0)


def test_validate_session_inputs_accepts_overnight_25_hour_end_time():
    start_dt, end_dt = validate_session_inputs(
        "2026-04-26",
        "22:00",
        "2026-04-26",
        "25:00",
        10,
        40,
    )

    assert start_dt == datetime(2026, 4, 26, 22, 0)
    assert end_dt == datetime(2026, 4, 27, 1, 0)


def test_validate_session_inputs_accepts_explicit_next_day_end_date():
    start_dt, end_dt = validate_session_inputs(
        "2026-04-26",
        "23:30",
        "2026-04-27",
        "00:30",
        10,
        40,
    )

    assert start_dt == datetime(2026, 4, 26, 23, 30)
    assert end_dt == datetime(2026, 4, 27, 0, 30)


@pytest.mark.parametrize("time_text", ["24:60", "-1:00", "25"])
def test_parse_time_on_date_rejects_invalid_extended_times(time_text):
    with pytest.raises(ValueError):
        parse_time_on_date(time_text, datetime(2026, 4, 26))
