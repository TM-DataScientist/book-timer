import { BookOpen, CheckCircle2, Clock3 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { Session } from "../types";
import { formatRemaining, formatJapaneseDate } from "../utils";

interface SessionProgressProps {
  session: Session | null;
}

interface ProgressSnapshot {
  state: "ready" | "upcoming" | "active" | "complete";
  currentPage: number | null;
  percent: number;
  status: string;
  remaining: string;
}

function calculateProgress(session: Session | null, now: Date): ProgressSnapshot {
  if (!session) {
    return {
      state: "ready",
      currentPage: null,
      percent: 0,
      status: "セッション未設定",
      remaining: "--",
    };
  }

  const start = new Date(session.start_at).getTime();
  const end = new Date(session.end_at).getTime();
  const current = now.getTime();
  const totalSeconds = Math.max((end - start) / 1000, 1);

  if (current < start) {
    return {
      state: "upcoming",
      currentPage: session.start_page,
      percent: 0,
      status: "開始前",
      remaining: formatRemaining((start - current) / 1000),
    };
  }
  if (current >= end) {
    return {
      state: "complete",
      currentPage: session.end_page,
      percent: 100,
      status: "終了",
      remaining: "0分",
    };
  }

  const progress = Math.min(Math.max((current - start) / (end - start), 0), 1);
  const pageCount = Math.max(session.end_page - session.start_page, 0) + 1;
  const currentPage = Math.min(
    session.start_page + Math.floor(pageCount * progress),
    session.end_page,
  );
  return {
    state: "active",
    currentPage,
    percent: progress * 100,
    status: "進行中",
    remaining: formatRemaining(totalSeconds * (1 - progress)),
  };
}

export function SessionProgress({ session }: SessionProgressProps) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timerId = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timerId);
  }, []);

  const snapshot = useMemo(() => calculateProgress(session, now), [session, now]);

  return (
    <section className="panel progress-panel" aria-labelledby="progress-title">
      <div className="section-heading progress-heading">
        <div>
          <span className="section-kicker">LIVE PROGRESS</span>
          <h2 id="progress-title">読書進捗</h2>
        </div>
        <span className={`status-pill ${snapshot.state}`}>
          {snapshot.state === "complete" ? (
            <CheckCircle2 size={15} />
          ) : (
            <Clock3 size={15} />
          )}
          {snapshot.status}
        </span>
      </div>

      <div className="progress-body">
        <div className="page-readout">
          <BookOpen size={24} aria-hidden="true" />
          <div>
            <span className="readout-label">推定ページ</span>
            <strong>{snapshot.currentPage ?? "--"}</strong>
            <span>ページ</span>
          </div>
        </div>
        <div className="progress-metrics">
          <div>
            <span>進捗</span>
            <strong>{Math.round(snapshot.percent)}%</strong>
          </div>
          <div>
            <span>{snapshot.state === "upcoming" ? "開始まで" : "残り"}</span>
            <strong>{snapshot.remaining}</strong>
          </div>
        </div>
      </div>

      <div
        className="progress-track"
        role="progressbar"
        aria-label="読書進捗"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(snapshot.percent)}
      >
        <span style={{ width: `${snapshot.percent}%` }} />
      </div>

      {session ? (
        <div className="session-caption">
          <strong>{session.book_title || "書名未入力"}</strong>
          <span>
            {formatJapaneseDate(session.start_date)} {session.start_time} - {session.end_time}
          </span>
          <span>
            P.{session.start_page} - P.{session.end_page}
          </span>
        </div>
      ) : (
        <p className="empty-state compact">左の入力内容を反映すると進捗が表示されます。</p>
      )}
    </section>
  );
}
