import { createClient } from "@/lib/supabase/server";
import { createDeal, moveDeal } from "./actions";

type Stage = { id: string; name: string; position: number };
type Deal = { id: string; title: string; stage_id: string; value_cents: number };

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

  const byStage = (stageId: string) => deals.filter((d) => d.stage_id === stageId);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Pipeline</h1>
      <p className="mt-1 text-muted">See exactly where every client stands. Move a card with the dropdown.</p>

      {/* Add deal */}
      <form action={createDeal} className="card mt-6">
        <p className="label">Add a deal</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <input name="title" className="input sm:col-span-2" placeholder="e.g. Sarah — 12-week package" />
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

      {/* Board */}
      <div className="mt-6 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        {stages.map((stage) => {
          const cards = byStage(stage.id);
          return (
            <div key={stage.id} className="rounded-2xl bg-white/70 p-3 ring-1 ring-deep-green/10">
              <div className="mb-3 flex items-center justify-between px-1">
                <span className="text-sm font-semibold text-deep-green">{stage.name}</span>
                <span className="rounded-full bg-mint px-2 text-xs text-deep-green">{cards.length}</span>
              </div>
              <div className="space-y-2">
                {cards.map((d) => (
                  <div key={d.id} className="rounded-xl border border-deep-green/10 bg-white p-3 shadow-soft">
                    <p className="text-sm font-medium text-ink">{d.title}</p>
                    <form action={moveDeal} className="mt-2">
                      <input type="hidden" name="id" value={d.id} />
                      <select
                        name="stage_id"
                        defaultValue={d.stage_id}
                        className="w-full rounded-lg border border-deep-green/15 bg-canvas px-2 py-1 text-xs text-muted"
                      >
                        {stages.map((s) => (
                          <option key={s.id} value={s.id}>Move to: {s.name}</option>
                        ))}
                      </select>
                      <button className="mt-1.5 text-[11px] font-medium text-forest">Move</button>
                    </form>
                  </div>
                ))}
                {cards.length === 0 && (
                  <p className="px-1 py-4 text-center text-xs text-muted">Empty</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
