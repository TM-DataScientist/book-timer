from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import web_app
from modules.google_calendar import CalendarEvent


client = TestClient(web_app.app)


def session_payload(**overrides):
    payload = {
        "book_title": "Clean Code",
        "start_date": "2026-07-11",
        "start_time": "22:00",
        "end_date": "2026-07-11",
        "end_time": "25:00",
        "start_page": "10",
        "end_page": "40",
    }
    payload.update(overrides)
    return payload


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_session_endpoint_validates_and_persists_form(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "STATE_PATH", tmp_path / "state.json")

    response = client.post("/api/session", json=session_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["end_at"] == "2026-07-12T01:00"
    assert body["session"]["start_page"] == 10
    assert body["book_titles"] == ["Clean Code"]


def test_bootstrap_returns_history_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(web_app, "TOKEN_PATH", tmp_path / "token.json")
    monkeypatch.setattr(
        web_app,
        "load_reading_history",
        lambda *args: [
            {"session_date": "2026-07-10", "book_title": "Book A"},
            {"session_date": "2026-06-01", "book_title": "Book B"},
        ],
    )

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total"] == 2
    assert body["summary"]["yearly"] == [{"period": "2026", "count": 2}]
    assert body["calendar_connected"] is False


def test_history_endpoint_requires_confirmation_for_reread(monkeypatch):
    saved_history = []
    existing_history = [
        {"session_date": "2026-05-01", "book_title": "Clean Code"}
    ]
    monkeypatch.setattr(
        web_app,
        "load_reading_history",
        lambda *args: list(existing_history),
    )
    monkeypatch.setattr(
        web_app,
        "save_reading_history",
        lambda history, path: saved_history.extend(history),
    )
    monkeypatch.setattr(web_app, "_remember_book_title", lambda title: [title])

    confirmation_response = client.post(
        "/api/history",
        json={
            "session_date": "2026-07-11",
            "book_title": "Clean Code",
        },
    )
    confirmed_response = client.post(
        "/api/history",
        json={
            "session_date": "2026-07-11",
            "book_title": "Clean Code",
            "allow_reread": True,
        },
    )

    assert confirmation_response.status_code == 409
    assert confirmation_response.json()["detail"]["code"] == "confirm_reread"
    assert confirmed_response.status_code == 200
    assert len(saved_history) == 2


def test_calendar_today_serializes_all_day_and_timed_events(monkeypatch):
    japan_timezone = timezone(timedelta(hours=9))
    monkeypatch.setattr(
        web_app,
        "get_today_events",
        lambda **kwargs: [
            CalendarEvent(
                summary="終日予定",
                start=None,
                end=None,
                is_all_day=True,
            ),
            CalendarEvent(
                summary="朝会",
                start=datetime(2026, 7, 11, 9, 0, tzinfo=japan_timezone),
                end=datetime(2026, 7, 11, 9, 30, tzinfo=japan_timezone),
                is_all_day=False,
            ),
        ],
    )

    response = client.get("/api/calendar/today")

    assert response.status_code == 200
    events = response.json()["events"]
    assert events[0]["is_all_day"] is True
    assert events[1]["start"] == "2026-07-11T09:00:00+09:00"
