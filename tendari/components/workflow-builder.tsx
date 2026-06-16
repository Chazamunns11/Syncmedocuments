"use client";

import { useState } from "react";
import { addCustomWorkflow } from "@/app/dashboard/automations/actions";

type Step = { type: string; days?: number; name?: string; title?: string; body?: string; offset_days?: number; url?: string };

const STEP_TYPES = [
  { type: "wait", label: "Wait" },
  { type: "add_tag", label: "Add tag" },
  { type: "create_task", label: "Create task" },
  { type: "notify", label: "Notify me" },
  { type: "webhook", label: "Call webhook" },
];

export function WorkflowBuilder() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [trigger, setTrigger] = useState("contact_created");
  const [steps, setSteps] = useState<Step[]>([{ type: "notify", title: "New activity", body: "{name}" }]);

  const upd = (i: number, patch: Partial<Step>) => setSteps((s) => s.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
  const add = () => setSteps((s) => [...s, { type: "wait", days: 1 }]);
  const remove = (i: number) => setSteps((s) => s.filter((_, idx) => idx !== i));

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="btn-ghost mt-4">+ Build your own automation</button>
    );
  }

  return (
    <form action={addCustomWorkflow} className="card mt-4">
      <input type="hidden" name="steps" value={JSON.stringify(steps)} />
      <p className="label">Build your own automation</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <input name="name" className="input" placeholder="Automation name" value={name} onChange={(e) => setName(e.target.value)} />
        <select name="trigger_type" className="input" value={trigger} onChange={(e) => setTrigger(e.target.value)}>
          <option value="contact_created">When a contact is added</option>
          <option value="booking_created">When a booking is made</option>
          <option value="tag_added">When a tag is added</option>
        </select>
      </div>

      <p className="label mt-4">Then…</p>
      <div className="space-y-3">
        {steps.map((s, i) => (
          <div key={i} className="rounded-xl border border-deep-green/10 bg-canvas p-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">{i + 1}.</span>
              <select className="input" value={s.type} onChange={(e) => upd(i, { type: e.target.value })}>
                {STEP_TYPES.map((t) => <option key={t.type} value={t.type}>{t.label}</option>)}
              </select>
              <button type="button" onClick={() => remove(i)} className="ml-auto text-xs text-muted hover:text-red-600">remove</button>
            </div>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {s.type === "wait" && (
                <label className="text-xs text-muted">Days
                  <input type="number" min={0} className="input mt-1" value={s.days ?? 1} onChange={(e) => upd(i, { days: Number(e.target.value) })} />
                </label>
              )}
              {s.type === "add_tag" && (
                <label className="text-xs text-muted">Tag name
                  <input className="input mt-1" value={s.name ?? ""} onChange={(e) => upd(i, { name: e.target.value })} />
                </label>
              )}
              {s.type === "create_task" && (
                <>
                  <label className="text-xs text-muted">Task title (use {"{name}"})
                    <input className="input mt-1" value={s.title ?? ""} onChange={(e) => upd(i, { title: e.target.value })} />
                  </label>
                  <label className="text-xs text-muted">Due in (days)
                    <input type="number" min={0} className="input mt-1" value={s.offset_days ?? 0} onChange={(e) => upd(i, { offset_days: Number(e.target.value) })} />
                  </label>
                </>
              )}
              {s.type === "notify" && (
                <>
                  <label className="text-xs text-muted">Title
                    <input className="input mt-1" value={s.title ?? ""} onChange={(e) => upd(i, { title: e.target.value })} />
                  </label>
                  <label className="text-xs text-muted">Message (use {"{name}"})
                    <input className="input mt-1" value={s.body ?? ""} onChange={(e) => upd(i, { body: e.target.value })} />
                  </label>
                </>
              )}
              {s.type === "webhook" && (
                <label className="text-xs text-muted sm:col-span-2">Webhook URL
                  <input className="input mt-1" value={s.url ?? ""} onChange={(e) => upd(i, { url: e.target.value })} placeholder="https://…" />
                </label>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-3">
        <button type="button" onClick={add} className="btn-ghost px-3 py-1.5 text-xs">+ Add step</button>
        <button className="btn-primary">Save automation</button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-muted hover:text-deep-green">cancel</button>
      </div>
    </form>
  );
}
