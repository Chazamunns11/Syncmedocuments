import { createClient } from "@/lib/supabase/server";
import { addContact, deleteContact } from "./actions";

type Contact = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  created_at: string;
};

export default async function ContactsPage() {
  const supabase = createClient();
  const { data: contacts } = await supabase
    .from("contacts")
    .select("id, first_name, last_name, email, phone, created_at")
    .order("created_at", { ascending: false });

  const list = (contacts as Contact[]) || [];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-deep-green">Contacts</h1>
          <p className="mt-1 text-muted">Everyone in your world, in one tidy place.</p>
        </div>
      </div>

      {/* Add contact — inline, one line, no modal. Ease of use first. */}
      <form action={addContact} className="card mt-6">
        <p className="label">Add a contact</p>
        <div className="grid gap-3 sm:grid-cols-4">
          <input name="first_name" className="input" placeholder="First name" />
          <input name="last_name" className="input" placeholder="Last name" />
          <input name="email" type="email" className="input" placeholder="Email" />
          <input name="phone" className="input" placeholder="Phone" />
        </div>
        <div className="mt-3">
          <button className="btn-primary">Add contact</button>
        </div>
      </form>

      {/* List */}
      <div className="card mt-6 p-0">
        {list.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-deep-green">No contacts yet.</p>
            <p className="mt-1 text-sm text-muted">Add your first one above — it takes five seconds.</p>
          </div>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {list.map((c) => {
              const name = [c.first_name, c.last_name].filter(Boolean).join(" ") || "—";
              return (
                <li key={c.id} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-mint text-sm font-semibold text-deep-green">
                      {(c.first_name?.[0] || c.email?.[0] || "?").toUpperCase()}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-ink">{name}</p>
                      <p className="text-xs text-muted">{c.email || c.phone || "No contact details"}</p>
                    </div>
                  </div>
                  <form action={deleteContact}>
                    <input type="hidden" name="id" value={c.id} />
                    <button className="text-xs text-muted hover:text-red-600">Remove</button>
                  </form>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
