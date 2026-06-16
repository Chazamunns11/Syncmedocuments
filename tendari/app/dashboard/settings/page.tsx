import { getAccount } from "@/lib/account";
import { createClient } from "@/lib/supabase/server";
import { googleConfigured } from "@/lib/google";
import { updateAccount, disconnectGoogle } from "./actions";

const TIMEZONES = [
  "UTC",
  "Europe/London",
  "Europe/Dublin",
  "Europe/Paris",
  "Europe/Berlin",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Australia/Sydney",
  "Asia/Singapore",
  "Asia/Dubai",
];

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: { google?: string };
}) {
  const account = await getAccount();
  const tz = account?.timezone ?? "UTC";
  const tzOptions = TIMEZONES.includes(tz) ? TIMEZONES : [tz, ...TIMEZONES];

  const supabase = createClient();
  const { data: googleConnected } = await supabase.rpc("integration_status", { p_provider: "google" });
  const googleReady = googleConfigured();

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Settings</h1>
      <p className="mt-1 text-muted">Your workspace, your rules.</p>

      <form action={updateAccount} className="card mt-6 max-w-lg">
        <p className="label">Business name</p>
        <input name="name" className="input" defaultValue={account?.businessName ?? ""} placeholder="e.g. Clarity Coaching" />

        <p className="label mt-4">Timezone</p>
        <select name="timezone" className="input" defaultValue={tz}>
          {tzOptions.map((z) => (
            <option key={z} value={z}>{z}</option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted">Used for due dates and timeline timestamps.</p>

        <div className="mt-4">
          <button className="btn-primary">Save</button>
        </div>
      </form>

      <div className="card mt-6 max-w-lg">
        <p className="label">Integrations</p>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-ink">Google Calendar</p>
            <p className="text-xs text-muted">Bookings appear on your Google Calendar automatically.</p>
          </div>
          {!googleReady ? (
            <span className="text-xs text-muted">Not set up yet</span>
          ) : googleConnected ? (
            <form action={disconnectGoogle}>
              <button className="text-xs font-medium text-muted hover:text-red-600">Disconnect</button>
            </form>
          ) : (
            <a href="/api/google/connect" className="btn-primary px-4 py-2 text-xs">Connect</a>
          )}
        </div>
        {searchParams.google === "connected" && <p className="mt-2 text-xs text-forest">Google Calendar connected ✓</p>}
        {searchParams.google === "error" && <p className="mt-2 text-xs text-red-600">Couldn&apos;t connect — please try again.</p>}
        {searchParams.google === "notconfigured" && <p className="mt-2 text-xs text-muted">Google isn&apos;t configured on the server yet.</p>}
      </div>

      <div className="card mt-6 max-w-lg">
        <p className="label">Plan</p>
        <p className="text-sm text-ink">
          You&apos;re on the <span className="font-semibold capitalize">{account?.plan || "trial"}</span> plan.
        </p>
        <p className="mt-1 text-xs text-muted">Billing (Stripe) arrives in a later phase — no card charged during the trial setup.</p>
      </div>

      <div className="card mt-6 max-w-lg">
        <p className="label">Sign out</p>
        <form action="/auth/signout" method="post">
          <button className="btn-ghost">Sign out of Tendari</button>
        </form>
      </div>
    </div>
  );
}
