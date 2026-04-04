from __future__ import annotations

import json
from pathlib import Path

DEFAULT_STATE_PATH = Path(".book_timer_state.json")
BOOKS_FIELD = "books"
READING_HISTORY_FIELD = "reading_history"
STATE_FIELDS = (
    "book_title",
    "session_date",
    "start_time",
    "end_time",
    "start_page",
    "end_page",
)


class SessionStateError(RuntimeError):
    """Raised when the application state cannot be saved."""


def load_form_state(state_path: Path = DEFAULT_STATE_PATH) -> dict[str, str]:
    """Load the previously saved form values, if available."""
    data = _load_state_data(state_path)

    return {
        field: _normalize_value(data.get(field))
        for field in STATE_FIELDS
        if field in data
    }


def load_book_titles(state_path: Path = DEFAULT_STATE_PATH) -> list[str]:
    """Load the saved book title choices for the dropdown."""
    data = _load_state_data(state_path)
    return _normalize_book_titles(data.get(BOOKS_FIELD))


def load_reading_history(state_path: Path = DEFAULT_STATE_PATH) -> list[dict[str, str]]:
    """Load the persisted reading history entries sorted by latest first."""
    data = _load_state_data(state_path)
    return _normalize_reading_history(data.get(READING_HISTORY_FIELD))


def save_form_state(
    form_state: dict[str, str],
    book_titles: list[str] | None = None,
    reading_history: list[dict[str, str]] | None = None,
    state_path: Path = DEFAULT_STATE_PATH,
) -> None:
    """Persist the current form values for the next launch."""
    payload: dict[str, object] = {
        field: _normalize_value(form_state.get(field, ""))
        for field in STATE_FIELDS
    }
    payload[BOOKS_FIELD] = _normalize_book_titles(book_titles)
    payload[READING_HISTORY_FIELD] = _normalize_reading_history(reading_history)

    try:
        state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise SessionStateError(
            "前回の入力内容を保存できませんでした。書き込み権限を確認してください。"
        ) from exc


def _normalize_value(value: object) -> str:
    """Convert persisted values to strings while keeping empty values empty."""
    if value is None:
        return ""
    return str(value)


def _load_state_data(state_path: Path) -> dict[str, object]:
    """Read the JSON state payload if it exists and is well-formed."""
    if not state_path.exists():
        return {}

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def _normalize_book_titles(value: object) -> list[str]:
    """Normalize a persisted book list into unique, non-empty strings."""
    if not isinstance(value, list):
        return []

    normalized_titles: list[str] = []

    for item in value:
        title = _normalize_value(item).strip()
        if title and title not in normalized_titles:
            normalized_titles.append(title)

    normalized_titles.sort(key=str.casefold)
    return normalized_titles


def _normalize_reading_history(value: object) -> list[dict[str, str]]:
    """Normalize persisted reading history into unique entries sorted by date."""
    if not isinstance(value, list):
        return []

    normalized_entries: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()

    for item in value:
        if not isinstance(item, dict):
            continue

        session_date = _normalize_value(item.get("session_date")).strip()
        book_title = _normalize_value(item.get("book_title")).strip()

        if not session_date or not book_title:
            continue

        entry_key = (session_date, book_title.casefold())
        if entry_key in seen_keys:
            continue

        seen_keys.add(entry_key)
        normalized_entries.append(
            {
                "session_date": session_date,
                "book_title": book_title,
            }
        )

    normalized_entries.sort(
        key=lambda entry: (
            entry["session_date"],
            entry["book_title"].casefold(),
        ),
        reverse=True,
    )
    return normalized_entries
