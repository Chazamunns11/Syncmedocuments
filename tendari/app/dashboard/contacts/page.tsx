import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { contactName, contactInitial } from "@/lib/contact";
import { addContact, deleteContact, importContacts } from "./actions";

type Contact = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  created_at: string;
};

export default async function ContactsPage({
  searchParams,
}: {
  searchParams: { q?: string; tag?: string };
}) {
  const supabase = createClient();
  // Strip characters that break the PostgREST `or` filter syntax (, ( ))
  // and LIKE wildcards (% _ *) so search stays literal.
  const q = (searchParams.q || "").replace(/[,()%_*]/g, " ").trim();
  const tagId = searchParams.tag || "";

  const { data: allTags } = await supabase.from("tags").select("id, name").order("name");

  // If filtering by tag, resolve the contact ids that carry it first.
  let tagContactIds: string[] | null = null;
  if (tagId) {
    const { data: ct } = await supabase
      .from("contact_tags")
      .select("contact_id")
      .eq("tag_id", tagId);
    tagContactIds = (ct || []).map((r: { contact_id: string }) => r.contact_id);
  }

  let list: Contact[] = [];
  if (tagContactIds === null || tagContactIds.length > 0) {
    let query = supabase
      .from("contacts")
      .select("id, first_name, last_name, email, phone, created_at")
      .order("created_at", { ascending: false });
    if (q) {
      query = query.or(`first_name.ilike.%${q}%,last_name.ilike.%${q}%,email.ilike.%${q}%`);
    }
    if (tagContactIds) query = query.in("id", tagContactIds);
    const { data: contacts } = await query;
    list = (contacts as Contact[]) || [];
  }

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

      {/* Import from CSV */}
      <details className="card mt-4">
        <summary className="cursor-pointer text-sm font-medium text-deep-green">Import from CSV</summary>
        <p className="mt-2 text-xs text-muted">
          One contact per line: <code>first name, last name, email, phone</code>. A header row is optional.
          Existing emails are skipped. Moving from another tool? Paste your export here.
        </p>
        <form action={importContacts} className="mt-3">
          <textarea
            name="csv"
            className="input min-h-28 font-mono text-xs"
            placeholder={"Sarah, Lee, sarah@example.com, 07700 900001\nTom, Avery, tom@example.com"}
          />
          <div className="mt-3">
            <button className="btn-primary">Import contacts</button>
          </div>
        </form>
      </details>

      {/* Search + tag filter */}
      <form method="get" className="mt-6 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <input
          name="q"
          defaultValue={q}
          className="input"
          placeholder="Search contacts by name or email…"
        />
        <select name="tag" defaultValue={tagId} className="input">
          <option value="">All tags</option>
          {(allTags as { id: string; name: string }[] | null)?.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <button className="btn-ghost">Filter</button>
      </form>

      {/* List */}
      <div className="card mt-4 p-0">
        {list.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-deep-green">{q ? `No matches for “${q}”.` : "No contacts yet."}</p>
            <p className="mt-1 text-sm text-muted">
              {q ? "Try a different search." : "Add your first one above — it takes five seconds."}
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {list.map((c) => {
              const name = contactName(c, "—");
              return (
                <li key={c.id} className="flex items-center justify-between px-5 py-3.5">
                  <Link href={`/dashboard/contacts/${c.id}`} className="flex flex-1 items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-mint text-sm font-semibold text-deep-green">
                      {contactInitial(c)}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-ink hover:text-forest">{name}</p>
                      <p className="text-xs text-muted">{c.email || c.phone || "No contact details"}</p>
                    </div>
                  </Link>
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
