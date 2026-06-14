import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { formatDay, todayISOInTz } from "@/lib/format";
import { addTask, toggleTask, deleteTask } from "./actions";

type Task = { id: string; title: string; due_on: string | null; done: boolean };

function dueLabel(due: string | null, todayISO: string) {
  if (!due) return null;
  return {
    text: formatDay(due),
    overdue: due < todayISO, // ISO date strings compare correctly lexically
  };
}

export default async function TasksPage() {
  const supabase = createClient();
  const account = await getAccount();
  const todayISO = todayISOInTz(account?.timezone);
  const { data } = await supabase
    .from("tasks")
    .select("id, title, due_on, done")
    .order("done", { ascending: true })
    .order("due_on", { ascending: true, nullsFirst: false });
  const tasks = (data as Task[]) || [];
  const open = tasks.filter((t) => !t.done);
  const done = tasks.filter((t) => t.done);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Follow-ups</h1>
      <p className="mt-1 text-muted">Your manual to-do list. Soon, automations will create these for you.</p>

      <form action={addTask} className="card mt-6">
        <p className="label">Add a follow-up</p>
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
          <input name="title" className="input" placeholder="e.g. Send Sarah her welcome pack" />
          <input name="due_on" type="date" className="input" />
          <button className="btn-primary">Add</button>
        </div>
      </form>

      <div className="card mt-6 p-0">
        {open.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted">Nothing to do — nice. Add a follow-up above.</p>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {open.map((t) => {
              const due = dueLabel(t.due_on, todayISO);
              return (
                <li key={t.id} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <form action={toggleTask}>
                      <input type="hidden" name="id" value={t.id} />
                      <input type="hidden" name="done" value={String(t.done)} />
                      <button className="flex h-6 w-6 items-center justify-center rounded-full border border-deep-green/25 text-transparent hover:border-forest hover:text-forest">✓</button>
                    </form>
                    <span className="text-sm text-ink">{t.title}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {due && (
                      <span className={`rounded-full px-2 py-0.5 text-xs ${due.overdue ? "bg-red-50 text-red-600" : "bg-mint text-deep-green"}`}>
                        {due.overdue ? "Overdue · " : ""}{due.text}
                      </span>
                    )}
                    <form action={deleteTask}>
                      <input type="hidden" name="id" value={t.id} />
                      <button className="text-xs text-muted hover:text-red-600">Remove</button>
                    </form>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {done.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-sm font-semibold text-muted">Done ({done.length})</p>
          <div className="card p-0">
            <ul className="divide-y divide-deep-green/10">
              {done.map((t) => (
                <li key={t.id} className="flex items-center justify-between px-5 py-3">
                  <div className="flex items-center gap-3">
                    <form action={toggleTask}>
                      <input type="hidden" name="id" value={t.id} />
                      <input type="hidden" name="done" value={String(t.done)} />
                      <button className="flex h-6 w-6 items-center justify-center rounded-full bg-forest text-xs text-white">✓</button>
                    </form>
                    <span className="text-sm text-muted line-through">{t.title}</span>
                  </div>
                  <form action={deleteTask}>
                    <input type="hidden" name="id" value={t.id} />
                    <button className="text-xs text-muted hover:text-red-600">Remove</button>
                  </form>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
