from __future__ import annotations

from datetime import datetime
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
DEFAULT_CALENDAR_ID = "primary"
DEFAULT_CREDENTIALS_PATH = Path("credentials.json")
DEFAULT_TOKEN_PATH = Path("token.json")
DEPENDENCY_MESSAGE = (
    "Google Calendar連携を使うには "
    "`python -m pip install --upgrade "
    "google-api-python-client google-auth-httplib2 google-auth-oauthlib` "
    "を実行してください。"
)


class GoogleCalendarIntegrationError(RuntimeError):
    """Raised when Google Calendar integration cannot proceed."""


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
    build, http_error = _import_google_calendar_client()
    credentials = _load_credentials(credentials_path, token_path)
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    event_body = {
        "summary": f"読書: {book_title}",
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

    try:
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    except http_error as exc:
        raise GoogleCalendarIntegrationError(
            "Googleカレンダーへの登録に失敗しました。認証設定とネットワークを確認してください。"
        ) from exc

    return str(event.get("htmlLink", ""))


def _load_credentials(credentials_path: Path, token_path: Path):
    credentials_cls, request_cls, installed_app_flow_cls = _import_google_auth_client()
    credentials = None

    if token_path.exists():
        try:
            credentials = credentials_cls.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as exc:
            raise GoogleCalendarIntegrationError(
                "`token.json` の読み込みに失敗しました。削除して再認証してください。"
            ) from exc

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(request_cls())
        except Exception as exc:
            raise GoogleCalendarIntegrationError(
                "Google認証の更新に失敗しました。`token.json` を削除して再認証してください。"
            ) from exc
    else:
        if not credentials_path.exists():
            raise GoogleCalendarIntegrationError(
                "`credentials.json` が見つかりません。Google Cloud で Desktop app の OAuth "
                "クライアントを作成し、このフォルダに配置してください。"
            )

        try:
            flow = installed_app_flow_cls.from_client_secrets_file(
                str(credentials_path),
                SCOPES,
            )
            credentials = flow.run_local_server(port=0)
        except Exception as exc:
            raise GoogleCalendarIntegrationError(
                "Google認証に失敗しました。ブラウザでのログインと OAuth 設定を確認してください。"
            ) from exc

    try:
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    except OSError as exc:
        raise GoogleCalendarIntegrationError(
            "`token.json` を保存できませんでした。書き込み権限を確認してください。"
        ) from exc

    return credentials


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


def _to_rfc3339(value: datetime) -> str:
    """Convert a local datetime to the RFC3339 string accepted by Google Calendar."""
    return value.astimezone().isoformat(timespec="seconds")
