from book_timer import (
    READING_STATS_EMPTY_TEXT,
    build_reading_stats_lines,
    has_same_book_title,
    has_recent_same_book_title,
    has_same_reading_entry,
    is_less_than_one_month_apart,
)


def test_build_reading_stats_lines_formats_total_years_and_recent_months():
    lines = build_reading_stats_lines(
        [
            {"session_date": "2026-04-20", "book_title": "Alpha"},
            {"session_date": "2026-04-21", "book_title": "Alpha"},
            {"session_date": "2026-03-01", "book_title": "Beta"},
            {"session_date": "2025-12-31", "book_title": "Gamma"},
        ]
    )

    assert lines[0] == "累計 ########## 4 冊"
    assert "2026" in lines[1]
    assert "2026-04" in lines[3]


def test_build_reading_stats_lines_handles_empty_history():
    assert build_reading_stats_lines([]) == [READING_STATS_EMPTY_TEXT]


def test_duplicate_helpers_match_case_insensitive_titles():
    history = [{"session_date": "2026-04-20", "book_title": "Clean Code"}]

    assert has_same_reading_entry(history, "2026-04-20", "clean code")
    assert not has_same_reading_entry(history, "2026-04-21", "clean code")
    assert has_same_book_title(history, "clean code")


def test_one_month_threshold_uses_calendar_months():
    assert is_less_than_one_month_apart("2026-04-20", "2026-05-19")
    assert not is_less_than_one_month_apart("2026-04-20", "2026-05-20")
    assert not is_less_than_one_month_apart("2026-01-31", "2026-02-28")


def test_recent_same_book_title_blocks_only_under_one_month():
    history = [{"session_date": "2026-04-20", "book_title": "Clean Code"}]

    assert has_recent_same_book_title(history, "2026-05-19", "clean code")
    assert not has_recent_same_book_title(history, "2026-05-20", "clean code")
    assert not has_recent_same_book_title(history, "2026-05-19", "Other Book")
