export interface FormState {
  book_title: string;
  start_date: string;
  start_time: string;
  end_date: string;
  end_time: string;
  start_page: string;
  end_page: string;
}

export interface Session extends Omit<FormState, "start_page" | "end_page"> {
  start_page: number;
  end_page: number;
  start_at: string;
  end_at: string;
}

export interface ReadingEntry {
  session_date: string;
  book_title: string;
}

export interface PeriodCount {
  period: string;
  count: number;
}

export interface ReadingSummary {
  total: number;
  yearly: PeriodCount[];
  monthly: PeriodCount[];
}

export interface CalendarEvent {
  summary: string;
  start: string | null;
  end: string | null;
  is_all_day: boolean;
}

export interface BootstrapResponse {
  form_state: FormState;
  book_titles: string[];
  history: ReadingEntry[];
  summary: ReadingSummary;
  calendar_connected: boolean;
}

export interface SessionResponse {
  session: Session;
  book_titles: string[];
}

export interface HistoryResponse {
  history: ReadingEntry[];
  summary: ReadingSummary;
}

export interface CalendarResponse {
  date: string;
  events: CalendarEvent[];
  calendar_connected: boolean;
}

export type BusyAction =
  | "bootstrap"
  | "apply"
  | "history"
  | "calendar"
  | "events"
  | "delete"
  | null;

export interface Notice {
  kind: "success" | "error" | "info";
  message: string;
}
