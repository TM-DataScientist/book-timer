import type { CalendarEvent } from "./types";

export function toLocalDateString(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function toLocalTimeString(value: Date): string {
  const hours = String(value.getHours()).padStart(2, "0");
  const minutes = String(value.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

export function formatJapaneseDate(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(date);
}

export function shiftDate(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  date.setDate(date.getDate() + days);
  return toLocalDateString(date);
}

export function shiftEndDateWithStart(
  previousStart: string,
  nextStart: string,
  currentEnd: string,
): string {
  const previous = new Date(`${previousStart}T00:00:00`);
  const next = new Date(`${nextStart}T00:00:00`);
  const end = new Date(`${currentEnd}T00:00:00`);
  if ([previous, next, end].some((date) => Number.isNaN(date.getTime()))) {
    return nextStart;
  }
  const dayDifference = Math.round(
    (next.getTime() - previous.getTime()) / 86_400_000,
  );
  end.setDate(end.getDate() + dayDifference);
  return toLocalDateString(end);
}

export function formatCalendarTime(event: CalendarEvent): string {
  if (event.is_all_day) {
    return "終日";
  }
  if (!event.start) {
    return "時刻未設定";
  }

  const start = new Date(event.start);
  const end = event.end ? new Date(event.end) : null;
  const time = (date: Date) =>
    new Intl.DateTimeFormat("ja-JP", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);

  if (!end) {
    return time(start);
  }
  if (start.toDateString() === end.toDateString()) {
    return `${time(start)}-${time(end)}`;
  }
  const dateTime = (date: Date) =>
    `${date.getMonth() + 1}/${date.getDate()} ${time(date)}`;
  return `${dateTime(start)}-${dateTime(end)}`;
}

export function formatRemaining(seconds: number): string {
  const safeSeconds = Math.max(Math.floor(seconds), 0);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}時間 ${minutes}分`;
  }
  return `${minutes}分`;
}
