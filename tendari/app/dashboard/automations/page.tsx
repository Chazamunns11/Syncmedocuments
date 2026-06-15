import { createClient } from "@/lib/supabase/server";
import { TEMPLATES } from "@/lib/automation-templates";
import { addWorkflowFromTemplate, toggleWorkflow, deleteWorkflow } from "./actions";

type Step = Record<string, unknown>;
type Workflow = { id: string; name: string; trigger_type: string; steps: Step[]; active: boolean };

const TRIGGER_LABEL: Record<string, string> = {
  contact_created: "When a contact is added",
  booking_created: "When a booking is made",
  tag_added: "When a tag is added",
};

function stepSummary(step: Step): string {
  const type = String(step.type);
  switch (type) {
    case "wait": return `wait ${Number(step.days ?? 0)} day(s)`;
    case "add_tag": return `tag “${String(step.name)}”`;
    case "create_task": return `create task “${String(step.title)}”`;
    case "notify": return "notify you";
    default: return type;
  }
}

export default async function AutomationsPage() {
  const supabase = createClient();
  const { data } = await supabase
    .from("workflows")
    .select("id, name, trigger_type, steps, active")
    .order("created_at", { ascending: false });
  const workflows = (data as Workflow[]) || [];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Automations</h1>
      <p className="mt-1 text-muted">Set it once, and Tendari does the chasing. Runs automatically in the background.</p>

      {/* Templates */}
      <div className="mt-6">
        <p className="label">Add an automation</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(TEMPLATES).map(([key, t]) => (
            <form action={addWorkflowFromTemplate} key={key} className="card flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-ink">{t.name}</p>
                <p className="text-xs text-muted">
                  {TRIGGER_LABEL[t.trigger_type]} → {t.steps.map(stepSummary).join(" → ")}
                </p>
              </div>
              <input type="hidden" name="template" value={key} />
              <button className="btn-primary shrink-0">Add</button>
            </form>
          ))}
        </div>
      </div>

      {/* Active automations */}
      <div className="mt-8">
        <p className="mb-2 text-sm font-semibold text-deep-green">Your automations</p>
        <div className="card p-0">
          {workflows.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted">None yet. Add one above — it starts working immediately.</p>
          ) : (
            <ul className="divide-y divide-deep-green/10">
              {workflows.map((w) => (
                <li key={w.id} className="flex items-center justify-between gap-4 px-5 py-3.5">
                  <div>
                    <p className="text-sm font-medium text-ink">{w.name}</p>
                    <p className="text-xs text-muted">
                      {TRIGGER_LABEL[w.trigger_type] || w.trigger_type} → {(w.steps || []).map(stepSummary).join(" → ")}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${w.active ? "bg-mint text-deep-green" : "bg-deep-green/10 text-muted"}`}>
                      {w.active ? "On" : "Off"}
                    </span>
                    <form action={toggleWorkflow}>
                      <input type="hidden" name="id" value={w.id} />
                      <button className="text-xs font-medium text-forest hover:underline">{w.active ? "Pause" : "Enable"}</button>
                    </form>
                    <form action={deleteWorkflow}>
                      <input type="hidden" name="id" value={w.id} />
                      <button className="text-xs text-muted hover:text-red-600">Delete</button>
                    </form>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <p className="mt-3 text-xs text-muted">
          Email steps are coming once an email provider is connected — for now automations can tag
          contacts, create follow-up tasks, and notify you.
        </p>
      </div>
    </div>
  );
}
