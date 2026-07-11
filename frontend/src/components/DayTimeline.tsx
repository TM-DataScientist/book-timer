import { BookOpen } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import type { CalendarEvent, Session } from "../types";
import {
  formatCalendarTime,
  toLocalDateString,
  toLocalTimeString,
} from "../utils";

const HOUR_PX = 40;
const MIN_BLOCK_MINUTES = 30;
const DEFAULT_START_HOUR = 8;
const DEFAULT_END_HOUR = 21;

interface DayTimelineProps {
  date: string;
  events: CalendarEvent[];
  session: Session | null;
  emptyMessage: string;
}

interface TimedBlock {
  key: string;
  summary: string;
  timeText: string;
  startMin: number;
  endMin: number;
  column: number;
  columns: number;
}

interface SessionBand {
  title: string;
  timeText: string;
  startMin: number;
  endMin: number;
}

function clampToDay(
  startMs: number,
  endMs: number,
  dayStartMs: number,
): [number, number] | null {
  const dayEndMs = dayStartMs + 86_400_000;
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) {
    return null;
  }
  if (endMs <= dayStartMs || startMs >= dayEndMs) {
    return null;
  }
  return [
    Math.max(0, (startMs - dayStartMs) / 60_000),
    Math.min(1440, (endMs - dayStartMs) / 60_000),
  ];
}

function withDisplayFloor(startMin: number, endMin: number): [number, number] {
  if (endMin - startMin >= MIN_BLOCK_MINUTES) {
    return [startMin, endMin];
  }
  const floored = Math.min(1440, startMin + MIN_BLOCK_MINUTES);
  return [floored - MIN_BLOCK_MINUTES, floored];
}

function assignColumns(blocks: TimedBlock[]): TimedBlock[] {
  const sorted = [...blocks].sort(
    (left, right) => left.startMin - right.startMin || right.endMin - left.endMin,
  );
  let cluster: TimedBlock[] = [];
  let columnEnds: number[] = [];
  let clusterEnd = 0;

  const closeCluster = () => {
    for (const block of cluster) {
      block.columns = columnEnds.length;
    }
    cluster = [];
    columnEnds = [];
  };

  for (const block of sorted) {
    if (cluster.length > 0 && block.startMin >= clusterEnd) {
      closeCluster();
    }
    clusterEnd =
      cluster.length === 0 ? block.endMin : Math.max(clusterEnd, block.endMin);
    let column = columnEnds.findIndex((end) => end <= block.startMin);
    if (column === -1) {
      column = columnEnds.length;
      columnEnds.push(block.endMin);
    } else {
      columnEnds[column] = block.endMin;
    }
    block.column = column;
    cluster.push(block);
  }
  closeCluster();
  return sorted;
}

function buildBlocks(events: CalendarEvent[], dayStartMs: number): TimedBlock[] {
  const blocks: TimedBlock[] = [];
  events.forEach((event, index) => {
    if (event.is_all_day || !event.start) {
      return;
    }
    const startMs = new Date(event.start).getTime();
    const parsedEndMs = event.end ? new Date(event.end).getTime() : Number.NaN;
    const endMs =
      Number.isNaN(parsedEndMs) || parsedEndMs <= startMs
        ? startMs + MIN_BLOCK_MINUTES * 60_000
        : parsedEndMs;
    const range = clampToDay(startMs, endMs, dayStartMs);
    if (!range) {
      return;
    }
    const [startMin, endMin] = withDisplayFloor(range[0], range[1]);
    blocks.push({
      key: `${event.start}-${event.summary}-${index}`,
      summary: event.summary,
      timeText: formatCalendarTime(event),
      startMin,
      endMin,
      column: 0,
      columns: 1,
    });
  });
  return assignColumns(blocks);
}

function buildSessionBand(
  session: Session | null,
  dayStartMs: number,
): SessionBand | null {
  if (!session) {
    return null;
  }
  const startMs = new Date(session.start_at).getTime();
  const endMs = new Date(session.end_at).getTime();
  const range = clampToDay(startMs, endMs, dayStartMs);
  if (!range) {
    return null;
  }
  const [startMin, endMin] = withDisplayFloor(range[0], range[1]);
  return {
    title: session.book_title.trim() || "読書セッション",
    timeText: `${session.start_time}-${session.end_time}`,
    startMin,
    endMin,
  };
}

