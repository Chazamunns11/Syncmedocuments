import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { formatDateTime } from "@/lib/format";
import { markAllRead, markRead, deleteNotification } from "./actions";

type Note = { id: string; type: string; title: string; body: string | null; read: boolean; created_at: string };

export default async function NotificationsPage() {
  const supabase = createClient();
  const account = await getAccount();
  const { data } = await supabase
    .from("notifications")
    .select("id, type, title, body, read, created_at")
    .order("created_at", { ascending: false })
    .limit(100);
  const notes = (data as Note[]) || [];
  const unread = notes.filter((n) => !n.read).length;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-deep-green">Notifications</h1>
          <p className="mt-1 text-muted">New leads and bookings show up here.</p>
        </div>
        {unread > 0 && (
          <form action={markAllRead}>
            <button className="btn-ghost">Mark all read</button>
          </form>
        )}
      </div>

      <div className="card mt-6 p-0">
        {notes.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted">Nothing yet. When a lead or booking comes in, you&apos;ll see it here.</p>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {notes.map((n) => (
              <li key={n.id} className={`flex items-start justify-between gap-4 px-5 py-3.5 ${n.read ? "" : "bg-mint/30"}`}>
                <div className="flex items-start gap-3">
                  <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-transparent" : "bg-forest"}`} />
                  <div>
                    <p className="text-sm font-medium text-ink">{n.title}</p>
                    {n.body && <p className="text-sm text-muted">{n.body}</p>}
                    <p className="mt-0.5 text-xs text-muted">{formatDateTime(n.created_at, account?.timezone)}</p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  {!n.read && (
                    <form action={markRead}>
                      <input type="hidden" name="id" value={n.id} />
                      <button className="text-xs font-medium text-forest hover:underline">Mark read</button>
                    </form>
                  )}
                  <form action={deleteNotification}>
                    <input type="hidden" name="id" value={n.id} />
                    <button className="text-xs text-muted hover:text-red-600">Delete</button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
