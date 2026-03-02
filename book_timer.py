import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime, timedelta

DEFAULT_WIDTH = 520
DEFAULT_HEIGHT = 360
TIME_FORMAT = "%H:%M"
EMPTY_TIME_TEXT = "Start --:-- / End --:--"
EMPTY_PAGE_TEXT = "Pages -- -> --"
READY_TEXT = "Enter session details and click Apply."


def parse_time_on_date(time_text: str, reference: datetime) -> datetime:
    """Parse HH:MM text on the reference date, allowing 24:00 as next-day midnight."""
    normalized = time_text.strip()

    if normalized == "24:00":
        midnight = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight + timedelta(days=1)

    parsed = datetime.strptime(normalized, TIME_FORMAT)
    return reference.replace(
        hour=parsed.hour,
        minute=parsed.minute,
        second=0,
        microsecond=0,
    )


def parse_page(page_text: str, label: str) -> int:
    """Convert page input to an integer with a readable validation message."""
    try:
        return int(page_text.strip())
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer.") from exc


def validate_session_inputs(
    start_time: str,
    end_time: str,
    start_page: int,
    end_page: int,
    reference: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Validate time/page inputs and return parsed datetimes."""
    if reference is None:
        reference = datetime.now()

    try:
        start_dt = parse_time_on_date(start_time, reference)
        end_dt = parse_time_on_date(end_time, reference)
    except ValueError as exc:
        raise ValueError("Use time format HH:MM. Enter 24:00 only for midnight.") from exc

    if end_dt <= start_dt:
        raise ValueError("End time must be after the start time.")

    if end_page < start_page:
        raise ValueError("End page must be greater than or equal to the start page.")

    return start_dt, end_dt


def calculate_pages(start_time: str, end_time: str, start_page: int, end_page: int) -> str:
    """Return a friendly status message describing the current reading progress."""
    now = datetime.now()

    try:
        start_dt, end_dt = validate_session_inputs(
            start_time,
            end_time,
            start_page,
            end_page,
            now,
        )
    except ValueError as exc:
        return str(exc)

    if now < start_dt:
        minutes = int((start_dt - now).total_seconds() // 60)
        return f"Reading begins in {minutes} minute(s)."

    if now >= end_dt:
        return f"Reading session finished. Review final page {end_page}."

    total_minutes = (end_dt - start_dt).total_seconds()
    elapsed_minutes = (now - start_dt).total_seconds()
    progress = min(max(elapsed_minutes / total_minutes, 0), 1)

    total_pages = max(end_page - start_page, 0) + 1
    current_page = start_page + int(total_pages * progress)
    current_page = min(max(current_page, start_page), end_page)

    return f"Estimated position: page {current_page}."


def run_app() -> None:
    """Create and run the Tkinter application."""
    root = tk.Tk()
    root.title("Reading Timer")
    root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
    root.minsize(420, 320)
    root.resizable(True, True)

    info_font = tkfont.Font(family="Helvetica", size=12)
    progress_font = tkfont.Font(family="Helvetica", size=14)
    start_time_var = tk.StringVar()
    end_time_var = tk.StringVar()
    start_page_var = tk.StringVar()
    end_page_var = tk.StringVar()
    error_var = tk.StringVar()
    time_label_var = tk.StringVar(value=EMPTY_TIME_TEXT)
    page_label_var = tk.StringVar(value=EMPTY_PAGE_TEXT)
    current_session: tuple[str, str, int, int] | None = None
    scheduled_update_id: str | None = None

    form_frame = tk.LabelFrame(root, text="Session Setup", padx=12, pady=12)
    form_frame.pack(fill="x", padx=16, pady=(16, 8))
    form_frame.columnconfigure(1, weight=1)
    form_frame.columnconfigure(3, weight=1)

    tk.Label(form_frame, text="Start time", font=info_font).grid(
        row=0, column=0, padx=(0, 8), pady=4, sticky="w"
    )
    start_time_entry = tk.Entry(form_frame, textvariable=start_time_var, font=info_font)
    start_time_entry.grid(row=0, column=1, padx=(0, 12), pady=4, sticky="ew")

    tk.Label(form_frame, text="End time", font=info_font).grid(
        row=0, column=2, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=end_time_var, font=info_font).grid(
        row=0, column=3, pady=4, sticky="ew"
    )

    tk.Label(form_frame, text="Start page", font=info_font).grid(
        row=1, column=0, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=start_page_var, font=info_font).grid(
        row=1, column=1, padx=(0, 12), pady=4, sticky="ew"
    )

    tk.Label(form_frame, text="End page", font=info_font).grid(
        row=1, column=2, padx=(0, 8), pady=4, sticky="w"
    )
    tk.Entry(form_frame, textvariable=end_page_var, font=info_font).grid(
        row=1, column=3, pady=4, sticky="ew"
    )

    info_frame = tk.Frame(root)
    info_frame.pack(pady=(8, 8))

    time_label = tk.Label(
        info_frame,
        textvariable=time_label_var,
        font=info_font,
    )
    time_label.pack()

    page_label = tk.Label(
        info_frame,
        textvariable=page_label_var,
        font=info_font,
    )
    page_label.pack()

    progress_label = tk.Label(
        root,
        text=READY_TEXT,
        font=progress_font,
        wraplength=440,
        justify="center",
    )
    progress_label.pack(padx=16, pady=(8, 12))

    error_label = tk.Label(
        root,
        textvariable=error_var,
        font=info_font,
        fg="red",
        wraplength=440,
        justify="center",
    )
    error_label.pack(padx=16, pady=(0, 12))

    def schedule_progress_update(delay_ms: int) -> None:
        nonlocal scheduled_update_id
        if scheduled_update_id is not None:
            root.after_cancel(scheduled_update_id)
            scheduled_update_id = None
        scheduled_update_id = root.after(delay_ms, update_progress)

    def apply_session(event=None) -> None:
        nonlocal current_session

        start_time = start_time_var.get().strip()
        end_time = end_time_var.get().strip()

        try:
            start_page = parse_page(start_page_var.get(), "Start page")
            end_page = parse_page(end_page_var.get(), "End page")
            validate_session_inputs(start_time, end_time, start_page, end_page)
        except ValueError as exc:
            error_var.set(str(exc))
            return

        current_session = (start_time, end_time, start_page, end_page)
        time_label_var.set(f"Start {start_time} / End {end_time}")
        page_label_var.set(f"Pages {start_page} -> {end_page}")
        error_var.set("")
        schedule_progress_update(0)

    apply_button = tk.Button(root, text="Apply", font=info_font, command=apply_session)
    apply_button.pack(pady=(0, 8))

    def update_progress() -> None:
        nonlocal scheduled_update_id
        scheduled_update_id = None

        if current_session is None:
            progress_label.config(text=READY_TEXT)
            return

        start_time, end_time, start_page, end_page = current_session
        progress_label.config(
            text=calculate_pages(start_time, end_time, start_page, end_page)
        )

        now = datetime.now()
        _, end_dt = validate_session_inputs(
            start_time,
            end_time,
            start_page,
            end_page,
            now,
        )

        if now < end_dt:
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
        progress_label.config(wraplength=max(int(width * 0.85), 200))
        error_label.config(wraplength=max(int(width * 0.85), 200))

    root.bind("<Configure>", adjust_layout)
    root.bind("<Return>", apply_session)
    root.after(0, adjust_layout)
    start_time_entry.focus_set()
    root.mainloop()


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
