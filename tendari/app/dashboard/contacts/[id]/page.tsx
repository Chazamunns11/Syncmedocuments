import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { contactName, contactInitial } from "@/lib/contact";
import { formatDateTime } from "@/lib/format";
import { getAccount } from "@/lib/account";
import { updateContact, addNote, deleteContact } from "../actions";
import { addTagByName, removeContactTag } from "../tag-actions";
import { createDeal } from "../../pipeline/actions";
import { addTask, toggleTask } from "../../tasks/actions";

type Activity = { id: string; type: string; body: string | null; title: string | null; created_at: string };
type Deal = { id: string; title: string; stage_id: string };
type Stage = { id: string; name: string };
type Task = { id: string; title: string; done: boolean; due_on: string | null };
type TagLink = { tag_id: string; tags: { name: string; color: string } | { name: string; color: string }[] | null };

export default async function ContactDetailPage({ params }: { params: { id: string } }) {
  const supabase = createClient();
  const account = await getAccount();
  const tz = account?.timezone;

  const { data: contact } = await supabase
    .from("contacts")
    .select("id, first_name, last_name, email, phone, notes, created_at")
    .eq("id", params.id)
    .single();

  if (!contact) notFound();

  const [{ data: acts }, { data: dealRows }, { data: stageRows }, { data: taskRows }, { data: tagRows }] =
    await Promise.all([
      supabase
        .from("activities")
        .select("id, type, body, title, created_at")
        .eq("contact_id", params.id)
        .order("created_at", { ascending: false }),
      supabase.from("deals").select("id, title, stage_id").eq("contact_id", params.id),
      supabase.from("stages").select("id, name").order("position", { ascending: true }),
      supabase
        .from("tasks")
        .select("id, title, done, due_on")
        .eq("contact_id", params.id)
        .order("done", { ascending: true }),
      supabase.from("contact_tags").select("tag_id, tags(name, color)").eq("contact_id", params.id),
    ]);

  const activities = (acts as Activity[]) || [];
  const deals = (dealRows as Deal[]) || [];
  const stages = (stageRows as Stage[]) || [];
  const tasks = (taskRows as Task[]) || [];
  const tags = ((tagRows as TagLink[]) || []).map((r) => {
    const t = Array.isArray(r.tags) ? r.tags[0] : r.tags;
    return { tag_id: r.tag_id, name: t?.name ?? "", color: t?.color ?? "#8FB7A3" };
  });
  const stageName = (id: string) => stages.find((s) => s.id === id)?.name ?? "";
  const firstStage = stages[0]?.id ?? "";

  const name = contactName(contact);

  return (
    <div>
      <Link href="/dashboard/contacts" className="text-sm text-muted hover:text-deep-green">← Back to contacts</Link>

      <div className="mt-3 flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-mint text-lg font-semibold text-deep-green">
          {contactInitial(contact)}
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

          {/* Tags */}
          <div className="card mt-4">
            <p className="label">Tags</p>
            <div className="mb-3 flex flex-wrap gap-2">
              {tags.length === 0 && <span className="text-sm text-muted">No tags yet.</span>}
              {tags.map((t) => (
                <span key={t.tag_id} className="inline-flex items-center gap-1.5 rounded-full bg-mint px-2.5 py-1 text-xs text-deep-green">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: t.color }} />
                  {t.name}
                  <form action={removeContactTag} className="inline">
                    <input type="hidden" name="contact_id" value={contact.id} />
                    <input type="hidden" name="tag_id" value={t.tag_id} />
                    <button className="text-deep-green/60 hover:text-red-600" aria-label={`Remove ${t.name}`}>×</button>
                  </form>
                </span>
              ))}
            </div>
            <form action={addTagByName} className="flex gap-2">
              <input type="hidden" name="contact_id" value={contact.id} />
              <input name="name" className="input" placeholder="Add a tag (e.g. VIP, Lead)" />
              <input name="color" type="color" defaultValue="#8FB7A3" className="h-9 w-11 shrink-0 rounded border border-deep-green/15" title="Tag colour" />
              <button className="btn-primary shrink-0">Add</button>
            </form>
          </div>

          {/* Deals for this contact */}
          <div className="card mt-4">
            <p className="label">Deals</p>
            {deals.length > 0 && (
              <ul className="mb-3 space-y-1.5">
                {deals.map((d) => (
                  <li key={d.id} className="flex items-center justify-between text-sm">
                    <span className="text-ink">{d.title}</span>
                    <span className="rounded-full bg-mint px-2 py-0.5 text-xs text-deep-green">{stageName(d.stage_id)}</span>
                  </li>
                ))}
              </ul>
            )}
            <form action={createDeal} className="flex gap-2">
              <input type="hidden" name="contact_id" value={contact.id} />
              <input type="hidden" name="stage_id" value={firstStage} />
              <input name="title" className="input" placeholder="New deal title…" />
              <button className="btn-primary shrink-0">Add</button>
            </form>
          </div>

          {/* Follow-ups for this contact */}
          <div className="card mt-4">
            <p className="label">Follow-ups</p>
            {tasks.length > 0 && (
              <ul className="mb-3 space-y-1.5">
                {tasks.map((t) => (
                  <li key={t.id} className="flex items-center gap-2 text-sm">
                    <form action={toggleTask}>
                      <input type="hidden" name="id" value={t.id} />
                      <input type="hidden" name="done" value={String(t.done)} />
                      <input type="hidden" name="contact_id" value={contact.id} />
                      <button className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${t.done ? "bg-forest text-white" : "border border-deep-green/25 text-transparent hover:text-forest"}`}>✓</button>
                    </form>
                    <span className={t.done ? "text-muted line-through" : "text-ink"}>{t.title}</span>
                  </li>
                ))}
              </ul>
            )}
            <form action={addTask} className="flex gap-2">
              <input type="hidden" name="contact_id" value={contact.id} />
              <input name="title" className="input" placeholder="New follow-up…" />
              <button className="btn-primary shrink-0">Add</button>
            </form>
          </div>

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
                    <p className="mt-0.5 text-xs text-muted">{formatDateTime(a.created_at, tz)}</p>
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
