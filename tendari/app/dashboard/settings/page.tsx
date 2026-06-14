import { getAccount } from "@/lib/account";
import { updateAccount } from "./actions";

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

export default async function SettingsPage() {
  const account = await getAccount();
  const tz = account?.timezone ?? "UTC";
  const tzOptions = TIMEZONES.includes(tz) ? TIMEZONES : [tz, ...TIMEZONES];

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