export function DayTimeline({
  date,
  events,
  session,
  emptyMessage,
}: DayTimelineProps) {
  const [now, setNow] = useState(() => new Date());
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const timerId = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timerId);
  }, []);

  const dayStartMs = useMemo(
    () => new Date(`${date}T00:00:00`).getTime(),
    [date],
  );
  const allDayEvents = useMemo(
    () => events.filter((event) => event.is_all_day || !event.start),
    [events],
  );
  const blocks = useMemo(
    () => buildBlocks(events, dayStartMs),
    [events, dayStartMs],
  );
  const band = useMemo(
    () => buildSessionBand(session, dayStartMs),
    [session, dayStartMs],
  );

  const nowMin =
    toLocalDateString(now) === date
      ? (now.getTime() - dayStartMs) / 60_000
      : null;

  let startHour = DEFAULT_START_HOUR;
  let endHour = DEFAULT_END_HOUR;
  const extents = band ? [...blocks, band] : blocks;
  for (const item of extents) {
    startHour = Math.min(startHour, Math.floor(item.startMin / 60));
    endHour = Math.max(endHour, Math.ceil(item.endMin / 60));
  }
  if (nowMin !== null) {
    startHour = Math.min(startHour, Math.floor(nowMin / 60));
    endHour = Math.max(endHour, Math.min(24, Math.floor(nowMin / 60) + 1));
  }
  startHour = Math.max(0, startHour);
  endHour = Math.min(24, Math.max(endHour, startHour + 1));

  const top = (minute: number) => ((minute - startHour * 60) / 60) * HOUR_PX;

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) {
      return;
    }
    const anchorMin = nowMin ?? blocks[0]?.startMin ?? band?.startMin;
    if (anchorMin === undefined || anchorMin === null) {
      return;
    }
    const anchorTop = ((anchorMin - startHour * 60) / 60) * HOUR_PX;
    element.scrollTop = Math.max(0, anchorTop - element.clientHeight / 3);
    // Recenter only when the displayed data changes, not on the 30s clock tick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, events, session]);

  if (allDayEvents.length === 0 && blocks.length === 0 && !band) {
    return <div className="empty-state">{emptyMessage}</div>;
  }

  const hours = Array.from(
    { length: endHour - startHour + 1 },
    (_, index) => startHour + index,
  );

  return (
    <div className="timeline">
      {allDayEvents.length > 0 ? (
        <div className="allday-row">
          <span className="allday-label">終日</span>
          <div className="allday-chips">
            {allDayEvents.map((event, index) => (
              <span
                className="allday-chip"
                key={`${event.summary}-${index}`}
                title={`${formatCalendarTime(event)} ${event.summary}`}
              >
                {event.summary}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {blocks.length === 0 && !band ? (
        <p className="empty-state compact">時間指定の予定はありません。</p>
      ) : (
        <div className="timeline-scroll" ref={scrollRef}>
          <div
            className="timeline-canvas"
            style={{ height: (endHour - startHour) * HOUR_PX + 1 }}
          >
            {hours.map((hour) => (
              <div
                className="timeline-hour"
                key={hour}
                style={{ top: (hour - startHour) * HOUR_PX }}
                aria-hidden="true"
              >
                {nowMin !== null && Math.abs(nowMin - hour * 60) < 20 ? null : (
                  <span>{hour}:00</span>
                )}
              </div>
            ))}
            <div className="timeline-plot" role="list" aria-label="今日のタイムライン">
              {band ? (
                <div
                  className="session-band"
                  role="listitem"
                  style={{
                    top: top(band.startMin),
                    height: Math.max(top(band.endMin) - top(band.startMin), 20),
                  }}
                  title={`読書予定 ${band.timeText} ${band.title}`}
                  aria-label={`読書予定 ${band.timeText} ${band.title}`}
                >
                  <span className="session-band-label">
                    <BookOpen size={13} aria-hidden="true" />
                    {band.title}
                    <em>{band.timeText}</em>
                  </span>
                </div>
              ) : null}
              {blocks.map((block) => (
                <div
                  key={block.key}
                  role="listitem"
                  className={`timeline-block${
                    block.endMin - block.startMin <= 38 ? " compact" : ""
                  }`}
                  style={{
                    top: top(block.startMin),
                    height: Math.max(
                      top(block.endMin) - top(block.startMin) - 2,
                      16,
                    ),
                    left: `${(block.column / block.columns) * 100}%`,
                    width: `calc(${100 / block.columns}% - 4px)`,
                  }}
                  title={`${block.timeText} ${block.summary}`}
                  aria-label={`${block.timeText} ${block.summary}`}
                >
                  <span className="block-title">{block.summary}</span>
                  <span className="block-time">{block.timeText}</span>
                </div>
              ))}
              {nowMin !== null &&
              nowMin >= startHour * 60 &&
              nowMin <= endHour * 60 ? (
                <div
                  className="timeline-now"
                  style={{ top: top(nowMin) }}
                  aria-hidden="true"
                >
                  <span className="now-time">{toLocalTimeString(now)}</span>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
