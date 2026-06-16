import { createClient } from "@/lib/supabase/server";
import { contactName } from "@/lib/contact";
import { formatMoney, formatDay } from "@/lib/format";
import { addPayment, deletePayment } from "./actions";

type Payment = {
  id: string;
  amount_cents: number;
  note: string | null;
  method: string | null;
  paid_on: string;
  contact_id: string | null;
};
type ContactRow = { id: string; first_name: string | null; last_name: string | null; email: string | null };

export default async function PaymentsPage() {
  const supabase = createClient();
  const [{ data: pData }, { data: cData }] = await Promise.all([
    supabase.from("payments").select("id, amount_cents, note, method, paid_on, contact_id").order("paid_on", { ascending: false }).limit(200),
    supabase.from("contacts").select("id, first_name, last_name, email").order("created_at", { ascending: false }).limit(500),
  ]);
  const payments = (pData as Payment[]) || [];
  const contacts = (cData as ContactRow[]) || [];
  const nameFor = (id: string | null) => {
    const c = contacts.find((x) => x.id === id);
    return c ? contactName(c, c.email || "—") : "—";
  };

  const now = new Date();
  const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const total = payments.reduce((s, p) => s + (p.amount_cents || 0), 0);
  const monthTotal = payments
    .filter((p) => new Date(p.paid_on + "T00:00:00Z") >= monthStart)
    .reduce((s, p) => s + (p.amount_cents || 0), 0);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Payments</h1>
      <p className="mt-1 text-muted">Log income as it comes in. (Automatic Stripe payments arrive later.)</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="card"><p className="text-sm text-muted">This month</p><p className="mt-1 text-2xl font-semibold text-deep-green">{formatMoney(monthTotal)}</p></div>
        <div className="card"><p className="text-sm text-muted">All time</p><p className="mt-1 text-2xl font-semibold text-deep-green">{formatMoney(total)}</p></div>
      </div>

      <form action={addPayment} className="card mt-6">
        <p className="label">Log a payment</p>
        <div className="grid gap-3 sm:grid-cols-4">
          <input name="amount" className="input" placeholder="Amount (e.g. 150)" inputMode="decimal" />
          <select name="contact_id" className="input" defaultValue="">
            <option value="">No contact</option>
            {contacts.map((c) => (
              <option key={c.id} value={c.id}>{contactName(c, c.email || "Unnamed")}</option>
            ))}
          </select>
          <select name="method" className="input" defaultValue="">
            <option value="">Method…</option>
            <option value="cash">Cash</option>
            <option value="bank">Bank transfer</option>
            <option value="card">Card</option>
            <option value="other">Other</option>
          </select>
          <input name="paid_on" type="date" className="input" />
        </div>
        <input name="note" className="input mt-3" placeholder="Note (optional) — e.g. 12-week package" />
        <div className="mt-3"><button className="btn-primary">Log payment</button></div>
      </form>

      <div className="card mt-6 p-0">
        {payments.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted">No payments logged yet.</p>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {payments.map((p) => (
              <li key={p.id} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <p className="text-sm font-medium text-ink">{formatMoney(p.amount_cents)} <span className="text-muted">· {nameFor(p.contact_id)}</span></p>
                  <p className="text-xs text-muted">{formatDay(p.paid_on)}{p.method ? ` · ${p.method}` : ""}{p.note ? ` · ${p.note}` : ""}</p>
                </div>
                <form action={deletePayment}>
                  <input type="hidden" name="id" value={p.id} />
                  <button className="text-xs text-muted hover:text-red-600">Delete</button>
                </form>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
