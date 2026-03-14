/**
 * Main page — Amsterdam Padel Availability Tracker
 *
 * Shows a date picker and a card per venue with available slots.
 * Auto-refreshes every 2 minutes.
 */

import { useEffect, useState, useCallback } from "react";
import Head from "next/head";
import CourtCard, { VenueAvailability } from "../components/CourtCard";
import { API_URL } from "../lib/constants";

const REFRESH_MS = 2 * 60 * 1000; // 2 minutes
const TODAY_ISO = new Date().toISOString().slice(0, 10);

export default function Home() {
  const [selectedDate, setSelectedDate] = useState<string>(TODAY_ISO);
  const [venues, setVenues] = useState<VenueAvailability[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchAvailability = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/availability?date=${selectedDate}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data: VenueAvailability[] = await res.json();
      setVenues(data);
      setLastUpdated(new Date().toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load availability");
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  // Fetch on date change and every REFRESH_MS.
  useEffect(() => {
    fetchAvailability();
    const interval = setInterval(fetchAvailability, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchAvailability]);

  const totalSlots = venues.reduce((sum, v) => sum + v.slots.length, 0);

  return (
    <>
      <Head>
        <title>Padel Amsterdam — Beschikbaarheid</title>
        <meta name="description" content="Check real-time padel court availability in Amsterdam" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="main">
        <header className="header">
          <div className="header-inner">
            <div>
              <h1 className="title">Padel Amsterdam</h1>
              <p className="subtitle">Real-time beschikbaarheid van padelcourts</p>
            </div>
            <div className="header-meta">
              {lastUpdated && <span className="updated">Bijgewerkt om {lastUpdated}</span>}
              <button className="refresh-btn" onClick={fetchAvailability} disabled={loading}>
                {loading ? "Laden…" : "Vernieuwen"}
              </button>
            </div>
          </div>
        </header>

        <div className="container">
          {/* Date picker */}
          <div className="date-row">
            <label htmlFor="date-picker" className="date-label">Datum</label>
            <input
              id="date-picker"
              type="date"
              value={selectedDate}
              min={TODAY_ISO}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="date-input"
            />
            {!loading && !error && (
              <span className="total-slots">
                {totalSlots} vrije slot{totalSlots !== 1 ? "s" : ""} gevonden
              </span>
            )}
          </div>

          {/* Error state */}
          {error && (
            <div className="error-box">
              <strong>Fout:</strong> {error}
            </div>
          )}

          {/* Venue cards */}
          {loading && venues.length === 0 ? (
            <div className="loading">Beschikbaarheid ophalen…</div>
          ) : (
            venues.map((venue) => (
              <CourtCard key={venue.venue_id} venue={venue} />
            ))
          )}
        </div>
      </main>

      <style jsx global>{`
        *, *::before, *::after { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          background: #f1f5f9;
          color: #1e293b;
        }
        a { color: inherit; }
      `}</style>

      <style jsx>{`
        .main { min-height: 100vh; }
        .header {
          background: #1e40af;
          color: white;
          padding: 24px 0;
          margin-bottom: 28px;
        }
        .header-inner {
          max-width: 900px;
          margin: 0 auto;
          padding: 0 16px;
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          gap: 16px;
        }
        .title { font-size: 28px; font-weight: 800; margin: 0; }
        .subtitle { font-size: 14px; opacity: 0.8; margin: 4px 0 0; }
        .header-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
        .updated { font-size: 12px; opacity: 0.7; }
        .refresh-btn {
          background: rgba(255,255,255,0.15);
          color: white;
          border: 1px solid rgba(255,255,255,0.3);
          border-radius: 6px;
          padding: 6px 14px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }
        .refresh-btn:hover { background: rgba(255,255,255,0.25); }
        .refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .container { max-width: 900px; margin: 0 auto; padding: 0 16px 48px; }
        .date-row {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        .date-label { font-weight: 600; font-size: 14px; }
        .date-input {
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          background: white;
        }
        .total-slots { font-size: 13px; color: #6b7280; margin-left: auto; }
        .error-box {
          background: #fee2e2;
          border: 1px solid #fca5a5;
          color: #991b1b;
          padding: 12px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
          font-size: 14px;
        }
        .loading { text-align: center; color: #6b7280; padding: 60px 0; font-size: 16px; }
      `}</style>
    </>
  );
}
