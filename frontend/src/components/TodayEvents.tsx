import { CalendarDays, RefreshCw } from "lucide-react";

import type { CalendarEvent } from "../types";
import { formatCalendarTime, formatJapaneseDate } from "../utils";

interface TodayEventsProps {
  date: string;
  events: CalendarEvent[];
  connected: boolean;
  loading: boolean;
  onRefresh: () => void;
}

export function TodayEvents({
  date,
  events,
  connected,
  loading,
  onRefresh,
}: TodayEventsProps) {
  return (
    <section className="panel events-panel" aria-labelledby="events-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">GOOGLE CALENDAR</span>
          <h2 id="events-title">今日の予定</h2>
        </div>
        <div className="heading-actions">
          <span className={`connection-status ${connected ? "connected" : ""}`}>
            {connected ? "接続済み" : "未接続"}
          </span>
          <button
            type="button"
            className="icon-button"
            onClick={onRefresh}
            disabled={loading}
            title="今日の予定を更新"
            aria-label="今日の予定を更新"
          >
            <RefreshCw size={18} className={loading ? "spinning" : ""} />
          </button>
        </div>
      </div>

      <div className="events-date">
        <CalendarDays size={18} />
        {formatJapaneseDate(date)}
      </div>

      <div className="table-wrap events-table-wrap">
        <table>
          <thead>
            <tr>
              <th>時間</th>
              <th>予定</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, index) => (
              <tr key={`${event.start ?? "all-day"}-${event.summary}-${index}`}>
                <td className="event-time">{formatCalendarTime(event)}</td>
                <td>{event.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && events.length === 0 ? (
          <div className="empty-state">
            {connected
              ? "今日の予定はありません。"
              : "更新するとGoogleアカウントの認証が始まります。"}
          </div>
        ) : null}
        {loading ? <div className="loading-row">予定を取得中...</div> : null}
      </div>
    </section>
  );
}
