import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Info,
  LoaderCircle,
  MonitorDot,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError, api } from "./api";
import { ReadingHistory } from "./components/ReadingHistory";
import { SessionForm } from "./components/SessionForm";
import { SessionProgress } from "./components/SessionProgress";
import { TodayEvents } from "./components/TodayEvents";
import type {
  BusyAction,
  CalendarEvent,
  FormState,
  Notice,
  ReadingEntry,
  ReadingSummary,
  Session,
} from "./types";
import {
  formatJapaneseDate,
  shiftDate,
  shiftEndDateWithStart,
  toLocalDateString,
  toLocalTimeString,
} from "./utils";

const today = toLocalDateString(new Date());

const initialForm: FormState = {
  book_title: "",
  start_date: today,
  start_time: "08:00",
  end_date: today,
  end_time: "24:00",
  start_page: "",
  end_page: "",
};

const emptySummary: ReadingSummary = {
  total: 0,
  yearly: [],
  monthly: [],
};

function errorNotice(error: unknown): Notice {
  return {
    kind: "error",
    message: error instanceof Error ? error.message : "処理に失敗しました。",
  };
}

function addTitle(titles: string[], title: string): string[] {
  const normalized = title.trim();
  if (!normalized || titles.includes(normalized)) {
    return titles;
  }
  return [...titles, normalized].sort((left, right) =>
    left.localeCompare(right, "ja"),
  );
}

