import queue
import threading
import tkinter as tk
from calendar import monthrange
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk
from datetime import datetime, timedelta

from modules.google_calendar import (
    GoogleCalendarIntegrationError,
    create_reading_event,
)
from modules.reading_history_store import (
    ReadingHistoryStoreError,
    load_reading_history,
    normalize_reading_history,
    save_reading_history,
    summarize_reading_history,
)
from modules.session_state import (
    SessionStateError,
    load_book_titles,
    load_form_state,
    save_form_state,
)

DEFAULT_WIDTH = 560
DEFAULT_HEIGHT = 620
DATE_FORMAT = "%Y-%m-%d"
APP_TITLE = "読書タイマー"
SETUP_TITLE = "セッション設定"
BOOK_TITLE_LABEL = "書名"
START_DATE_LABEL = "開始日"
END_DATE_LABEL = "終了日"
START_TIME_LABEL = "開始時刻"
END_TIME_LABEL = "終了時刻"
START_PAGE_LABEL = "開始ページ"
END_PAGE_LABEL = "終了ページ"
APPLY_LABEL = "反映"
REGISTER_CALENDAR_LABEL = "Googleカレンダーに登録"
ADD_READING_HISTORY_LABEL = "読了リストに追加"
DELETE_BOOK_LABEL = "削除"
EMPTY_BOOK_TEXT = "書名 --"
EMPTY_TIME_TEXT = "開始 ----/--/-- --:-- / 終了 ----/--/-- --:--"
EMPTY_PAGE_TEXT = "ページ -- -> --"
READING_HISTORY_TITLE = "読了リスト"
LATEST_READING_EMPTY_TEXT = "最新の読了: まだ記録がありません。"
READING_HISTORY_EMPTY_TEXT = "まだ読了履歴がありません。"
READY_TEXT = "読書セッションを入力して「反映」を押してください。"
CALENDAR_PROGRESS_TEXT = "Googleカレンダーへ登録中です..."
CALENDAR_SUCCESS_TEXT = "Googleカレンダーに登録しました。"
CALENDAR_UNEXPECTED_ERROR_TEXT = (
    "Googleカレンダーへの登録中に予期しないエラーが発生しました。"
)
BOOK_DELETED_TEXT = "書名一覧から削除しました。"
READING_HISTORY_SUCCESS_TEXT = "読了リストに追加しました。"
READING_STATS_TITLE = "読了冊数"
READING_STATS_EMPTY_TEXT = "読了冊数: 0 冊"
DUPLICATE_READING_ENTRY_TEXT = "同じ日付の同じ本はすでに読了リストにあります。"
DUPLICATE_RECENT_BOOK_TEXT = "同じ本は近い読了日から1ヶ月以上空けて登録してください。"
DUPLICATE_BOOK_CONFIRM_TITLE = "同じ本の登録"
DUPLICATE_BOOK_CONFIRM_MESSAGE = "この本はすでに読了リストにあります。再読として追加しますか？"
DEFAULT_START_TIME = "08:00"
DEFAULT_END_TIME = "24:00"
CALENDAR_RESULT_POLL_MS = 100


def parse_time_on_date(time_text: str, reference: datetime) -> datetime:
    """Parse HH:MM text on the reference date, allowing hours beyond 24."""
    normalized = time_text.strip()

    try:
        hour_text, minute_text = normalized.split(":", maxsplit=1)
        hours = int(hour_text)
        minutes = int(minute_text)
    except ValueError as exc:
        raise ValueError("Invalid time format") from exc

    if hours < 0 or minutes < 0 or minutes > 59:
        raise ValueError("Invalid time format")

    midnight = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight + timedelta(hours=hours, minutes=minutes)


def parse_session_date(date_text: str) -> datetime:
    """Parse YYYY-MM-DD text and return the date at midnight."""
    try:
        parsed = datetime.strptime(date_text.strip(), DATE_FORMAT)
    except ValueError as exc:
        raise ValueError("日付は YYYY-MM-DD 形式で入力してください。") from exc

    return parsed.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_page(page_text: str, label: str) -> int:
    """Convert page input to an integer with a readable validation message."""
    try:
        return int(page_text.strip())
    except ValueError as exc:
        raise ValueError(f"{label}は整数で入力してください。") from exc


