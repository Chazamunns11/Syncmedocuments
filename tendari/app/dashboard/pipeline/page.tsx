import { createClient } from "@/lib/supabase/server";
import { createDeal } from "./actions";
import { PipelineBoard } from "@/components/pipeline-board";

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

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Pipeline</h1>
      <p className="mt-1 text-muted">See exactly where every client stands. Just drag a card to move it.</p>

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

      {/* Drag-and-drop board */}
      <PipelineBoard stages={stages} deals={deals} />
    </div>
  );
}
