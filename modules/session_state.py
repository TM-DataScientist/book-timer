from __future__ import annotations

import json
from pathlib import Path

DEFAULT_STATE_PATH = Path(".book_timer_state.json")
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
    if not state_path.exists():
        return {}

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        field: _normalize_value(data.get(field))
        for field in STATE_FIELDS
        if field in data
    }


def save_form_state(
    form_state: dict[str, str],
    state_path: Path = DEFAULT_STATE_PATH,
) -> None:
    """Persist the current form values for the next launch."""
    payload = {
        field: _normalize_value(form_state.get(field, ""))
        for field in STATE_FIELDS
    }

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
