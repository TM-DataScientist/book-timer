import type {
  BootstrapResponse,
  CalendarResponse,
  FormState,
  HistoryResponse,
  ReadingEntry,
  SessionResponse,
} from "./types";

interface ErrorDetail {
  code?: string;
  message?: string;
}

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail as string | ErrorDetail | undefined;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message ?? "処理に失敗しました。";
    throw new ApiError(response.status, message, detail && typeof detail !== "string" ? detail.code : undefined);
  }
  return body as T;
}

export const api = {
  bootstrap: () => request<BootstrapResponse>("/api/bootstrap"),

  saveState: (form: FormState, bookTitles: string[]) =>
    request<{ saved: boolean; book_titles: string[] }>("/api/state", {
      method: "PUT",
      body: JSON.stringify({ ...form, book_titles: bookTitles }),
    }),

  applySession: (form: FormState) =>
    request<SessionResponse>("/api/session", {
      method: "POST",
      body: JSON.stringify(form),
    }),

  addHistory: (form: FormState, allowReread = false) =>
    request<HistoryResponse>("/api/history", {
      method: "POST",
      body: JSON.stringify({
        session_date: form.start_date,
        book_title: form.book_title,
        allow_reread: allowReread,
      }),
    }),

  deleteHistory: (entry: ReadingEntry) => {
    const params = new URLSearchParams({
      session_date: entry.session_date,
      book_title: entry.book_title,
    });
    return request<HistoryResponse>(`/api/history?${params}`, {
      method: "DELETE",
    });
  },

  deleteBook: (bookTitle: string) => {
    const params = new URLSearchParams({ book_title: bookTitle });
    return request<{ book_titles: string[]; form_state: FormState }>(
      `/api/books?${params}`,
      { method: "DELETE" },
    );
  },

  getTodayEvents: () => request<CalendarResponse>("/api/calendar/today"),

  createCalendarEvent: (form: FormState) =>
    request<{ created: boolean; event_link: string; message: string }>(
      "/api/calendar/events",
      {
        method: "POST",
        body: JSON.stringify(form),
      },
    ),
};
