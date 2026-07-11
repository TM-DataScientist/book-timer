from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, tzinfo
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
DEFAULT_CALENDAR_ID = "primary"
DEFAULT_CREDENTIALS_PATH = Path("credentials.json")
DEFAULT_TOKEN_PATH = Path("token.json")
CREDENTIALS_GLOB_PATTERNS = (
    "credentials.json",
    "client_secret_*.json",
    "*.apps.googleusercontent.com.json",
)
DEPENDENCY_MESSAGE = (
    "Google Calendar連携を使うには "
    "`python -m pip install --upgrade "
    "google-api-python-client google-auth-httplib2 google-auth-oauthlib` "
    "を実行してください。"
)


class GoogleCalendarIntegrationError(RuntimeError):
    """Raised when Google Calendar integration cannot proceed."""


@dataclass(frozen=True)
class CalendarEvent:
    """A calendar event normalized for display by the application."""

    summary: str
    start: datetime | None
    end: datetime | None
    is_all_day: bool


def get_today_events(
    *,
    now: datetime | None = None,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> list[CalendarEvent]:
    """Return events overlapping the local calendar day containing ``now``."""
    current_time = now or datetime.now().astimezone()
    if current_time.tzinfo is None:
        current_time = current_time.astimezone()

    local_timezone = current_time.tzinfo
    if local_timezone is None:
        raise GoogleCalendarIntegrationError(
            "ローカルタイムゾーンを取得できませんでした。"
        )

    day_start = datetime.combine(
        current_time.date(),
        time.min,
        tzinfo=local_timezone,
    )
    day_end = day_start + timedelta(days=1)
    service, http_error = _build_calendar_service(credentials_path, token_path)
    events: list[CalendarEvent] = []
    page_token: str | None = None

    try:
        while True:
            request_parameters = {
                "calendarId": calendar_id,
                "timeMin": _to_rfc3339(day_start),
                "timeMax": _to_rfc3339(day_end),
                "singleEvents": True,
                "orderBy": "startTime",
                "showDeleted": False,
                "maxResults": 2500,
            }
            if page_token:
                request_parameters["pageToken"] = page_token

            response = service.events().list(**request_parameters).execute()
            for event_data in response.get("items", []):
                calendar_event = _normalize_calendar_event(
                    event_data,
                    local_timezone,
                )
                if calendar_event is not None:
                    events.append(calendar_event)

            page_token = response.get("nextPageToken")
            if not page_token:
                break
    except http_error as exc:
        raise GoogleCalendarIntegrationError(
            "今日の予定を取得できませんでした。認証設定とネットワークを確認してください。"
        ) from exc
    except Exception as exc:
        raise GoogleCalendarIntegrationError(
            "今日の予定の取得中にエラーが発生しました。認証設定とネットワークを確認してください。"
        ) from exc

    return events


def has_cached_calendar_credentials(
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> bool:
    """Return whether a saved OAuth token is available for automatic loading."""
    return token_path.is_file()


def create_reading_event(
    *,
    book_title: str,
    session_date: str,
    start_dt: datetime,
    end_dt: datetime,
    start_page: int,
    end_page: int,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> str:
    """Insert a reading session event into Google Calendar and return its link."""
    event_body = {
        "summary": _build_event_summary(book_title, start_page, end_page),
        "description": "\n".join(
            [
                f"書名: {book_title}",
                f"読書日: {session_date}",
                f"開始ページ: {start_page}",
                f"終了ページ: {end_page}",
                "登録元: Book Timer",
            ]
        ),
        "start": {"dateTime": _to_rfc3339(start_dt)},
        "end": {"dateTime": _to_rfc3339(end_dt)},
        "extendedProperties": {
            "private": {
                "bookTimer": "true",
                "bookTitle": book_title,
                "startPage": str(start_page),
                "endPage": str(end_page),
            }
        },
    }
    return _insert_event_body(
        event_body,
        calendar_id=calendar_id,
        credentials_path=credentials_path,
        token_path=token_path,
    )


def create_calendar_event(
    *,
    summary: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
    location: str = "",
    calendar_id: str = DEFAULT_CALENDAR_ID,
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> str:
    """Insert a generic event into Google Calendar and return its link."""
    if end_dt <= start_dt:
        raise GoogleCalendarIntegrationError(
            "Googleカレンダーに登録する終了日時は開始日時より後にしてください。"
        )

    event_body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": _to_rfc3339(start_dt)},
        "end": {"dateTime": _to_rfc3339(end_dt)},
    }
    return _insert_event_body(
        event_body,
        calendar_id=calendar_id,
        credentials_path=credentials_path,
        token_path=token_path,
    )


def _insert_event_body(
    event_body: dict,
    *,
    calendar_id: str,
    credentials_path: Path,
    token_path: Path,
) -> str:
    """Insert a prepared event body into Google Calendar and return its link."""
    service, http_error = _build_calendar_service(credentials_path, token_path)

    try:
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    except http_error as exc:
        raise GoogleCalendarIntegrationError(
            "Googleカレンダーへの登録に失敗しました。認証設定とネットワークを確認してください。"
        ) from exc
    except Exception as exc:
        raise GoogleCalendarIntegrationError(
            "Googleカレンダーへの登録中にエラーが発生しました。認証設定とネットワークを確認してください。"
        ) from exc

    return str(event.get("htmlLink", ""))


def _build_calendar_service(credentials_path: Path, token_path: Path):
    """Create an authenticated Calendar API service and its HTTP error type."""
    build, http_error = _import_google_calendar_client()
    credentials = _load_credentials(credentials_path, token_path)
    service = build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )
    return service, http_error


def _normalize_calendar_event(
    event_data: dict,
    local_timezone: tzinfo,
) -> CalendarEvent | None:
    """Convert a Calendar API event resource into a display-safe value."""
    if event_data.get("status") == "cancelled":
        return None

    summary = str(event_data.get("summary") or "").strip() or "(タイトルなし)"
    start_data = event_data.get("start") or {}
    end_data = event_data.get("end") or {}

    if start_data.get("date"):
        return CalendarEvent(
            summary=summary,
            start=None,
            end=None,
            is_all_day=True,
        )

    start = _parse_event_datetime(start_data.get("dateTime"), local_timezone)
    if start is None:
        return None

    return CalendarEvent(
        summary=summary,
        start=start,
        end=_parse_event_datetime(end_data.get("dateTime"), local_timezone),
        is_all_day=False,
    )


def _parse_event_datetime(
    value: object,
    local_timezone: tzinfo,
) -> datetime | None:
    """Parse an RFC3339 event timestamp and convert it to local time."""
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_timezone)
    return parsed.astimezone(local_timezone)


def _load_credentials(credentials_path: Path, token_path: Path):
    credentials_cls, request_cls, installed_app_flow_cls = _import_google_auth_client()
    credentials = _load_cached_credentials(token_path, credentials_cls)

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(request_cls())
        except Exception:
            credentials = None
            _discard_cached_token(token_path)

    if not credentials or not credentials.valid:
        credentials = _authorize_with_browser(
            credentials_path,
            installed_app_flow_cls,
        )

    try:
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    except OSError as exc:
        raise GoogleCalendarIntegrationError(
            "`token.json` を保存できませんでした。書き込み権限を確認してください。"
        ) from exc

    return credentials


def _load_cached_credentials(token_path: Path, credentials_cls):
    """Load cached user credentials when available, ignoring unusable tokens."""
    if not token_path.exists():
        return None

    try:
        return credentials_cls.from_authorized_user_file(str(token_path), SCOPES)
    except Exception:
        _discard_cached_token(token_path)
        return None


def _authorize_with_browser(credentials_path: Path, installed_app_flow_cls):
    """Start the OAuth browser flow and return fresh user credentials."""
    resolved_credentials_path = _resolve_credentials_path(credentials_path)

    if resolved_credentials_path is None:
        raise GoogleCalendarIntegrationError(
            "OAuth クライアント JSON が見つかりません。Google Cloud で Desktop app "
            "の OAuth クライアントを作成し、`credentials.json` または "
            "`client_secret_...json` をこのフォルダに配置してください。"
        )

    try:
        flow = installed_app_flow_cls.from_client_secrets_file(
            str(resolved_credentials_path),
            SCOPES,
        )
        return flow.run_local_server(port=0)
    except Exception as exc:
        raise GoogleCalendarIntegrationError(
            "Google認証に失敗しました。ブラウザでのログインと OAuth 設定を確認してください。"
        ) from exc


def _discard_cached_token(token_path: Path) -> None:
    """Best-effort cleanup of an unusable cached token before reauth."""
    try:
        token_path.unlink(missing_ok=True)
    except OSError:
        return


def _import_google_auth_client():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise GoogleCalendarIntegrationError(DEPENDENCY_MESSAGE) from exc

    return Credentials, Request, InstalledAppFlow


def _import_google_calendar_client():
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise GoogleCalendarIntegrationError(DEPENDENCY_MESSAGE) from exc

    return build, HttpError


def _resolve_credentials_path(credentials_path: Path) -> Path | None:
    """Resolve the OAuth client JSON from explicit and common downloaded filenames."""
    if credentials_path.exists():
        return credentials_path

    parent_dir = credentials_path.parent if credentials_path.parent != Path("") else Path(".")

    for pattern in CREDENTIALS_GLOB_PATTERNS:
        matches = sorted(parent_dir.glob(pattern))
        if matches:
            return matches[0]

    return None


def _to_rfc3339(value: datetime) -> str:
    """Convert a local datetime to the RFC3339 string accepted by Google Calendar."""
    return value.astimezone().isoformat(timespec="seconds")


def _build_event_summary(book_title: str, start_page: int, end_page: int) -> str:
    """Build a concise calendar title with page range."""
    return f"読書：{book_title}(P.{start_page}-{end_page})"
