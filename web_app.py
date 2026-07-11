from __future__ import annotations

import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from modules.google_calendar import (
    CalendarEvent,
    GoogleCalendarIntegrationError,
    create_reading_event,
    get_today_events,
    has_cached_calendar_credentials,
)
from modules.reading_history_store import (
    ReadingHistoryStoreError,
    load_reading_history,
    normalize_reading_history,
    save_reading_history,
    summarize_reading_history,
)
from modules.reading_session import (
    collect_session_inputs,
    has_recent_same_book_title,
    has_same_book_title,
    has_same_reading_entry,
    normalize_session_date,
    parse_book_title,
    validate_session_inputs,
)
from modules.session_state import (
    SessionStateError,
    load_book_titles,
    load_form_state,
    save_form_state,
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
STATE_PATH = BASE_DIR / ".book_timer_state.json"
HISTORY_PATH = BASE_DIR / "data" / "reading_history.parquet"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

DEFAULT_START_TIME = "08:00"
DEFAULT_END_TIME = "24:00"


class SessionForm(BaseModel):
    book_title: str = Field(default="", max_length=300)
    start_date: str = Field(max_length=10)
    start_time: str = Field(max_length=5)
    end_date: str = Field(max_length=10)
    end_time: str = Field(max_length=5)
    start_page: str = Field(max_length=10)
    end_page: str = Field(max_length=10)


class SaveStateRequest(SessionForm):
    book_titles: list[str] = Field(default_factory=list)


class ReadingHistoryRequest(BaseModel):
    session_date: str = Field(max_length=10)
    book_title: str = Field(max_length=300)
    allow_reread: bool = False


app = FastAPI(
    title="Book Timer API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


def _default_form_state() -> dict[str, str]:
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "book_title": "",
        "start_date": today,
        "end_date": today,
        "session_date": today,
        "start_time": DEFAULT_START_TIME,
        "end_time": DEFAULT_END_TIME,
        "start_page": "",
        "end_page": "",
    }


def _load_complete_form_state() -> dict[str, str]:
    state = _default_form_state()
    state.update(
        {
            key: value
            for key, value in load_form_state(STATE_PATH).items()
            if value
        }
    )
    return state


def _serialize_summary(history: list[dict[str, str]]) -> dict[str, object]:
    summary = summarize_reading_history(history)
    return {
        "total": summary["total"],
        "yearly": [
            {"period": period, "count": count}
            for period, count in summary["yearly"]
        ],
        "monthly": [
            {"period": period, "count": count}
            for period, count in summary["monthly"]
        ],
    }


def _history_response(history: list[dict[str, str]]) -> dict[str, object]:
    normalized = normalize_reading_history(history)
    return {
        "history": normalized,
        "summary": _serialize_summary(normalized),
    }


def _form_state_from_payload(payload: SessionForm) -> dict[str, str]:
    return {
        "book_title": payload.book_title.strip(),
        "start_date": payload.start_date.strip(),
        "end_date": payload.end_date.strip(),
        "session_date": payload.start_date.strip(),
        "start_time": payload.start_time.strip(),
        "end_time": payload.end_time.strip(),
        "start_page": payload.start_page.strip(),
        "end_page": payload.end_page.strip(),
    }


def _remember_book_title(book_title: str) -> list[str]:
    titles = load_book_titles(STATE_PATH)
    normalized_title = book_title.strip()
    if normalized_title and normalized_title not in titles:
        titles.append(normalized_title)
        titles.sort(key=str.casefold)
        save_form_state(load_form_state(STATE_PATH), titles, STATE_PATH)
    return titles


def _validated_session(
    payload: SessionForm,
    *,
    require_title: bool = False,
) -> dict[str, object]:
    title = payload.book_title.strip()
    if require_title:
        title = parse_book_title(title)

    (
        start_date,
        start_time,
        end_date,
        end_time,
        start_page,
        end_page,
    ) = collect_session_inputs(
        payload.start_date,
        payload.start_time,
        payload.end_date,
        payload.end_time,
        payload.start_page,
        payload.end_page,
    )
    start_at, end_at = validate_session_inputs(
        start_date,
        start_time,
        end_date,
        end_time,
        start_page,
        end_page,
    )
    return {
        "book_title": title,
        "start_date": start_date,
        "start_time": start_time,
        "end_date": end_date,
        "end_time": end_time,
        "start_page": start_page,
        "end_page": end_page,
        "start_at": start_at.isoformat(timespec="minutes"),
        "end_at": end_at.isoformat(timespec="minutes"),
    }


def _calendar_event_response(event: CalendarEvent) -> dict[str, object]:
    return {
        "summary": event.summary,
        "start": event.start.isoformat() if event.start else None,
        "end": event.end.isoformat() if event.end else None,
        "is_all_day": event.is_all_day,
    }


def _storage_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


def _calendar_autoload_enabled() -> bool:
    """Allow browser smoke tests to avoid contacting a real calendar account."""
    return os.environ.get("BOOK_TIMER_SKIP_CALENDAR_AUTOLOAD") != "1"


@app.get("/api/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/bootstrap")
def get_bootstrap() -> dict[str, object]:
    try:
        history = load_reading_history(HISTORY_PATH, STATE_PATH)
    except ReadingHistoryStoreError as exc:
        raise _storage_error(exc) from exc

    return {
        "form_state": _load_complete_form_state(),
        "book_titles": load_book_titles(STATE_PATH),
        **_history_response(history),
        "calendar_connected": (
            _calendar_autoload_enabled()
            and has_cached_calendar_credentials(TOKEN_PATH)
        ),
    }


@app.put("/api/state")
def put_state(payload: SaveStateRequest) -> dict[str, object]:
    titles = list(payload.book_titles)
    title = payload.book_title.strip()
    if title and title not in titles:
        titles.append(title)
    titles = sorted(set(titles), key=str.casefold)

    try:
        save_form_state(_form_state_from_payload(payload), titles, STATE_PATH)
    except SessionStateError as exc:
        raise _storage_error(exc) from exc

    return {"saved": True, "book_titles": titles}


@app.post("/api/session")
def post_session(payload: SessionForm) -> dict[str, object]:
    try:
        session = _validated_session(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    titles = load_book_titles(STATE_PATH)
    title = payload.book_title.strip()
    if title and title not in titles:
        titles.append(title)
        titles.sort(key=str.casefold)

    try:
        save_form_state(_form_state_from_payload(payload), titles, STATE_PATH)
    except SessionStateError as exc:
        raise _storage_error(exc) from exc

    return {"session": session, "book_titles": titles}


@app.get("/api/history")
def get_history() -> dict[str, object]:
    try:
        return _history_response(load_reading_history(HISTORY_PATH, STATE_PATH))
    except ReadingHistoryStoreError as exc:
        raise _storage_error(exc) from exc


@app.post("/api/history")
def post_history(payload: ReadingHistoryRequest) -> dict[str, object]:
    try:
        session_date = normalize_session_date(payload.session_date)
        book_title = parse_book_title(payload.book_title)
        history = load_reading_history(HISTORY_PATH, STATE_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReadingHistoryStoreError as exc:
        raise _storage_error(exc) from exc

    if has_same_reading_entry(history, session_date, book_title):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_entry",
                "message": "同じ日付の同じ本はすでに読了リストにあります。",
            },
        )

    if has_recent_same_book_title(history, session_date, book_title):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "recent_duplicate",
                "message": "同じ本は近い読了日から1ヶ月以上空けて登録してください。",
            },
        )

    if has_same_book_title(history, book_title) and not payload.allow_reread:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "confirm_reread",
                "message": "この本はすでに読了リストにあります。再読として追加しますか？",
            },
        )

    updated_history = normalize_reading_history(
        history
        + [
            {
                "session_date": session_date,
                "book_title": book_title,
            }
        ]
    )
    try:
        save_reading_history(updated_history, HISTORY_PATH)
        _remember_book_title(book_title)
    except (ReadingHistoryStoreError, SessionStateError) as exc:
        raise _storage_error(exc) from exc

    return _history_response(updated_history)


