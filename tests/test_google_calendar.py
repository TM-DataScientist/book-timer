from pathlib import Path

from modules import google_calendar


class DummyCredentials:
    next_cached = None

    def __init__(
        self,
        *,
        valid: bool,
        expired: bool = False,
        refresh_token: str | None = None,
        refresh_error: Exception | None = None,
        json_text: str = '{"token": "dummy"}',
    ) -> None:
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refresh_error = refresh_error
        self.json_text = json_text
        self.refresh_calls = 0

    @classmethod
    def from_authorized_user_file(cls, path: str, scopes: list[str]):
        return cls.next_cached

    def refresh(self, request) -> None:
        self.refresh_calls += 1
        if self.refresh_error is not None:
            raise self.refresh_error
        self.valid = True
        self.expired = False

    def to_json(self) -> str:
        return self.json_text


class DummyFlow:
    fresh_credentials = None
    created_from = None
    run_calls = 0

    @classmethod
    def from_client_secrets_file(cls, path: str, scopes: list[str]):
        cls.created_from = Path(path)
        return cls()

    def run_local_server(self, port: int = 0):
        type(self).run_calls += 1
        return type(self).fresh_credentials


class DummyRequest:
    pass


class DummyEventsResource:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def insert(self, **kwargs):
        return self

    def execute(self):
        if self.error is not None:
            raise self.error
        return {"htmlLink": "https://calendar.google.com/event"}


class DummyCalendarService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def events(self):
        return DummyEventsResource(self.error)


def install_auth_stubs(monkeypatch):
    monkeypatch.setattr(
        google_calendar,
        "_import_google_auth_client",
        lambda: (DummyCredentials, DummyRequest, DummyFlow),
    )


def test_refresh_failure_falls_back_to_browser_reauth(tmp_path, monkeypatch):
    install_auth_stubs(monkeypatch)
    credentials_path = tmp_path / "client_secret.json"
    credentials_path.write_text("{}", encoding="utf-8")
    token_path = tmp_path / "token.json"
    token_path.write_text("stale", encoding="utf-8")

    cached = DummyCredentials(
        valid=False,
        expired=True,
        refresh_token="refresh-token",
        refresh_error=RuntimeError("expired"),
        json_text='{"token": "stale"}',
    )
    fresh = DummyCredentials(valid=True, json_text='{"token": "fresh"}')
    DummyCredentials.next_cached = cached
    DummyFlow.fresh_credentials = fresh
    DummyFlow.created_from = None
    DummyFlow.run_calls = 0

    credentials = google_calendar._load_credentials(credentials_path, token_path)

    assert credentials is fresh
    assert cached.refresh_calls == 1
    assert DummyFlow.created_from == credentials_path
    assert DummyFlow.run_calls == 1
    assert token_path.read_text(encoding="utf-8") == '{"token": "fresh"}'


def test_invalid_cached_token_falls_back_to_browser_reauth(tmp_path, monkeypatch):
    install_auth_stubs(monkeypatch)
    credentials_path = tmp_path / "client_secret.json"
    credentials_path.write_text("{}", encoding="utf-8")
    token_path = tmp_path / "token.json"
    token_path.write_text("broken", encoding="utf-8")

    def raise_on_load(path: str, scopes: list[str]):
        raise ValueError("bad token")

    monkeypatch.setattr(
        DummyCredentials,
        "from_authorized_user_file",
        classmethod(lambda cls, path, scopes: raise_on_load(path, scopes)),
    )
    fresh = DummyCredentials(valid=True, json_text='{"token": "fresh-after-bad-cache"}')
    DummyFlow.fresh_credentials = fresh
    DummyFlow.created_from = None
    DummyFlow.run_calls = 0

    credentials = google_calendar._load_credentials(credentials_path, token_path)

    assert credentials is fresh
    assert DummyFlow.created_from == credentials_path
    assert DummyFlow.run_calls == 1
    assert token_path.read_text(encoding="utf-8") == '{"token": "fresh-after-bad-cache"}'


def test_create_reading_event_wraps_unexpected_insert_errors(monkeypatch):
    monkeypatch.setattr(
        google_calendar,
        "_import_google_calendar_client",
        lambda: (
            lambda *args, **kwargs: DummyCalendarService(ValueError("network down")),
            RuntimeError,
        ),
    )
    monkeypatch.setattr(google_calendar, "_load_credentials", lambda *args, **kwargs: object())

    try:
        google_calendar.create_reading_event(
            book_title="Test Book",
            session_date="2026-04-04",
            start_dt=google_calendar.datetime(2026, 4, 4, 9, 0),
            end_dt=google_calendar.datetime(2026, 4, 4, 10, 0),
            start_page=1,
            end_page=10,
        )
    except google_calendar.GoogleCalendarIntegrationError as exc:
        assert "Googleカレンダーへの登録" in str(exc)
    else:
        raise AssertionError("GoogleCalendarIntegrationError was not raised")
