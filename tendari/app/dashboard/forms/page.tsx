import { createClient } from "@/lib/supabase/server";
import { createForm, toggleForm, deleteForm } from "./actions";

type Form = { id: string; name: string; token: string; active: boolean };

export default async function FormsPage() {
  const supabase = createClient();
  const { data } = await supabase
    .from("forms")
    .select("id, name, token, active")
    .order("created_at", { ascending: false });
  const forms = (data as Form[]) || [];
  const base = process.env.NEXT_PUBLIC_SITE_URL || "";

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Lead forms</h1>
      <p className="mt-1 text-muted">Share a link. Every submission lands as a contact, automatically.</p>

      <form action={createForm} className="card mt-6">
        <p className="label">Create a form</p>
        <div className="flex gap-2">
          <input name="name" className="input" placeholder="e.g. Free discovery call" />
          <button className="btn-primary shrink-0">Create</button>
        </div>
      </form>

      <div className="card mt-6 p-0">
        {forms.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted">No forms yet. Create one above and share the link.</p>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {forms.map((f) => {
              const link = `${base}/f/${f.token}`;
              return (
                <li key={f.id} className="px-5 py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <a href={`/dashboard/forms/${f.id}`} className="text-sm font-medium text-ink hover:text-forest">{f.name} ✎</a>
                      <a href={link} target="_blank" className="text-xs text-forest hover:underline">
                        {base ? link : `/f/${f.token}`}
                      </a>
                      <p className="mt-0.5 text-xs text-muted">
                        Webhook (POST JSON): <code>{base ? `${base}/api/hooks/${f.token}` : `/api/hooks/${f.token}`}</code>
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${f.active ? "bg-mint text-deep-green" : "bg-deep-green/10 text-muted"}`}>
                        {f.active ? "Active" : "Off"}
                      </span>
                      <form action={toggleForm}>
                        <input type="hidden" name="id" value={f.id} />
                        <button className="text-xs font-medium text-forest hover:underline">{f.active ? "Disable" : "Enable"}</button>
                      </form>
                      <form action={deleteForm}>
                        <input type="hidden" name="id" value={f.id} />
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

      <p className="mt-4 text-xs text-muted">
        Tip: set <code>NEXT_PUBLIC_SITE_URL</code> so the shareable links show your full domain.
      </p>
    </div>
  );
}