def parse_book_title(
    book_text: str,
    *,
    missing_message: str = "書名を入力してください。",
) -> str:
    """Require a non-empty book title and return the normalized value."""
    title = book_text.strip()
    if not title:
        raise ValueError(missing_message)
    return title


def build_latest_reading_text(reading_history: list[dict[str, str]]) -> str:
    """Build the latest reading summary label from the saved history."""
    if not reading_history:
        return LATEST_READING_EMPTY_TEXT

    latest_entry = reading_history[0]
    return (
        f"最新の読了: {latest_entry['session_date']} / "
        f"{latest_entry['book_title']}"
    )


def format_reading_history_entry(entry: dict[str, str]) -> str:
    """Render one reading-history row for the on-screen list."""
    return f"{entry['session_date']}  {entry['book_title']}"


def build_reading_stats_lines(reading_history: list[dict[str, str]]) -> list[str]:
    """Build compact count lines for the reading-history stats list."""
    summary = summarize_reading_history(reading_history)
    total = int(summary["total"])
    if total == 0:
        return [READING_STATS_EMPTY_TEXT]

    yearly_counts = list(summary["yearly"])
    monthly_counts = list(summary["monthly"])
    max_count = max(
        [count for _, count in yearly_counts + monthly_counts],
        default=total,
    )

    def format_count(label: str, count: int) -> str:
        bar_length = max(1, round((count / max_count) * 10))
        return f"{label} {'#' * bar_length} {count} 冊"

    lines = [f"累計 {'#' * 10} {total} 冊"]
    lines.extend(format_count(year, count) for year, count in yearly_counts[:3])
    lines.extend(format_count(month, count) for month, count in monthly_counts[:6])
    return lines


def has_same_reading_entry(
    reading_history: list[dict[str, str]],
    session_date: str,
    book_title: str,
) -> bool:
    """Return whether the same normalized title is registered on the same date."""
    normalized_title = book_title.casefold()
    return any(
        entry["session_date"] == session_date
        and entry["book_title"].casefold() == normalized_title
        for entry in reading_history
    )


def add_months(value: datetime, month_count: int) -> datetime:
    """Return a date shifted by whole calendar months."""
    month_index = value.month - 1 + month_count
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def is_less_than_one_month_apart(first_date: str, second_date: str) -> bool:
    """Return whether two YYYY-MM-DD dates are separated by less than one month."""
    first_dt = parse_session_date(first_date)
    second_dt = parse_session_date(second_date)
    earlier_dt, later_dt = sorted((first_dt, second_dt))
    return add_months(earlier_dt, 1) > later_dt


def has_recent_same_book_title(
    reading_history: list[dict[str, str]],
    session_date: str,
    book_title: str,
) -> bool:
    """Return whether the same title was read less than one month apart."""
    normalized_title = book_title.casefold()
    return any(
        entry["book_title"].casefold() == normalized_title
        and is_less_than_one_month_apart(entry["session_date"], session_date)
        for entry in reading_history
    )


def has_same_book_title(
    reading_history: list[dict[str, str]],
    book_title: str,
) -> bool:
    """Return whether the same normalized title exists anywhere in history."""
    normalized_title = book_title.casefold()
    return any(
        entry["book_title"].casefold() == normalized_title
        for entry in reading_history
    )


def normalize_session_date(date_text: str) -> str:
    """Normalize a supported date input to YYYY-MM-DD."""
    return parse_session_date(date_text).strftime(DATE_FORMAT)


def validate_session_inputs(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    start_page: int,
    end_page: int,
) -> tuple[datetime, datetime]:
    """Validate date/time/page inputs and return parsed datetimes."""
    start_reference = parse_session_date(start_date)
    end_reference = parse_session_date(end_date)

    try:
        start_dt = parse_time_on_date(start_time, start_reference)
        end_dt = parse_time_on_date(end_time, end_reference)
    except ValueError as exc:
        raise ValueError(
            "時刻は HH:MM 形式で入力してください。24:00 以降は翌日の時刻として扱います。"
        ) from exc

    if end_dt <= start_dt:
        raise ValueError("終了時刻は開始時刻より後にしてください。")

    if end_page < start_page:
        raise ValueError("終了ページは開始ページ以上にしてください。")

    return start_dt, end_dt


