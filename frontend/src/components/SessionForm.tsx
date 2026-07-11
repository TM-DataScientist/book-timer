import { useState } from "react";
import {
  BookCheck,
  CalendarPlus,
  Check,
  Clock3,
  Plus,
  Trash2,
} from "lucide-react";

import type { FormState } from "../types";

interface SessionFormProps {
  form: FormState;
  bookTitles: string[];
  disabled: boolean;
  onFieldChange: (field: keyof FormState, value: string) => void;
  onApply: () => void;
  onAddHistory: () => void;
  onRegisterCalendar: () => void;
  onSetNow: () => void;
  onNextDay: () => void;
  onIncrementPages: (increment: string) => boolean;
  onDeleteBook: () => void;
}

export function SessionForm({
  form,
  bookTitles,
  disabled,
  onFieldChange,
  onApply,
  onAddHistory,
  onRegisterCalendar,
  onSetNow,
  onNextDay,
  onIncrementPages,
  onDeleteBook,
}: SessionFormProps) {
  const [increment, setIncrement] = useState("");

  const update = (field: keyof FormState) =>
    (event: React.ChangeEvent<HTMLInputElement>) =>
      onFieldChange(field, event.target.value);

  const applyIncrement = () => {
    if (onIncrementPages(increment)) {
      setIncrement("");
    }
  };

  return (
    <section className="panel session-form-panel" aria-labelledby="session-form-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">READING SESSION</span>
          <h2 id="session-form-title">セッション設定</h2>
        </div>
      </div>

      <form
        className="session-form"
        onSubmit={(event) => {
          event.preventDefault();
          onApply();
        }}
      >
        <div className="field-group book-field-group">
          <label htmlFor="book-title">書名</label>
          <div className="input-with-action">
            <input
              id="book-title"
              list="book-title-options"
              value={form.book_title}
              onChange={update("book_title")}
              placeholder="読んでいる本"
              autoComplete="off"
            />
            <datalist id="book-title-options">
              {bookTitles.map((title) => (
                <option key={title} value={title} />
              ))}
            </datalist>
            <button
              type="button"
              className="icon-button danger-quiet"
              onClick={onDeleteBook}
              disabled={disabled || !form.book_title}
              title="選択中の書名を削除"
              aria-label="選択中の書名を削除"
            >
              <Trash2 size={18} />
            </button>
          </div>
        </div>

        <div className="date-time-grid">
          <div className="field-group">
            <label htmlFor="start-date">開始日</label>
            <input
              id="start-date"
              type="date"
              value={form.start_date}
              onChange={update("start_date")}
            />
          </div>
          <div className="field-group">
            <label htmlFor="start-time">開始時刻</label>
            <input
              id="start-time"
              type="text"
              inputMode="numeric"
              value={form.start_time}
              onChange={update("start_time")}
              placeholder="08:00"
            />
          </div>
          <div className="field-group">
            <label htmlFor="end-date">終了日</label>
            <input
              id="end-date"
              type="date"
              value={form.end_date}
              onChange={update("end_date")}
            />
          </div>
          <div className="field-group">
            <label htmlFor="end-time">終了時刻</label>
            <input
              id="end-time"
              type="text"
              inputMode="numeric"
              value={form.end_time}
              onChange={update("end_time")}
              placeholder="24:00"
            />
          </div>
        </div>

        <div className="page-grid">
          <div className="field-group">
            <label htmlFor="start-page">開始ページ</label>
            <input
              id="start-page"
              type="number"
              min="0"
              value={form.start_page}
              onChange={update("start_page")}
              placeholder="0"
            />
          </div>
          <div className="field-group">
            <label htmlFor="end-page">終了ページ</label>
            <input
              id="end-page"
              type="number"
              min="0"
              value={form.end_page}
              onChange={update("end_page")}
              placeholder="0"
            />
          </div>
        </div>

        <div className="utility-toolbar" aria-label="入力補助">
          <button type="button" onClick={onSetNow} disabled={disabled}>
            <Clock3 size={16} />
            開始を現在に
          </button>
          <button type="button" onClick={onNextDay} disabled={disabled}>
            <CalendarPlus size={16} />
            日付 +1日
          </button>
          <div className="increment-control">
            <label htmlFor="page-increment">ページ加算</label>
            <input
              id="page-increment"
              type="number"
              min="0"
              value={increment}
              onChange={(event) => setIncrement(event.target.value)}
              placeholder="0"
            />
            <button
              type="button"
              className="icon-button"
              onClick={applyIncrement}
              disabled={disabled || !increment}
              title="開始・終了ページへ加算"
              aria-label="開始・終了ページへ加算"
            >
              <Plus size={18} />
            </button>
          </div>
        </div>

        <div className="primary-actions">
          <button className="primary-button" type="submit" disabled={disabled}>
            <Check size={18} />
            反映
          </button>
          <button type="button" onClick={onAddHistory} disabled={disabled}>
            <BookCheck size={18} />
            読了に追加
          </button>
          <button type="button" onClick={onRegisterCalendar} disabled={disabled}>
            <CalendarPlus size={18} />
            予定を登録
          </button>
        </div>
      </form>
    </section>
  );
}
