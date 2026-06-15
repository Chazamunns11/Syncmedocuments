import { createClient } from "@/lib/supabase/server";
import { contactName } from "@/lib/contact";
import { createContract, voidContract, deleteContract } from "./actions";

type Contract = { id: string; title: string; token: string; status: string; signed_name: string | null; contact_id: string | null };
type ContactRow = { id: string; first_name: string | null; last_name: string | null; email: string | null };

export default async function ContractsPage() {
  const supabase = createClient();
  const base = process.env.NEXT_PUBLIC_SITE_URL || "";

  const [{ data: cData }, { data: contactsData }] = await Promise.all([
    supabase.from("contracts").select("id, title, token, status, signed_name, contact_id").order("created_at", { ascending: false }),
    supabase.from("contacts").select("id, first_name, last_name, email").order("created_at", { ascending: false }).limit(500),
  ]);
  const contracts = (cData as Contract[]) || [];
  const contacts = (contactsData as ContactRow[]) || [];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Contracts</h1>
      <p className="mt-1 text-muted">Send an agreement, get it e-signed, and it lands on the client&apos;s timeline.</p>

      <form action={createContract} className="card mt-6">
        <p className="label">New contract</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <input name="title" className="input" placeholder="e.g. Coaching agreement" />
          <select name="contact_id" className="input" defaultValue="">
            <option value="">No contact (optional)</option>
            {contacts.map((c) => (
              <option key={c.id} value={c.id}>{contactName(c, c.email || "Unnamed")}</option>
            ))}
          </select>
        </div>
        <textarea name="body" className="input mt-3 min-h-40" placeholder="Paste your agreement text here. The client reads this and types their name to sign." />
        <div className="mt-3">
          <button className="btn-primary">Create &amp; get signing link</button>
        </div>
      </form>

      <div className="card mt-6 p-0">
        {contracts.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted">No contracts yet. Create one above and share the signing link.</p>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {contracts.map((c) => {
              const link = `${base}/sign/${c.token}`;
              return (
                <li key={c.id} className="px-5 py-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-ink">{c.title}</p>
                      {c.status === "signed" ? (
                        <p className="text-xs text-forest">Signed by {c.signed_name}</p>
                      ) : c.status === "void" ? (
                        <p className="text-xs text-muted">Void</p>
                      ) : (
                        <a href={link} target="_blank" className="text-xs text-forest hover:underline">{base ? link : `/sign/${c.token}`}</a>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${
                        c.status === "signed" ? "bg-mint text-deep-green" : c.status === "void" ? "bg-deep-green/10 text-muted" : "bg-mint/50 text-deep-green"
                      }`}>{c.status}</span>
                      {c.status === "sent" && (
                        <form action={voidContract}>
                          <input type="hidden" name="id" value={c.id} />
                          <button className="text-xs text-muted hover:text-red-600">Void</button>
                        </form>
                      )}
                      <form action={deleteContract}>
                        <input type="hidden" name="id" value={c.id} />
                        <button className="text-xs text-muted hover:text-red-600">Delete</button>
                      </form>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
