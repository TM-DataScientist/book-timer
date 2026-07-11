import { BarChart3, BookMarked, Trash2 } from "lucide-react";

import type { ReadingEntry, ReadingSummary } from "../types";

interface ReadingHistoryProps {
  history: ReadingEntry[];
  summary: ReadingSummary;
  disabled: boolean;
  onDelete: (entry: ReadingEntry) => void;
}

function CountBars({
  title,
  values,
}: {
  title: string;
  values: ReadingSummary["monthly"];
}) {
  const maxCount = Math.max(...values.map((value) => value.count), 1);

  return (
    <div className="count-bars">
      <h3>{title}</h3>
      {values.length === 0 ? (
        <p className="empty-state compact">集計データはまだありません。</p>
      ) : (
        values.map((value) => (
          <div className="count-row" key={value.period}>
            <span>{value.period}</span>
            <div className="count-track" aria-hidden="true">
              <span style={{ width: `${(value.count / maxCount) * 100}%` }} />
            </div>
            <strong>{value.count}</strong>
          </div>
        ))
      )}
    </div>
  );
}

export function ReadingHistory({
  history,
  summary,
  disabled,
  onDelete,
}: ReadingHistoryProps) {
  const latest = history[0];
  const currentYear = summary.yearly[0]?.count ?? 0;
  const currentMonth = summary.monthly[0]?.count ?? 0;

  return (
    <section className="panel history-panel" aria-labelledby="history-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">READING LOG</span>
          <h2 id="history-title">読了履歴</h2>
        </div>
        <BookMarked size={22} aria-hidden="true" />
      </div>

      <div className="history-metrics">
        <div>
          <span>累計</span>
          <strong>{summary.total}</strong>
          <small>冊</small>
        </div>
        <div>
          <span>最新年</span>
          <strong>{currentYear}</strong>
          <small>冊</small>
        </div>
        <div>
          <span>最新月</span>
          <strong>{currentMonth}</strong>
          <small>冊</small>
        </div>
        <div className="latest-reading">
          <span>最新の読了</span>
          <strong>{latest?.book_title ?? "記録なし"}</strong>
          <small>{latest?.session_date ?? "--"}</small>
        </div>
      </div>

      <div className="history-content-grid">
        <div className="stats-column">
          <div className="subsection-title">
            <BarChart3 size={18} />
            <h3>読了冊数</h3>
          </div>
          <CountBars title="年別" values={summary.yearly.slice(0, 4)} />
          <CountBars title="月別" values={summary.monthly.slice(0, 6)} />
        </div>

        <div className="history-list-column">
          <div className="table-wrap history-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>読了日</th>
                  <th>書名</th>
                  <th aria-label="操作" />
                </tr>
              </thead>
              <tbody>
                {history.map((entry) => (
                  <tr key={`${entry.session_date}-${entry.book_title}`}>
                    <td>{entry.session_date}</td>
                    <td>{entry.book_title}</td>
                    <td className="row-action">
                      <button
                        type="button"
                        className="icon-button danger-quiet"
                        onClick={() => onDelete(entry)}
                        disabled={disabled}
                        title="この読了履歴を削除"
                        aria-label={`${entry.book_title}の読了履歴を削除`}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {history.length === 0 ? (
              <div className="empty-state">まだ読了履歴がありません。</div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
