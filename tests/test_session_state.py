import json

from modules.session_state import load_legacy_reading_history, save_form_state


def test_save_form_state_keeps_form_fields_and_book_titles_only(tmp_path):
    state_path = tmp_path / "state.json"

    save_form_state(
        {
            "book_title": "Current Book",
            "session_date": "2026-04-05",
            "start_time": "08:00",
            "end_time": "09:00",
            "start_page": "1",
            "end_page": "10",
        },
        ["Current Book", "Another Book"],
        state_path,
    )

    payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert payload == {
        "book_title": "Current Book",
        "session_date": "2026-04-05",
        "start_time": "08:00",
        "end_time": "09:00",
        "start_page": "1",
        "end_page": "10",
        "books": ["Another Book", "Current Book"],
    }


def test_load_legacy_reading_history_sorts_latest_first_and_deduplicates(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "reading_history": [
                    {"session_date": "2026-03-30", "book_title": "Alpha"},
                    {"session_date": "2026-04-01", "book_title": "Beta"},
                    {"session_date": "2026-4-1", "book_title": "beta"},
                    {"session_date": "2026-03-28", "book_title": "Gamma"},
                    {"session_date": "", "book_title": "Ignored"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert load_legacy_reading_history(state_path) == [
        {"session_date": "2026-04-01", "book_title": "Beta"},
        {"session_date": "2026-03-30", "book_title": "Alpha"},
        {"session_date": "2026-03-28", "book_title": "Gamma"},
    ]


def test_load_legacy_reading_history_ignores_non_list_values(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text('{"reading_history": "invalid"}', encoding="utf-8")

    assert load_legacy_reading_history(state_path) == []
