from __future__ import annotations

from datetime import datetime
from pathlib import Path

from modules.session_state import DEFAULT_STATE_PATH, load_legacy_reading_history

DEFAULT_READING_HISTORY_PATH = Path("data/reading_history.parquet")
DATE_FORMAT = "%Y-%m-%d"
READING_HISTORY_COLUMNS = ("session_date", "book_title")
DEPENDENCY_MESSAGE = (
    "読了履歴を Parquet で扱うには "
    "`python -m pip install --upgrade pandas pyarrow` を実行してください。"
)


class ReadingHistoryStoreError(RuntimeError):
    """Raised when reading-history persistence cannot proceed."""


def load_reading_history(
    history_path: Path = DEFAULT_READING_HISTORY_PATH,
    legacy_state_path: Path = DEFAULT_STATE_PATH,
) -> list[dict[str, str]]:
    """Load reading history from Parquet, migrating legacy JSON entries if needed."""
    if history_path.exists():
        return _load_history_from_parquet(history_path)

    legacy_history = normalize_reading_history(load_legacy_reading_history(legacy_state_path))
    if legacy_history:
        save_reading_history(legacy_history, history_path)

    return legacy_history


def save_reading_history(
    reading_history: list[dict[str, str]],
    history_path: Path = DEFAULT_READING_HISTORY_PATH,
) -> None:
    """Persist reading history to a Parquet file."""
    pd = _import_pandas()
    normalized_history = normalize_reading_history(reading_history)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_frame = pd.DataFrame(normalized_history, columns=READING_HISTORY_COLUMNS)

    try:
        history_frame.to_parquet(history_path, index=False)
    except Exception as exc:
        raise ReadingHistoryStoreError(
            "読了履歴を Parquet に保存できませんでした。書き込み権限と依存関係を確認してください。"
        ) from exc


def normalize_reading_history(value: object) -> list[dict[str, str]]:
    """Normalize reading history into unique entries sorted by latest date."""
    if not isinstance(value, list):
        return []

    normalized_entries: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()

    for item in value:
        if not isinstance(item, dict):
            continue

        session_date = _normalize_session_date(item.get("session_date"))
        book_title = _normalize_text(item.get("book_title"))

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

    normalized_entries.sort(key=lambda entry: entry["book_title"].casefold())
    normalized_entries.sort(key=lambda entry: entry["session_date"], reverse=True)
    return normalized_entries


def _load_history_from_parquet(history_path: Path) -> list[dict[str, str]]:
    """Read reading history from the Parquet file."""
    pd = _import_pandas()

    try:
        history_frame = pd.read_parquet(history_path)
    except Exception as exc:
        raise ReadingHistoryStoreError(
            "読了履歴の Parquet 読み込みに失敗しました。ファイル形式と依存関係を確認してください。"
        ) from exc

    return normalize_reading_history(history_frame.to_dict(orient="records"))


def _normalize_text(value: object) -> str:
    """Normalize text values while keeping empty values empty."""
    if value is None:
        return ""
    return str(value).strip()


def _normalize_session_date(value: object) -> str:
    """Normalize supported date inputs to YYYY-MM-DD."""
    text = _normalize_text(value)
    if not text:
        return ""

    try:
        return datetime.strptime(text, DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError:
        return ""


def _import_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise ReadingHistoryStoreError(DEPENDENCY_MESSAGE) from exc

    return pd
