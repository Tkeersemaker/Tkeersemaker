/**
 * TimeGrid — renders an hour-by-hour availability grid for a venue.
 * Green = available slot, grey = no data for that hour.
 */

import { useMemo } from "react";
import { Slot } from "./CourtCard";

interface Props {
  slots: Slot[];
  bookingUrl: string;
}

const HOURS = Array.from({ length: 16 }, (_, i) => i + 7); // 07:00 – 22:00

export default function TimeGrid({ slots, bookingUrl }: Props) {
  const byHour = useMemo(() => {
    const lookup: Record<string, Slot> = {};
    for (const slot of slots) {
      const hour = slot.start.slice(11, 13); // "HH" from ISO datetime
      if (!lookup[hour]) lookup[hour] = slot;
    }
    return lookup;
  }, [slots]);

  return (
    <div className="time-grid">
      {HOURS.map((h) => {
        const label = `${String(h).padStart(2, "0")}:00`;
        const hourKey = String(h).padStart(2, "0");
        const slot = byHour[hourKey];

        return (
          <div key={h} className={`time-cell ${slot ? "available" : "unavailable"}`}>
            <span className="time-label">{label}</span>
            {slot && (
              <a
                href={bookingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="book-btn"
                title={`Book ${label} — €${(slot.price / 100).toFixed(2)}`}
              >
                Book
              </a>
            )}
          </div>
        );
      })}

      <style jsx>{`
        .time-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 10px;
        }
        .time-cell {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 64px;
          height: 56px;
          border-radius: 8px;
          font-size: 12px;
          font-weight: 600;
        }
        .available {
          background: #d1fae5;
          color: #065f46;
          border: 1px solid #6ee7b7;
        }
        .unavailable {
          background: #f3f4f6;
          color: #9ca3af;
          border: 1px solid #e5e7eb;
        }
        .time-label {
          font-size: 11px;
        }
        .book-btn {
          margin-top: 4px;
          font-size: 10px;
          background: #059669;
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          text-decoration: none;
        }
        .book-btn:hover {
          background: #047857;
        }
      `}</style>
    </div>
  );
}
