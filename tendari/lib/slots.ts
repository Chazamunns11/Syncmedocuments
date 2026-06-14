// Pure slot computation for the booking page. Times in availability rules are
// minutes-from-midnight in the account's timezone; we convert each concrete
// day's wall-clock window to UTC instants (DST-aware via Intl offset).

export type Rule = { weekday: number; start_min: number; end_min: number };
export type Booked = { start: string; end: string };
export type Slot = { iso: string; label: string };
export type DaySlots = { dayLabel: string; slots: Slot[] };

/** Offset (ms) of `tz` from UTC at the given instant. */
function tzOffsetMs(date: Date, tz: string): number {
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const p = Object.fromEntries(dtf.formatToParts(date).map((x) => [x.type, x.value]));
  const asUTC = Date.UTC(
    Number(p.year),
    Number(p.month) - 1,
    Number(p.day),
    Number(p.hour),
    Number(p.minute),
    Number(p.second),
  );
  return asUTC - date.getTime();
}

/** Convert a wall-clock time (y/m/d + minutes) in `tz` to a UTC Date. */
function wallToUtc(y: number, m: number, d: number, minutes: number, tz: string): Date {
  const h = Math.floor(minutes / 60);
  const min = minutes % 60;
  const guess = Date.UTC(y, m, d, h, min);
  // Adjust by the offset at the guessed instant (one pass handles all but the
  // rare DST-transition minute, which we don't schedule on).
  const offset = tzOffsetMs(new Date(guess), tz);
  return new Date(guess - offset);
}

/** The y/m/d calendar parts of `date` as seen in `tz`. */
function ymdInTz(date: Date, tz: string): { y: number; m: number; d: number } {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
      .formatToParts(date)
      .map((x) => [x.type, x.value]),
  );
  return { y: Number(p.y || p.year), m: Number(p.month) - 1, d: Number(p.day) };
}

export function computeSlots(
  opts: {
    durationMin: number;
    rules: Rule[];
    booked: Booked[];
    tz: string;
  },
  cfg: { days?: number; minNoticeMin?: number; granularityMin?: number } = {},
): DaySlots[] {
  const tz = opts.tz || "UTC";
  const days = cfg.days ?? 14;
  const minNoticeMs = (cfg.minNoticeMin ?? 120) * 60_000;
  const gran = cfg.granularityMin ?? opts.durationMin;
  const now = Date.now();
  const earliest = now + minNoticeMs;

  const busy = opts.booked.map((b) => ({
    start: new Date(b.start).getTime(),
    end: new Date(b.end).getTime(),
  }));

  const out: DaySlots[] = [];

  for (let i = 0; i < days; i++) {
    const dayDate = new Date(now + i * 86_400_000);
    const { y, m, d } = ymdInTz(dayDate, tz);
    // weekday for that calendar day (noon UTC of the wall date avoids edge issues)
    const weekday = new Date(Date.UTC(y, m, d, 12)).getUTCDay();
    const rules = opts.rules.filter((r) => r.weekday === weekday);
    if (rules.length === 0) continue;

    const slots: Slot[] = [];
    for (const r of rules) {
      for (let t = r.start_min; t + opts.durationMin <= r.end_min; t += gran) {
        const start = wallToUtc(y, m, d, t, tz);
        const startMs = start.getTime();
        const endMs = startMs + opts.durationMin * 60_000;
        if (startMs < earliest) continue;
        if (busy.some((b) => b.start < endMs && b.end > startMs)) continue;
        slots.push({
          iso: start.toISOString(),
          label: start.toLocaleTimeString(undefined, {
            timeZone: tz,
            hour: "2-digit",
            minute: "2-digit",
          }),
        });
      }
    }
    if (slots.length === 0) continue;

    const dayLabel = new Date(Date.UTC(y, m, d, 12)).toLocaleDateString(undefined, {
      timeZone: "UTC",
      weekday: "short",
      day: "numeric",
      month: "short",
    });
    out.push({ dayLabel, slots });
  }

  return out;
}
