import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime, timedelta

DEFAULT_WIDTH = 420
DEFAULT_HEIGHT = 220
TIME_FORMAT = "%H:%M"


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


def prompt_session_inputs() -> tuple[str, str, int, int]:
    """Prompt until the user enters a valid reading session."""
    while True:
        start_time = input("Enter reading start time (e.g. 08:00): ").strip()
        end_time = input("Enter reading end time (e.g. 10:00 or 24:00): ").strip()
        start_page_text = input("Enter start page: ")
        end_page_text = input("Enter end page: ")

        try:
            start_page = parse_page(start_page_text, "Start page")
            end_page = parse_page(end_page_text, "End page")
            validate_session_inputs(start_time, end_time, start_page, end_page)
        except ValueError as exc:
            print(exc)
            print("Please try again.\n")
            continue

        return start_time, end_time, start_page, end_page


def run_app(start_time: str, end_time: str, start_page: int, end_page: int) -> None:
    """Create and run the Tkinter application."""
    print(f"Start {start_time} / End {end_time} / Pages {start_page}->{end_page}")

    root = tk.Tk()
    root.title("Reading Timer")
    root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
    root.minsize(320, 180)
    root.resizable(True, True)

    info_font = tkfont.Font(family="Helvetica", size=12)
    progress_font = tkfont.Font(family="Helvetica", size=14)

    info_frame = tk.Frame(root)
    info_frame.pack(pady=(20, 10))

    time_label = tk.Label(
        info_frame,
        text=f"Start {start_time} / End {end_time}",
        font=info_font,
    )
    time_label.pack()

    page_label = tk.Label(
        info_frame,
        text=f"Pages {start_page} -> {end_page}",
        font=info_font,
    )
    page_label.pack()

    progress_label = tk.Label(
        root,
        text="Calculating progress...",
        font=progress_font,
        wraplength=360,
        justify="center",
    )
    progress_label.pack(pady=20)

    def update_progress() -> None:
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
            root.after(60000, update_progress)

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

    root.bind("<Configure>", adjust_layout)
    root.after(0, adjust_layout)
    update_progress()
    root.mainloop()


def main() -> None:
    start_time, end_time, start_page, end_page = prompt_session_inputs()
    run_app(start_time, end_time, start_page, end_page)


if __name__ == "__main__":
    main()
