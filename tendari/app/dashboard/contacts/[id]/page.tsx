import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { updateContact, addNote, deleteContact } from "../actions";

type Activity = { id: string; type: string; body: string | null; title: string | null; created_at: string };

function timeAgo(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) +
    " · " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export default async function ContactDetailPage({ params }: { params: { id: string } }) {
  const supabase = createClient();

  const { data: contact } = await supabase
    .from("contacts")
    .select("id, first_name, last_name, email, phone, notes, created_at")
    .eq("id", params.id)
    .single();

  if (!contact) notFound();

  const { data: acts } = await supabase
    .from("activities")
    .select("id, type, body, title, created_at")
    .eq("contact_id", params.id)
    .order("created_at", { ascending: false });
  const activities = (acts as Activity[]) || [];

  const name = [contact.first_name, contact.last_name].filter(Boolean).join(" ") || "Unnamed contact";

  return (
    <div>
      <Link href="/dashboard/contacts" className="text-sm text-muted hover:text-deep-green">← Back to contacts</Link>

      <div className="mt-3 flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-mint text-lg font-semibold text-deep-green">
          {(contact.first_name?.[0] || contact.email?.[0] || "?").toUpperCase()}
        </span>
        <div>
          <h1 className="text-2xl font-semibold text-deep-green">{name}</h1>
          <p className="text-sm text-muted">{contact.email || contact.phone || "No contact details yet"}</p>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        {/* Details / edit */}
        <div className="lg:col-span-2">
          <form action={updateContact} className="card">
            <input type="hidden" name="id" value={contact.id} />
            <p className="label">Details</p>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <input name="first_name" className="input" placeholder="First name" defaultValue={contact.first_name ?? ""} />
                <input name="last_name" className="input" placeholder="Last name" defaultValue={contact.last_name ?? ""} />
              </div>
              <input name="email" type="email" className="input" placeholder="Email" defaultValue={contact.email ?? ""} />
              <input name="phone" className="input" placeholder="Phone" defaultValue={contact.phone ?? ""} />
              <textarea name="notes" className="input min-h-20" placeholder="Background notes…" defaultValue={contact.notes ?? ""} />
            </div>
            <div className="mt-4 flex items-center justify-between">
              <button className="btn-primary">Save changes</button>
            </div>
          </form>

          <form action={deleteContact} className="mt-3 text-right">
            <input type="hidden" name="id" value={contact.id} />
            <button className="text-xs text-muted hover:text-red-600">Delete contact</button>
          </form>
        </div>

        {/* Timeline */}
        <div className="lg:col-span-3">
          <div className="card">
            <p className="label">Add a note</p>
            <form action={addNote} className="flex gap-2">
              <input type="hidden" name="contact_id" value={contact.id} />
              <input name="body" className="input" placeholder="Logged a call, sent a proposal…" />
              <button className="btn-primary shrink-0">Add</button>
            </form>
          </div>

          <div className="card mt-4 p-0">
            <p className="px-5 pt-5 text-sm font-semibold text-deep-green">Timeline</p>
            {activities.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted">Nothing logged yet. Add a note above.</p>
            ) : (
              <ul className="mt-2 divide-y divide-deep-green/10">
                {activities.map((a) => (
                  <li key={a.id} className="px-5 py-3.5">
                    <p className="text-sm text-ink">{a.body || a.title || a.type}</p>
                    <p className="mt-0.5 text-xs text-muted">{timeAgo(a.created_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
