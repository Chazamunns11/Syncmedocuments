import { getAccount } from "@/lib/account";
import { updateBusinessName } from "./actions";

export default async function SettingsPage() {
  const account = await getAccount();

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Settings</h1>
      <p className="mt-1 text-muted">Your workspace, your rules.</p>

      <form action={updateBusinessName} className="card mt-6 max-w-lg">
        <p className="label">Business name</p>
        <input name="name" className="input" defaultValue={account?.businessName ?? ""} placeholder="e.g. Clarity Coaching" />
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