@app.delete("/api/history")
def delete_history(
    session_date: str = Query(max_length=10),
    book_title: str = Query(max_length=300),
) -> dict[str, object]:
    try:
        normalized_date = normalize_session_date(session_date)
        normalized_title = parse_book_title(book_title)
        history = load_reading_history(HISTORY_PATH, STATE_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReadingHistoryStoreError as exc:
        raise _storage_error(exc) from exc

    updated_history = [
        entry
        for entry in history
        if not (
            entry["session_date"] == normalized_date
            and entry["book_title"].casefold() == normalized_title.casefold()
        )
    ]
    if len(updated_history) == len(history):
        raise HTTPException(status_code=404, detail="読了履歴が見つかりません。")

    try:
        save_reading_history(updated_history, HISTORY_PATH)
    except ReadingHistoryStoreError as exc:
        raise _storage_error(exc) from exc
    return _history_response(updated_history)


@app.delete("/api/books")
def delete_book(book_title: str = Query(max_length=300)) -> dict[str, object]:
    normalized_title = book_title.strip()
    titles = load_book_titles(STATE_PATH)
    if normalized_title not in titles:
        raise HTTPException(status_code=404, detail="その書名は一覧にありません。")

    titles.remove(normalized_title)
    form_state = load_form_state(STATE_PATH)
    if form_state.get("book_title") == normalized_title:
        form_state["book_title"] = ""

    try:
        save_form_state(form_state, titles, STATE_PATH)
    except SessionStateError as exc:
        raise _storage_error(exc) from exc
    return {"book_titles": titles, "form_state": _load_complete_form_state()}


@app.get("/api/calendar/today")
def get_calendar_today() -> dict[str, object]:
    now = datetime.now().astimezone()
    try:
        events = get_today_events(
            now=now,
            credentials_path=CREDENTIALS_PATH,
            token_path=TOKEN_PATH,
        )
    except GoogleCalendarIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "date": now.date().isoformat(),
        "events": [_calendar_event_response(event) for event in events],
        "calendar_connected": True,
    }


@app.post("/api/calendar/events")
def post_calendar_event(payload: SessionForm) -> dict[str, object]:
    try:
        session = _validated_session(payload, require_title=True)
        event_link = create_reading_event(
            book_title=str(session["book_title"]),
            session_date=str(session["start_date"]),
            start_dt=datetime.fromisoformat(str(session["start_at"])),
            end_dt=datetime.fromisoformat(str(session["end_at"])),
            start_page=int(session["start_page"]),
            end_page=int(session["end_page"]),
            credentials_path=CREDENTIALS_PATH,
            token_path=TOKEN_PATH,
        )
        _remember_book_title(str(session["book_title"]))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GoogleCalendarIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SessionStateError as exc:
        raise _storage_error(exc) from exc

    return {
        "created": True,
        "event_link": event_link,
        "message": "Googleカレンダーに登録しました。",
    }


if (FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    index_path = FRONTEND_DIST / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)

    return {
        "message": "Frontend has not been built.",
        "command": "cd frontend && npm install && npm run build",
    }


def main() -> None:
    if os.environ.get("BOOK_TIMER_NO_BROWSER") != "1":
        threading.Timer(
            1.2,
            lambda: webbrowser.open("http://127.0.0.1:8000"),
        ).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
