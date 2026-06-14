import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Logo } from "@/components/logo";
import { computeSlots, type Rule, type Booked } from "@/lib/slots";
import { submitBooking } from "./actions";

export const dynamic = "force-dynamic";

type Ctx = {
  name: string;
  duration_min: number;
  timezone: string;
  rules: Rule[];
  booked: Booked[];
};

export default async function PublicBookingPage({
  params,
  searchParams,
}: {
  params: { token: string };
  searchParams: { start?: string; booked?: string; taken?: string };
}) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    notFound();
  }
  const supabase = createClient();
  const { data } = await supabase.rpc("get_booking_context", { p_token: params.token });
  if (!data) notFound();
  const ctx = data as Ctx;

  const booked = searchParams.booked === "1";
  const chosen = searchParams.start;

  const Shell = ({ children }: { children: React.ReactNode }) => (
    <main className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-lg">
        <div className="mb-6 flex justify-center"><Logo /></div>
        <div className="card">{children}</div>
        <p className="mt-4 text-center text-xs text-muted">Powered by Tendari</p>
      </div>
    </main>
  );

  if (booked) {
    return (
      <Shell>
        <div className="py-8 text-center">
          <h1 className="text-xl font-semibold text-deep-green">You&apos;re booked! 🌱</h1>
          <p className="mt-2 text-sm text-muted">A confirmation is on its way. See you soon.</p>
        </div>
      </Shell>
    );
  }

  // Step 2: collect details for the chosen slot.
  if (chosen) {
    const when = new Date(chosen).toLocaleString(undefined, {
      timeZone: ctx.timezone || "UTC",
      weekday: "long",
      day: "numeric",
      month: "long",
      hour: "2-digit",
      minute: "2-digit",
    });
    return (
      <Shell>
        <h1 className="text-xl font-semibold text-deep-green">{ctx.name}</h1>
        <p className="mt-1 text-sm text-muted">{when} ({ctx.timezone})</p>
        <form action={submitBooking} className="mt-6 space-y-4">
          <input type="hidden" name="token" value={params.token} />
          <input type="hidden" name="start" value={chosen} />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">First name</label>
              <input name="first_name" className="input" required />
            </div>
            <div>
              <label className="label">Last name</label>
              <input name="last_name" className="input" />
            </div>
          </div>
          <div>
            <label className="label">Email</label>
            <input name="email" type="email" className="input" required />
          </div>
          <div>
            <label className="label">Phone</label>
            <input name="phone" className="input" />
          </div>
          <div className="flex gap-2">
            <Link href={`/b/${params.token}`} className="btn-ghost">Back</Link>
            <button className="btn-primary flex-1">Confirm booking</button>
          </div>
        </form>
      </Shell>
    );
  }

  // Step 1: pick a slot.
  const days = computeSlots(
    { durationMin: ctx.duration_min, rules: ctx.rules || [], booked: ctx.booked || [], tz: ctx.timezone || "UTC" },
    { days: 14, minNoticeMin: 120 },
  );

  return (
    <Shell>
      <h1 className="text-xl font-semibold text-deep-green">{ctx.name}</h1>
      <p className="mt-1 text-sm text-muted">{ctx.duration_min} minutes · times shown in {ctx.timezone || "UTC"}</p>
      {searchParams.taken === "1" && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          Sorry, that slot was just taken — please pick another.
        </p>
      )}

      {days.length === 0 ? (
        <p className="mt-6 text-sm text-muted">No times available right now. Please check back soon.</p>
      ) : (
        <div className="mt-6 space-y-5">
          {days.map((d) => (
            <div key={d.dayLabel}>
              <p className="mb-2 text-sm font-semibold text-deep-green">{d.dayLabel}</p>
              <div className="flex flex-wrap gap-2">
                {d.slots.map((s) => (
                  <Link
                    key={s.iso}
                    href={`/b/${params.token}?start=${encodeURIComponent(s.iso)}`}
                    className="rounded-lg border border-forest/30 bg-white px-3 py-1.5 text-sm text-deep-green hover:border-forest hover:bg-mint/50"
                  >
                    {s.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Shell>
  );
}
