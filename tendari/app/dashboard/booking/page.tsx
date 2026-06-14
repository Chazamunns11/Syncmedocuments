import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { formatDateTime } from "@/lib/format";
import {
  createMeetingType,
  deleteMeetingType,
  addAvailability,
  deleteAvailability,
} from "./actions";

type MeetingType = { id: string; name: string; token: string; duration_min: number };
type Rule = { id: string; weekday: number; start_min: number; end_min: number };
type Booking = { id: string; name: string | null; email: string | null; starts_at: string };

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const hhmm = (min: number) =>
  `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;

export default async function BookingPage() {
  const supabase = createClient();
  const account = await getAccount();
  const base = process.env.NEXT_PUBLIC_SITE_URL || "";

  const [{ data: mtData }, { data: ruleData }, { data: bookingData }] = await Promise.all([
    supabase.from("meeting_types").select("id, name, token, duration_min").order("created_at"),
    supabase.from("availability_rules").select("id, weekday, start_min, end_min").order("weekday"),
    supabase
      .from("bookings")
      .select("id, name, email, starts_at")
      .eq("status", "confirmed")
      .gte("starts_at", new Date().toISOString())
      .order("starts_at")
      .limit(20),
  ]);

  const meetingTypes = (mtData as MeetingType[]) || [];
  const rules = (ruleData as Rule[]) || [];
  const bookings = (bookingData as Booking[]) || [];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Booking</h1>
      <p className="mt-1 text-muted">
        Set when you&apos;re free, share a link, and let clients book themselves in. Times use your
        timezone ({account?.timezone || "UTC"}) — change it in Settings.
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* Meeting types */}
        <div>
          <form action={createMeetingType} className="card">
            <p className="label">Add a meeting type</p>
            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <input name="name" className="input" placeholder="e.g. Discovery call" />
              <input name="duration" type="number" min={5} step={5} defaultValue={30} className="input w-28" title="Minutes" />
            </div>
            <div className="mt-3">
              <button className="btn-primary">Add</button>
            </div>
          </form>

          <div className="card mt-4 p-0">
            {meetingTypes.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted">No meeting types yet.</p>
            ) : (
              <ul className="divide-y divide-deep-green/10">
                {meetingTypes.map((m) => (
                  <li key={m.id} className="px-5 py-3.5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-ink">{m.name} · {m.duration_min} min</p>
                        <a href={`${base}/b/${m.token}`} target="_blank" className="text-xs text-forest hover:underline">
                          {base ? `${base}/b/${m.token}` : `/b/${m.token}`}
                        </a>
                      </div>
                      <form action={deleteMeetingType}>
                        <input type="hidden" name="id" value={m.id} />
                        <button className="text-xs text-muted hover:text-red-600">Delete</button>
                      </form>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Availability */}
        <div>
          <form action={addAvailability} className="card">
            <p className="label">Add availability</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <select name="weekday" className="input" defaultValue={1}>
                {DAYS.map((d, i) => (
                  <option key={d} value={i}>{d}</option>
                ))}
              </select>
              <input name="start" type="time" className="input" defaultValue="09:00" />
              <input name="end" type="time" className="input" defaultValue="17:00" />
              <button className="btn-primary">Add</button>
            </div>
          </form>

          <div className="card mt-4 p-0">
            {rules.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted">No availability set. Add a window above.</p>
            ) : (
              <ul className="divide-y divide-deep-green/10">
                {rules.map((r) => (
                  <li key={r.id} className="flex items-center justify-between px-5 py-3">
                    <span className="text-sm text-ink">
                      {DAYS[r.weekday]} · {hhmm(r.start_min)}–{hhmm(r.end_min)}
                    </span>
                    <form action={deleteAvailability}>
                      <input type="hidden" name="id" value={r.id} />
                      <button className="text-xs text-muted hover:text-red-600">Remove</button>
                    </form>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Upcoming bookings */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-deep-green">Upcoming bookings</h2>
        <div className="card mt-3 p-0">
          {bookings.length === 0 ? (
            <p className="p-6 text-center text-sm text-muted">No bookings yet.</p>
          ) : (
            <ul className="divide-y divide-deep-green/10">
              {bookings.map((b) => (
                <li key={b.id} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <p className="text-sm font-medium text-ink">{b.name || b.email || "Guest"}</p>
                    <p className="text-xs text-muted">{b.email}</p>
                  </div>
                  <span className="text-xs text-muted">{formatDateTime(b.starts_at, account?.timezone)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
