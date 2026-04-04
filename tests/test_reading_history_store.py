import json

import pytest

from modules.reading_history_store import (
    ReadingHistoryStoreError,
    load_reading_history,
    save_reading_history,
)


def test_save_and_load_reading_history_uses_parquet_and_sorts_latest_first(tmp_path):
    history_path = tmp_path / "reading_history.parquet"

    save_reading_history(
        [
            {"session_date": "2026-03-30", "book_title": "Alpha"},
            {"session_date": "2026-04-01", "book_title": "Beta"},
            {"session_date": "2026-4-1", "book_title": "beta"},
            {"session_date": "2026-03-28", "book_title": "Gamma"},
            {"session_date": "", "book_title": "Ignored"},
        ],
        history_path,
    )

    assert load_reading_history(history_path, tmp_path / "state.json") == [
        {"session_date": "2026-04-01", "book_title": "Beta"},
        {"session_date": "2026-03-30", "book_title": "Alpha"},
        {"session_date": "2026-03-28", "book_title": "Gamma"},
    ]


def test_load_reading_history_migrates_legacy_json_when_parquet_missing(tmp_path):
    history_path = tmp_path / "reading_history.parquet"
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "reading_history": [
                    {"session_date": "2026-04-04", "book_title": "Book A"},
                    {"session_date": "2026-04-03", "book_title": "Book B"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    migrated_history = load_reading_history(history_path, state_path)

    assert migrated_history == [
        {"session_date": "2026-04-04", "book_title": "Book A"},
        {"session_date": "2026-04-03", "book_title": "Book B"},
    ]
    assert history_path.exists()


def test_load_reading_history_raises_for_invalid_parquet(tmp_path):
    history_path = tmp_path / "reading_history.parquet"
    history_path.write_text("not parquet", encoding="utf-8")

    with pytest.raises(ReadingHistoryStoreError):
        load_reading_history(history_path, tmp_path / "state.json")
