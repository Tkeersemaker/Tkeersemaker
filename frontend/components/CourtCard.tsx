/**
 * CourtCard — shows availability for a single venue along with an
 * "Alert me" form to subscribe to Telegram notifications.
 */

import { useEffect, useState } from "react";
import TimeGrid from "./TimeGrid";
import { API_URL } from "../lib/constants";

export interface Slot {
  resource_id: string;
  start: string;       // ISO datetime
  duration: number;    // minutes
  price: number;       // cents
  currency: string;
  name?: string;
}

export interface VenueAvailability {
  venue_id: string;
  venue_name: string;
  booking_url: string;
  date: string;
  slots: Slot[];
  error?: string;
}

interface Props {
  venue: VenueAvailability;
}

export default function CourtCard({ venue }: Props) {
  const [alertOpen, setAlertOpen] = useState(false);
  const [contact, setContact] = useState("");
  const [timeFrom, setTimeFrom] = useState("09:00");
  const [timeTo, setTimeTo] = useState("11:00");
  const [alertStatus, setAlertStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  const availableCount = venue.slots.length;
  const timeRangeValid = timeFrom < timeTo;

  // Auto-close the form 2s after a successful alert submission.
  useEffect(() => {
    if (alertStatus !== "done") return;
    const timer = setTimeout(() => {
      setAlertOpen(false);
      setAlertStatus("idle");
    }, 2000);
    return () => clearTimeout(timer);
  }, [alertStatus]);

  const handleToggleAlert = () => {
    setAlertOpen((v) => !v);
    setAlertStatus("idle");
  };

  const submitAlert = async () => {
    if (!timeRangeValid) return;
    setAlertStatus("loading");
    try {
      const res = await fetch(`${API_URL}/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contact,
          channel: "telegram",
          venue_id: venue.venue_id,
          date: venue.date,
          time_from: timeFrom,
          time_to: timeTo,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setAlertStatus("done");
    } catch {
      setAlertStatus("error");
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="venue-name">{venue.venue_name}</h2>
          <p className="slot-count">
            {venue.error
              ? "Could not fetch availability"
              : `${availableCount} slot${availableCount !== 1 ? "s" : ""} available`}
          </p>
        </div>
        <div className="card-actions">
          <a href={venue.booking_url} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
            Open Playtomic
          </a>
          <button className="btn btn-secondary" onClick={handleToggleAlert}>
            {alertOpen ? "Cancel" : "Notify me"}
          </button>
        </div>
      </div>

      {alertOpen && (
        <div className="alert-form">
          <p className="alert-hint">
            Enter your Telegram chat ID and a time window. We'll message you the moment a court opens up.
          </p>
          <div className="alert-row">
            <input
              type="text"
              placeholder="Telegram chat ID (numbers only)"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              className="input"
            />
            <input type="time" value={timeFrom} onChange={(e) => setTimeFrom(e.target.value)} className="input-time" />
            <span>–</span>
            <input type="time" value={timeTo} onChange={(e) => setTimeTo(e.target.value)} className="input-time" />
            <button
              className="btn btn-primary"
              onClick={submitAlert}
              disabled={!contact || !timeRangeValid || alertStatus === "loading"}
            >
              {alertStatus === "loading" ? "Saving…" : "Set alert"}
            </button>
          </div>
          {!timeRangeValid && (
            <p className="alert-error">End time must be after start time.</p>
          )}
          {alertStatus === "done" && (
            <p className="alert-success">Alert set! You'll receive a Telegram message when a slot opens.</p>
          )}
          {alertStatus === "error" && (
            <p className="alert-error">Something went wrong. Please try again.</p>
          )}
        </div>
      )}

      <TimeGrid slots={venue.slots} bookingUrl={venue.booking_url} />

      <style jsx>{`
        .card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
          margin-bottom: 16px;
        }
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
        }
        .venue-name {
          font-size: 18px;
          font-weight: 700;
          margin: 0;
          color: #111827;
        }
        .slot-count {
          font-size: 13px;
          color: #6b7280;
          margin: 4px 0 0;
        }
        .card-actions {
          display: flex;
          gap: 8px;
          flex-shrink: 0;
        }
        .btn {
          padding: 7px 14px;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          border: none;
          text-decoration: none;
          display: inline-block;
        }
        .btn-primary {
          background: #2563eb;
          color: white;
        }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-primary:disabled { background: #93c5fd; cursor: not-allowed; }
        .btn-secondary {
          background: #f3f4f6;
          color: #374151;
        }
        .btn-secondary:hover { background: #e5e7eb; }
        .alert-form {
          margin-top: 14px;
          padding: 14px;
          background: #f9fafb;
          border-radius: 8px;
        }
        .alert-hint {
          font-size: 13px;
          color: #6b7280;
          margin: 0 0 10px;
        }
        .alert-row {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .input {
          flex: 1;
          min-width: 160px;
          padding: 7px 10px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 13px;
        }
        .input-time {
          padding: 7px 10px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 13px;
        }
        .alert-success { color: #059669; font-size: 13px; margin-top: 8px; }
        .alert-error { color: #dc2626; font-size: 13px; margin-top: 8px; }
      `}</style>
    </div>
  );
}
