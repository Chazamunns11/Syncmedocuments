/** Format integer cents as a currency string. */
export function formatMoney(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100);
}

/** Parse a user-typed amount (dollars) into integer cents. */
export function parseMoneyToCents(input: string): number {
  const n = parseFloat(String(input).replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) ? Math.round(n * 100) : 0;
}

function safeTz(tz?: string | null): string {
  return tz || "UTC";
}

/** Today's calendar date (YYYY-MM-DD) in the given timezone. */
export function todayISOInTz(tz?: string | null): string {
  // en-CA renders as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: safeTz(tz),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

/** Format a timestamptz in the account's timezone, e.g. "14 Jun 2026 · 14:30". */
export function formatDateTime(iso: string, tz?: string | null): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString(undefined, {
    timeZone: safeTz(tz),
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const time = d.toLocaleTimeString(undefined, {
    timeZone: safeTz(tz),
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${date} · ${time}`;
}

/** Format a date-only string (YYYY-MM-DD) without timezone shifting. */
export function formatDay(dateOnly: string): string {
  return new Date(dateOnly + "T00:00:00Z").toLocaleDateString(undefined, {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
  });
}