export default function App() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [bookTitles, setBookTitles] = useState<string[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [history, setHistory] = useState<ReadingEntry[]>([]);
  const [summary, setSummary] = useState<ReadingSummary>(emptySummary);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [eventsDate, setEventsDate] = useState(today);
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [busy, setBusy] = useState<BusyAction>("bootstrap");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await api.bootstrap();
        if (cancelled) return;
        setForm(data.form_state);
        setBookTitles(data.book_titles);
        setHistory(data.history);
        setSummary(data.summary);
        setCalendarConnected(data.calendar_connected);

        if (data.form_state.start_page && data.form_state.end_page) {
          try {
            const sessionData = await api.applySession(data.form_state);
            if (!cancelled) setSession(sessionData.session);
          } catch {
            // Keep an incomplete saved form editable without blocking startup.
          }
        }

        if (data.calendar_connected) {
          try {
            const calendar = await api.getTodayEvents();
            if (!cancelled) {
              setEvents(calendar.events);
              setEventsDate(calendar.date);
              setCalendarConnected(true);
            }
          } catch (error) {
            if (!cancelled) setNotice(errorNotice(error));
          }
        }
      } catch (error) {
        if (!cancelled) setNotice(errorNotice(error));
      } finally {
        if (!cancelled) {
          setBusy(null);
          setInitialized(true);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!initialized) return;
    const timerId = window.setTimeout(() => {
      void api.saveState(form, bookTitles).catch(() => undefined);
    }, 700);
    return () => window.clearTimeout(timerId);
  }, [bookTitles, form, initialized]);

  useEffect(() => {
    if (!notice) return;
    const timerId = window.setTimeout(() => setNotice(null), 6000);
    return () => window.clearTimeout(timerId);
  }, [notice]);

  const onFieldChange = (field: keyof FormState, value: string) => {
    setForm((current) => {
      if (field === "start_date") {
        return {
          ...current,
          start_date: value,
          end_date: shiftEndDateWithStart(
            current.start_date,
            value,
            current.end_date,
          ),
        };
      }
      return { ...current, [field]: value };
    });
  };

  const handleSetNow = () => {
    const now = new Date();
    const nextDate = toLocalDateString(now);
    setForm((current) => ({
      ...current,
      start_date: nextDate,
      start_time: toLocalTimeString(now),
      end_date: shiftEndDateWithStart(
        current.start_date,
        nextDate,
        current.end_date,
      ),
    }));
  };

  const handleNextDay = () => {
    setForm((current) => ({
      ...current,
      start_date: shiftDate(current.start_date, 1),
      end_date: shiftDate(current.end_date, 1),
    }));
  };

  const handleIncrementPages = (incrementText: string): boolean => {
    const increment = Number(incrementText);
    const startPage = Number(form.start_page);
    const endPage = Number(form.end_page);
    if (
      !form.start_page.trim() ||
      !form.end_page.trim() ||
      !Number.isInteger(increment) ||
      increment < 0 ||
      !Number.isInteger(startPage) ||
      !Number.isInteger(endPage)
    ) {
      setNotice({ kind: "error", message: "ページと加算値を整数で入力してください。" });
      return false;
    }
    setForm((current) => ({
      ...current,
      start_page: String(startPage + increment),
      end_page: String(endPage + increment),
    }));
    return true;
  };

  const handleApply = async () => {
    setBusy("apply");
    try {
      const response = await api.applySession(form);
      setSession(response.session);
      setBookTitles(response.book_titles);
      setNotice({ kind: "success", message: "セッションを反映しました。" });
    } catch (error) {
      setNotice(errorNotice(error));
    } finally {
      setBusy(null);
    }
  };

  const addHistory = async (allowReread = false) => {
    setBusy("history");
    try {
      const response = await api.addHistory(form, allowReread);
      setHistory(response.history);
      setSummary(response.summary);
      setBookTitles((current) => addTitle(current, form.book_title));
      setNotice({ kind: "success", message: "読了履歴に追加しました。" });
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.code === "confirm_reread" &&
        window.confirm(error.message)
      ) {
        setBusy(null);
        await addHistory(true);
        return;
      }
      setNotice(errorNotice(error));
    } finally {
      setBusy(null);
    }
  };

  const handleDeleteHistory = async (entry: ReadingEntry) => {
    if (!window.confirm(`${entry.book_title} の読了履歴を削除しますか？`)) return;
    setBusy("delete");
    try {
      const response = await api.deleteHistory(entry);
      setHistory(response.history);
      setSummary(response.summary);
      setNotice({ kind: "success", message: "読了履歴を削除しました。" });
    } catch (error) {
      setNotice(errorNotice(error));
    } finally {
      setBusy(null);
    }
  };

  const handleDeleteBook = async () => {
    const title = form.book_title.trim();
    if (!title || !window.confirm(`${title} を書名候補から削除しますか？`)) return;
    setBusy("delete");
    try {
      const response = await api.deleteBook(title);
      setBookTitles(response.book_titles);
      setForm((current) => ({ ...current, book_title: "" }));
      setNotice({ kind: "success", message: "書名候補から削除しました。" });
    } catch (error) {
      setNotice(errorNotice(error));
    } finally {
      setBusy(null);
    }
  };

  const refreshCalendar = async (showSuccess = true) => {
    setBusy("events");
    try {
      const response = await api.getTodayEvents();
      setEvents(response.events);
      setEventsDate(response.date);
      setCalendarConnected(true);
      if (showSuccess) {
        setNotice({
          kind: "success",
          message: `今日の予定を更新しました（${response.events.length}件）。`,
        });
      }
    } catch (error) {
      setNotice(errorNotice(error));
    } finally {
      setBusy(null);
    }
  };

  const handleRegisterCalendar = async () => {
    setBusy("calendar");
    try {
      const response = await api.createCalendarEvent(form);
      setBookTitles((current) => addTitle(current, form.book_title));
      setCalendarConnected(true);
      setNotice({ kind: "success", message: response.message });
      await refreshCalendar(false);
    } catch (error) {
      setNotice(errorNotice(error));
    } finally {
      setBusy(null);
    }
  };

  const noticeIcon =
    notice?.kind === "success" ? (
      <CheckCircle2 size={18} />
    ) : notice?.kind === "error" ? (
      <AlertCircle size={18} />
    ) : (
      <Info size={18} />
    );

  if (busy === "bootstrap") {
    return (
      <main className="app-loading">
        <LoaderCircle size={28} className="spinning" />
        <span>読書データを読み込んでいます...</span>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <BookOpen size={27} aria-hidden="true" />
          <div>
            <h1>Book Timer</h1>
            <span>Reading workspace</span>
          </div>
        </div>
        <div className="topbar-meta">
          <span>{formatJapaneseDate(new Date())}</span>
          <span className="local-badge">
            <MonitorDot size={16} />
            ローカル
          </span>
        </div>
      </header>

      {notice ? (
        <div className={`notice ${notice.kind}`} role="status">
          {noticeIcon}
          <span>{notice.message}</span>
          <button
            type="button"
            className="icon-button"
            onClick={() => setNotice(null)}
            aria-label="通知を閉じる"
            title="通知を閉じる"
          >
            <X size={17} />
          </button>
        </div>
      ) : null}

      <main className="app-main">
        <div className="workspace-grid">
          <SessionForm
            form={form}
            bookTitles={bookTitles}
            disabled={busy !== null}
            onFieldChange={onFieldChange}
            onApply={() => void handleApply()}
            onAddHistory={() => void addHistory()}
            onRegisterCalendar={() => void handleRegisterCalendar()}
            onSetNow={handleSetNow}
            onNextDay={handleNextDay}
            onIncrementPages={handleIncrementPages}
            onDeleteBook={() => void handleDeleteBook()}
          />

          <div className="dashboard-column">
            <SessionProgress session={session} />
            <TodayEvents
              date={eventsDate}
              events={events}
              session={session}
              connected={calendarConnected}
              loading={busy === "events"}
              onRefresh={() => void refreshCalendar()}
            />
          </div>
        </div>

        <ReadingHistory
          history={history}
          summary={summary}
          disabled={busy !== null}
          onDelete={(entry) => void handleDeleteHistory(entry)}
        />
      </main>
    </div>
  );
}
