"use client";

import { useState } from "react";
import { updateMeetingType } from "@/app/dashboard/booking/actions";

type Q = { key: string; label: string; type: string; required: boolean; options?: string[] };
type MeetingType = {
  id: string;
  name: string;
  duration_min: number;
  description: string | null;
  buffer_min: number;
  min_notice_min: number;
  max_per_day: number | null;
  questions: Q[];
};

const TYPES = ["text", "textarea", "select", "checkbox", "number"];
const slug = (s: string) => s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "q";

export function MeetingTypeEditor({ mt }: { mt: MeetingType }) {
  const [questions, setQuestions] = useState<Q[]>(mt.questions || []);
  const [saved, setSaved] = useState(false);

  const upd = (i: number, patch: Partial<Q>) => {
    setQuestions((q) => q.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
    setSaved(false);
  };

  return (
    <form action={async (fd) => { await updateMeetingType(fd); setSaved(true); }} className="space-y-4">
      <input type="hidden" name="id" value={mt.id} />
      <input type="hidden" name="questions" value={JSON.stringify(questions)} />

      <div className="card">
        <label className="label">Name</label>
        <input name="name" className="input" defaultValue={mt.name} />
        <label className="label mt-3">Description (shown on the booking page)</label>
        <textarea name="description" className="input min-h-20" defaultValue={mt.description ?? ""} placeholder="What this call is for, how to prepare…" />
      </div>

      <div className="card grid gap-3 sm:grid-cols-4">
        <div><label className="label">Duration (min)</label><input name="duration_min" type="number" min={5} step={5} className="input" defaultValue={mt.duration_min} /></div>
        <div><label className="label">Buffer (min)</label><input name="buffer_min" type="number" min={0} step={5} className="input" defaultValue={mt.buffer_min} /></div>
        <div><label className="label">Min notice (min)</label><input name="min_notice_min" type="number" min={0} step={30} className="input" defaultValue={mt.min_notice_min} /></div>
        <div><label className="label">Max / day</label><input name="max_per_day" type="number" min={1} className="input" defaultValue={mt.max_per_day ?? ""} placeholder="∞" /></div>
      </div>

      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <p className="label mb-0">Booking questions (asked when someone books)</p>
          <button type="button" onClick={() => { setQuestions((q) => [...q, { key: `q_${q.length + 1}`, label: "New question", type: "text", required: false }]); setSaved(false); }} className="btn-ghost px-3 py-1.5 text-xs">+ Add question</button>
        </div>
        {questions.length === 0 && <p className="text-sm text-muted">No extra questions. Name, email and phone are always collected.</p>}
        <div className="space-y-3">
          {questions.map((q, i) => (
            <div key={i} className="rounded-xl border border-deep-green/10 bg-canvas p-3">
              <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                <input className="input" value={q.label} placeholder="Question" onChange={(e) => upd(i, { label: e.target.value, key: q.key || slug(e.target.value) })} />
                <select className="input" value={q.type} onChange={(e) => upd(i, { type: e.target.value })}>
                  {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <label className="flex items-center gap-1 px-2 text-xs text-muted">
                  <input type="checkbox" checked={q.required} onChange={(e) => upd(i, { required: e.target.checked })} /> required
                </label>
              </div>
              {q.type === "select" && (
                <input className="input mt-2 text-xs" value={(q.options || []).join(", ")} placeholder="options, comma separated" onChange={(e) => upd(i, { options: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
              )}
              <button type="button" onClick={() => { setQuestions((qs) => qs.filter((_, idx) => idx !== i)); setSaved(false); }} className="mt-2 text-xs text-muted hover:text-red-600">remove</button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="btn-primary">Save</button>
        {saved && <span className="text-sm text-forest">Saved ✓</span>}
      </div>
    </form>
  );
}
