import { createClient } from "@/lib/supabase/server";
import { createDeal, reopenDeal } from "./actions";
import { PipelineBoard } from "@/components/pipeline-board";
import { formatMoney } from "@/lib/format";

type Stage = { id: string; name: string; position: number };
type Deal = { id: string; title: string; stage_id: string; value_cents: number };
type ClosedDeal = { id: string; title: string; value_cents: number; status: string };

export default async function PipelinePage() {
  const supabase = createClient();

  const { data: stagesData } = await supabase
    .from("stages")
    .select("id, name, position")
    .order("position", { ascending: true });
  const stages = (stagesData as Stage[]) || [];

  const { data: dealsData } = await supabase
    .from("deals")
    .select("id, title, stage_id, value_cents")
    .eq("status", "open");
  const deals = (dealsData as Deal[]) || [];

  const { data: closedData } = await supabase
    .from("deals")
    .select("id, title, value_cents, status")
    .in("status", ["won", "lost"])
    .order("updated_at", { ascending: false })
    .limit(50);
  const closed = (closedData as ClosedDeal[]) || [];
  const wonTotal = closed.filter((d) => d.status === "won").reduce((s, d) => s + (d.value_cents || 0), 0);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Pipeline</h1>
      <p className="mt-1 text-muted">See exactly where every client stands. Just drag a card to move it.</p>

      {/* Add deal */}
      <form action={createDeal} className="card mt-6">
        <p className="label">Add a deal</p>
        <div className="grid gap-3 sm:grid-cols-4">
          <input name="title" className="input sm:col-span-2" placeholder="e.g. Sarah — 12-week package" />
          <input name="value" className="input" placeholder="Value (e.g. 1200)" inputMode="decimal" />
          <select name="stage_id" className="input" defaultValue={stages[0]?.id}>
            {stages.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div className="mt-3">
          <button className="btn-primary">Add deal</button>
        </div>
      </form>

      {/* Drag-and-drop board */}
      <PipelineBoard stages={stages} deals={deals} />

      {/* Closed deals */}
      {closed.length > 0 && (
        <div className="mt-10">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-deep-green">Closed</h2>
            <span className="text-sm text-muted">Won total: {formatMoney(wonTotal)}</span>
          </div>
          <div className="card p-0">
            <ul className="divide-y divide-deep-green/10">
              {closed.map((d) => (
                <li key={d.id} className="flex items-center justify-between px-5 py-3">
                  <div className="flex items-center gap-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        d.status === "won" ? "bg-mint text-deep-green" : "bg-red-50 text-red-600"
                      }`}
                    >
                      {d.status === "won" ? "Won" : "Lost"}
                    </span>
                    <span className="text-sm text-ink">{d.title}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {d.value_cents > 0 && <span className="text-xs text-muted">{formatMoney(d.value_cents)}</span>}
                    <form action={reopenDeal}>
                      <input type="hidden" name="id" value={d.id} />
                      <button className="text-xs font-medium text-forest hover:underline">Reopen</button>
                    </form>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