def collect_session_inputs(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    start_page_text: str,
    end_page_text: str,
) -> tuple[str, str, str, str, int, int]:
    """Parse and validate form values into a session tuple."""
    normalized_start_date = normalize_session_date(start_date)
    normalized_end_date = normalize_session_date(end_date)
    start_page = parse_page(start_page_text, START_PAGE_LABEL)
    end_page = parse_page(end_page_text, END_PAGE_LABEL)
    validate_session_inputs(
        normalized_start_date,
        start_time,
        normalized_end_date,
        end_time,
        start_page,
        end_page,
    )
    return (
        normalized_start_date,
        start_time,
        normalized_end_date,
        end_time,
        start_page,
        end_page,
    )


def calculate_pages(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    start_page: int,
    end_page: int,
) -> str:
    """Return a friendly status message describing the current reading progress."""
    now = datetime.now()

    try:
        start_dt, end_dt = validate_session_inputs(
            start_date,
            start_time,
            end_date,
            end_time,
            start_page,
            end_page,
        )
    except ValueError as exc:
        return str(exc)

    if now < start_dt:
        minutes = int((start_dt - now).total_seconds() // 60)
        return f"読書開始まであと {minutes} 分です。"

    if now >= end_dt:
        return f"読書セッションは終了しました。最終ページ {end_page} を確認してください。"

    total_minutes = (end_dt - start_dt).total_seconds()
    elapsed_minutes = (now - start_dt).total_seconds()
    progress = min(max(elapsed_minutes / total_minutes, 0), 1)

    total_pages = max(end_page - start_page, 0) + 1
    current_page = start_page + int(total_pages * progress)
    current_page = min(max(current_page, start_page), end_page)

    return f"現在の推定位置: {current_page} ページ"


def run_app() -> None:
    """Create and run the Tkinter application."""
    saved_form_state = load_form_state()
    saved_book_titles = load_book_titles()
    startup_error_message = ""

    try:
        saved_reading_history = load_reading_history()
    except ReadingHistoryStoreError as exc:
        saved_reading_history = []
        startup_error_message = str(exc)

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
    root.minsize(460, 420)
    root.resizable(True, True)

    info_font = tkfont.Font(family="Helvetica", size=12)
    progress_font = tkfont.Font(family="Helvetica", size=14)
    combobox_style = ttk.Style(root)
    combobox_style.configure("BookTimer.TCombobox", font=("Helvetica", 12))
    book_titles = list(saved_book_titles)
    reading_history = list(saved_reading_history)

    saved_book_title = saved_form_state.get("book_title", "").strip()
    if saved_book_title and saved_book_title not in book_titles:
        book_titles.append(saved_book_title)
        book_titles.sort(key=str.casefold)

    book_title_var = tk.StringVar(value=saved_form_state.get("book_title", ""))
    default_date = datetime.now().strftime(DATE_FORMAT)
    saved_start_date = saved_form_state.get(
        "start_date",
        saved_form_state.get("session_date", default_date),
    )
    saved_end_date = saved_form_state.get(
        "end_date",
        saved_form_state.get("session_date", saved_start_date),
    )
    start_date_var = tk.StringVar(value=saved_start_date)
    end_date_var = tk.StringVar(value=saved_end_date)
    start_time_var = tk.StringVar(
        value=saved_form_state.get("start_time", DEFAULT_START_TIME)
    )
    end_time_var = tk.StringVar(value=saved_form_state.get("end_time", DEFAULT_END_TIME))
    start_page_var = tk.StringVar(value=saved_form_state.get("start_page", ""))
    end_page_var = tk.StringVar(value=saved_form_state.get("end_page", ""))
    error_var = tk.StringVar(value=startup_error_message)
    calendar_status_var = tk.StringVar()
    book_label_var = tk.StringVar(value=EMPTY_BOOK_TEXT)
    time_label_var = tk.StringVar(value=EMPTY_TIME_TEXT)
    page_label_var = tk.StringVar(value=EMPTY_PAGE_TEXT)
    latest_reading_var = tk.StringVar(value=build_latest_reading_text(reading_history))
    current_session: tuple[str, str, str, str, int, int] | None = None
    scheduled_update_id: str | None = None
    calendar_result_queue: queue.Queue[tuple[str, str]] = queue.Queue()
    calendar_poll_id: str | None = None
    calendar_registration_in_progress = False

    form_frame = tk.LabelFrame(root, text=SETUP_TITLE, padx=12, pady=12)
    form_frame.pack(fill="x", padx=16, pady=(16, 8))
    form_frame.columnconfigure(1, weight=1)
    form_frame.columnconfigure(2, weight=1)
    form_frame.columnconfigure(3, weight=1)

    tk.Label(form_frame, text=BOOK_TITLE_LABEL, font=info_font).grid(
        row=0, column=0, padx=(0, 8), pady=4, sticky="w"
    )
    book_title_combobox = ttk.Combobox(
        form_frame,
        textvariable=book_title_var,
        values=tuple(book_titles),
        style="BookTimer.TCombobox",
    )
    book_title_combobox.grid(
        row=0,
        column=1,
        columnspan=2,
        padx=(0, 12),
        pady=4,
        sticky="ew",
    )
    delete_book_button = tk.Button(
        form_frame,
        text=DELETE_BOOK_LABEL,
        font=info_font,
        command=lambda: delete_selected_book(),
    )
    delete_book_button.grid(row=0, column=3, pady=4, sticky="ew")

    tk.Label(form_frame, text=START_DATE_LABEL, font=info_font).grid(
        row=1, column=0, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=start_date_var, font=info_font).grid(
        row=1, column=1, padx=(0, 12), pady=4, sticky="ew"
    )

    tk.Label(form_frame, text=START_TIME_LABEL, font=info_font).grid(
        row=1, column=2, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=start_time_var, font=info_font).grid(
        row=1, column=3, pady=4, sticky="ew"
    )

    tk.Label(form_frame, text=END_DATE_LABEL, font=info_font).grid(
        row=2, column=0, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=end_date_var, font=info_font).grid(
        row=2, column=1, padx=(0, 12), pady=4, sticky="ew"
    )

    tk.Label(form_frame, text=END_TIME_LABEL, font=info_font).grid(
        row=2, column=2, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=end_time_var, font=info_font).grid(
        row=2, column=3, pady=4, sticky="ew"
    )

    tk.Label(form_frame, text=START_PAGE_LABEL, font=info_font).grid(
        row=3, column=0, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=start_page_var, font=info_font).grid(
        row=3, column=1, padx=(0, 12), pady=4, sticky="ew"
    )

    tk.Label(form_frame, text=END_PAGE_LABEL, font=info_font).grid(
        row=3, column=2, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=end_page_var, font=info_font).grid(
        row=3, column=3, pady=4, sticky="ew"
    )

    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 8))

    apply_button = tk.Button(
        button_frame,
        text=APPLY_LABEL,
        font=info_font,
        command=lambda: apply_session(),
    )
    apply_button.pack(
        side="left",
        padx=(0, 8),
    )
    add_reading_history_button = tk.Button(
        button_frame,
        text=ADD_READING_HISTORY_LABEL,
        font=info_font,
        command=lambda: add_reading_history_entry(),
    )
    add_reading_history_button.pack(side="left", padx=(0, 8))
    register_calendar_button = tk.Button(
        button_frame,
        text=REGISTER_CALENDAR_LABEL,
        font=info_font,
        command=lambda: register_calendar_event(),
    )
    register_calendar_button.pack(side="left")

    info_frame = tk.Frame(root)
    info_frame.pack(pady=(8, 8))

    tk.Label(
        info_frame,
        textvariable=book_label_var,
        font=info_font,
    ).pack()

    tk.Label(
        info_frame,
        textvariable=time_label_var,
        font=info_font,
    ).pack()

    tk.Label(
        info_frame,
        textvariable=page_label_var,
        font=info_font,
    ).pack()

    progress_label = tk.Label(
        root,
        text=READY_TEXT,
        font=progress_font,
        wraplength=470,
        justify="center",
    )
    progress_label.pack(padx=16, pady=(8, 12))

    error_label = tk.Label(
        root,
        textvariable=error_var,
        font=info_font,
        fg="red",
        wraplength=470,
        justify="center",
    )
    error_label.pack(padx=16, pady=(0, 8))

    calendar_status_label = tk.Label(
        root,
        textvariable=calendar_status_var,
        font=info_font,
        fg="darkgreen",
        wraplength=470,
        justify="center",
    )
    calendar_status_label.pack(padx=16, pady=(0, 12))

    reading_history_frame = tk.LabelFrame(root, text=READING_HISTORY_TITLE, padx=12, pady=12)
    reading_history_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
    reading_history_frame.columnconfigure(0, weight=1)
    reading_history_frame.rowconfigure(2, weight=1)

    latest_reading_label = tk.Label(
        reading_history_frame,
        textvariable=latest_reading_var,
        font=info_font,
        anchor="w",
        justify="left",
    )
    latest_reading_label.grid(row=0, column=0, sticky="ew")

    reading_stats_frame = tk.LabelFrame(
        reading_history_frame,
        text=READING_STATS_TITLE,
        padx=8,
        pady=8,
    )
    reading_stats_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
    reading_stats_frame.columnconfigure(0, weight=1)

    reading_stats_listbox = tk.Listbox(
        reading_stats_frame,
        font=info_font,
        height=4,
        activestyle="none",
    )
    reading_stats_listbox.grid(row=0, column=0, sticky="ew")

    reading_history_listbox = tk.Listbox(
        reading_history_frame,
        font=info_font,
        height=6,
        activestyle="none",
    )
    reading_history_listbox.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

    def schedule_progress_update(delay_ms: int) -> None:
        nonlocal scheduled_update_id
        if scheduled_update_id is not None:
            root.after_cancel(scheduled_update_id)
            scheduled_update_id = None
        scheduled_update_id = root.after(delay_ms, update_progress)

    def schedule_calendar_result_poll(delay_ms: int) -> None:
        nonlocal calendar_poll_id
        if calendar_poll_id is not None:
            root.after_cancel(calendar_poll_id)
            calendar_poll_id = None
        calendar_poll_id = root.after(delay_ms, process_calendar_result)

    def set_calendar_registration_state(is_running: bool) -> None:
        nonlocal calendar_registration_in_progress
        calendar_registration_in_progress = is_running
        register_calendar_button.config(state="disabled" if is_running else "normal")
        apply_button.config(state="disabled" if is_running else "normal")
        add_reading_history_button.config(state="disabled" if is_running else "normal")

    def get_form_state() -> dict[str, str]:
        start_date = start_date_var.get().strip()
        end_date = end_date_var.get().strip()
        return {
            "book_title": book_title_var.get().strip(),
            "start_date": start_date,
            "end_date": end_date,
            "session_date": start_date,
            "start_time": start_time_var.get().strip(),
            "end_time": end_time_var.get().strip(),
            "start_page": start_page_var.get().strip(),
            "end_page": end_page_var.get().strip(),
        }

    def update_book_title_choices() -> None:
        book_title_combobox["values"] = tuple(book_titles)

    def remember_book_title(book_title: str) -> None:
        normalized_title = book_title.strip()
        if not normalized_title or normalized_title in book_titles:
            return

        book_titles.append(normalized_title)
        book_titles.sort(key=str.casefold)
        update_book_title_choices()

    def persist_form_state() -> None:
        save_form_state(get_form_state(), book_titles)

    def persist_reading_history(history_entries: list[dict[str, str]]) -> None:
        save_reading_history(history_entries)

    previous_start_date = start_date_var.get().strip()

    def sync_end_date_default(*_args) -> None:
        nonlocal previous_start_date
        current_start_date = start_date_var.get().strip()
        current_end_date = end_date_var.get().strip()

        if not current_end_date or current_end_date == previous_start_date:
            end_date_var.set(current_start_date)

        previous_start_date = current_start_date

    def refresh_reading_history_display() -> None:
        latest_reading_var.set(build_latest_reading_text(reading_history))
        reading_stats_listbox.delete(0, tk.END)
        for stats_line in build_reading_stats_lines(reading_history):
            reading_stats_listbox.insert(tk.END, stats_line)

        reading_history_listbox.delete(0, tk.END)

        if not reading_history:
            reading_history_listbox.insert(tk.END, READING_HISTORY_EMPTY_TEXT)
            return

        for entry in reading_history:
            reading_history_listbox.insert(tk.END, format_reading_history_entry(entry))

    def add_reading_history_entry() -> None:
        try:
            book_title = parse_book_title(book_title_var.get())
            session_date = normalize_session_date(start_date_var.get().strip())
        except ValueError as exc:
            error_var.set(str(exc))
            calendar_status_var.set("")
            return

        if has_recent_same_book_title(reading_history, session_date, book_title):
            error_var.set(DUPLICATE_RECENT_BOOK_TEXT)
            calendar_status_var.set("")
            return

        if has_same_book_title(reading_history, book_title) and not messagebox.askyesno(
            DUPLICATE_BOOK_CONFIRM_TITLE,
            DUPLICATE_BOOK_CONFIRM_MESSAGE,
            parent=root,
        ):
            calendar_status_var.set("")
            error_var.set("")
            return

        remember_book_title(book_title)
        entry = {
            "session_date": session_date,
            "book_title": book_title,
        }

        try:
            updated_history = normalize_reading_history(reading_history + [entry])
            persist_reading_history(updated_history)
            persist_form_state()
        except (ReadingHistoryStoreError, SessionStateError) as exc:
            error_var.set(str(exc))
            calendar_status_var.set("")
            return

        reading_history.clear()
        reading_history.extend(updated_history)
        refresh_reading_history_display()
        calendar_status_var.set(READING_HISTORY_SUCCESS_TEXT)
        error_var.set("")

    def start_calendar_registration_worker(
        book_title: str,
        session_date: str,
        start_dt: datetime,
        end_dt: datetime,
        start_page: int,
        end_page: int,
    ) -> None:
        def worker() -> None:
            try:
                create_reading_event(
                    book_title=book_title,
                    session_date=session_date,
                    start_dt=start_dt,
                    end_dt=end_dt,
                    start_page=start_page,
                    end_page=end_page,
                )
            except GoogleCalendarIntegrationError as exc:
                calendar_result_queue.put(("error", str(exc)))
            except Exception:
                calendar_result_queue.put(("error", CALENDAR_UNEXPECTED_ERROR_TEXT))
            else:
                calendar_result_queue.put(("success", ""))

        threading.Thread(target=worker, daemon=True).start()
        schedule_calendar_result_poll(CALENDAR_RESULT_POLL_MS)

    def set_session_state(
        book_title: str,
        session_values: tuple[str, str, str, str, int, int],
    ) -> None:
        nonlocal current_session

        start_date, start_time, end_date, end_time, start_page, end_page = (
            session_values
        )
        current_session = session_values
        book_label_var.set(f"書名 {book_title}" if book_title else "書名 未入力")
        time_label_var.set(
            f"開始 {start_date} {start_time} / 終了 {end_date} {end_time}"
        )
        page_label_var.set(f"ページ {start_page} -> {end_page}")
        error_var.set("")
        schedule_progress_update(0)

    def read_form_values() -> tuple[str, tuple[str, str, str, str, int, int]]:
        book_title = book_title_var.get().strip()
        session_values = collect_session_inputs(
            start_date_var.get().strip(),
            start_time_var.get().strip(),
            end_date_var.get().strip(),
            end_time_var.get().strip(),
            start_page_var.get(),
            end_page_var.get(),
        )
        return book_title, session_values

    def apply_session(event=None) -> None:
        try:
            book_title, session_values = read_form_values()
        except ValueError as exc:
            error_var.set(str(exc))
            calendar_status_var.set("")
            return

        remember_book_title(book_title)
        set_session_state(book_title, session_values)
        calendar_status_var.set("")

        try:
            persist_form_state()
        except SessionStateError as exc:
            error_var.set(str(exc))
            return

    def process_calendar_result() -> None:
        nonlocal calendar_poll_id
        calendar_poll_id = None

        try:
            result_kind, payload = calendar_result_queue.get_nowait()
        except queue.Empty:
            if calendar_registration_in_progress:
                schedule_calendar_result_poll(CALENDAR_RESULT_POLL_MS)
            return

        set_calendar_registration_state(False)

        if result_kind == "error":
            error_var.set(payload)
            calendar_status_var.set("")
            return

        calendar_status_var.set(CALENDAR_SUCCESS_TEXT)

        try:
            persist_form_state()
        except SessionStateError as exc:
            error_var.set(str(exc))
            calendar_status_var.set("")

    def delete_selected_book() -> None:
        selected_title = book_title_var.get().strip()
        if not selected_title:
            error_var.set("削除する書名を選択してください。")
            calendar_status_var.set("")
            return

        if selected_title not in book_titles:
            error_var.set("その書名は一覧にありません。")
            calendar_status_var.set("")
            return

        book_titles.remove(selected_title)
        update_book_title_choices()
        book_title_var.set("")
        error_var.set("")
        calendar_status_var.set(BOOK_DELETED_TEXT)

        if book_label_var.get() == f"書名 {selected_title}":
            book_label_var.set(EMPTY_BOOK_TEXT)

        try:
            persist_form_state()
        except SessionStateError as exc:
            error_var.set(str(exc))
            calendar_status_var.set("")
            return

    def register_calendar_event() -> None:
        if calendar_registration_in_progress:
            return

        calendar_status_var.set(CALENDAR_PROGRESS_TEXT)
        error_var.set("")
        root.update_idletasks()

        try:
            book_title, session_values = read_form_values()
            calendar_book_title = parse_book_title(
                book_title,
                missing_message="Googleカレンダーに登録するには書名を入力してください。",
            )
            remember_book_title(book_title)
            set_session_state(book_title, session_values)
            start_date, start_time, end_date, end_time, start_page, end_page = (
                session_values
            )
            start_dt, end_dt = validate_session_inputs(
                start_date,
                start_time,
                end_date,
                end_time,
                start_page,
                end_page,
            )
            set_calendar_registration_state(True)
            start_calendar_registration_worker(
                book_title=calendar_book_title,
                session_date=start_date,
                start_dt=start_dt,
                end_dt=end_dt,
                start_page=start_page,
                end_page=end_page,
            )
        except (GoogleCalendarIntegrationError, ValueError) as exc:
            error_var.set(str(exc))
            calendar_status_var.set("")
            return

    def update_progress() -> None:
        nonlocal scheduled_update_id
        scheduled_update_id = None

        if current_session is None:
            progress_label.config(text=READY_TEXT)
            return

        start_date, start_time, end_date, end_time, start_page, end_page = (
            current_session
        )
        progress_label.config(
            text=calculate_pages(
                start_date,
                start_time,
                end_date,
                end_time,
                start_page,
                end_page,
            )
        )

        _, end_dt = validate_session_inputs(
            start_date,
            start_time,
            end_date,
            end_time,
            start_page,
            end_page,
        )

        if datetime.now() < end_dt:
            scheduled_update_id = root.after(60000, update_progress)

    def adjust_layout(event=None) -> None:
        width = max(root.winfo_width(), 1)
        height = max(root.winfo_height(), 1)
        width_scale = width / DEFAULT_WIDTH
        height_scale = height / DEFAULT_HEIGHT
        scale = min(width_scale, height_scale)

        def scaled_size(base_size: int, minimum: int) -> int:
            return max(int(round(base_size * scale)), minimum)

        info_font.configure(size=scaled_size(12, 9))
        progress_font.configure(size=scaled_size(14, 11))
        combobox_style.configure(
            "BookTimer.TCombobox",
            font=("Helvetica", scaled_size(12, 9)),
        )
        progress_label.config(wraplength=max(int(width * 0.85), 220))
        error_label.config(wraplength=max(int(width * 0.85), 220))
        calendar_status_label.config(wraplength=max(int(width * 0.85), 220))
        latest_reading_label.config(wraplength=max(int(width * 0.8), 220))

    def restore_saved_session() -> None:
        if not any(saved_form_state.values()):
            return

        try:
            book_title, session_values = read_form_values()
        except ValueError:
            if book_title_var.get().strip():
                book_label_var.set(f"書名 {book_title_var.get().strip()}")
            return

        set_session_state(book_title, session_values)
        calendar_status_var.set("")

    def handle_close() -> None:
        nonlocal calendar_poll_id
        try:
            persist_form_state()
        except SessionStateError as exc:
            error_var.set(str(exc))
            calendar_status_var.set("")
            return

        if calendar_poll_id is not None:
            root.after_cancel(calendar_poll_id)
            calendar_poll_id = None

        root.destroy()

    root.bind("<Configure>", adjust_layout)
    root.bind("<Return>", apply_session)
    start_date_var.trace_add("write", sync_end_date_default)
    root.after(0, adjust_layout)
    root.after(0, refresh_reading_history_display)
    root.after(0, restore_saved_session)
    root.protocol("WM_DELETE_WINDOW", handle_close)
    book_title_combobox.focus_set()
    root.mainloop()


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
