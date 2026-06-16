"use client";

import { useState } from "react";
import { updateForm } from "@/app/dashboard/forms/actions";

type Field = { key: string; label: string; type: string; required: boolean; options?: string[] };

const TYPES = ["text", "textarea", "email", "phone", "number", "select", "checkbox", "date"];

function slug(s: string) {
  return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "field";
}

export function FormBuilder({
  id,
  initialName,
  initialFields,
}: {
  id: string;
  initialName: string;
  initialFields: Field[];
}) {
  const [name, setName] = useState(initialName);
  const [fields, setFields] = useState<Field[]>(
    initialFields.length ? initialFields : [{ key: "email", label: "Email", type: "email", required: true }],
  );
  const [saved, setSaved] = useState(false);

  function update(i: number, patch: Partial<Field>) {
    setFields((f) => f.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
    setSaved(false);
  }
  function addField() {
    setFields((f) => [...f, { key: `field_${f.length + 1}`, label: "New question", type: "text", required: false }]);
    setSaved(false);
  }
  function remove(i: number) {
    setFields((f) => f.filter((_, idx) => idx !== i));
    setSaved(false);
  }
  function move(i: number, dir: -1 | 1) {
    setFields((f) => {
      const j = i + dir;
      if (j < 0 || j >= f.length) return f;
      const copy = [...f];
      [copy[i], copy[j]] = [copy[j], copy[i]];
      return copy;
    });
    setSaved(false);
  }

  return (
    <form
      action={async (fd) => {
        await updateForm(fd);
        setSaved(true);
      }}
      className="space-y-4"
    >
      <input type="hidden" name="id" value={id} />
      <input type="hidden" name="fields" value={JSON.stringify(fields)} />

      <div className="card">
        <label className="label">Form name</label>
        <input name="name" className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </div>

      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <p className="label mb-0">Fields</p>
          <button type="button" onClick={addField} className="btn-ghost px-3 py-1.5 text-xs">+ Add field</button>
        </div>
        <p className="mb-3 text-xs text-muted">
          Tip: keep a field with key <code>email</code> (and <code>first_name</code>) so submissions map to a contact.
        </p>

        <div className="space-y-3">
          {fields.map((f, i) => (
            <div key={i} className="rounded-xl border border-deep-green/10 bg-canvas p-3">
              <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                <input
                  className="input"
                  value={f.label}
                  placeholder="Question label"
                  onChange={(e) => update(i, { label: e.target.value, key: f.key || slug(e.target.value) })}
                />
                <select className="input" value={f.type} onChange={(e) => update(i, { type: e.target.value })}>
                  {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <label className="flex items-center gap-1 px-2 text-xs text-muted">
                  <input type="checkbox" checked={f.required} onChange={(e) => update(i, { required: e.target.checked })} />
                  required
                </label>
              </div>
              <div className="mt-2 flex items-center gap-3">
                <input
                  className="input flex-1 text-xs"
                  value={f.key}
                  placeholder="key (e.g. email)"
                  onChange={(e) => update(i, { key: slug(e.target.value) })}
                />
                {f.type === "select" && (
                  <input
                    className="input flex-1 text-xs"
                    value={(f.options || []).join(", ")}
                    placeholder="options, comma separated"
                    onChange={(e) => update(i, { options: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                  />
                )}
                <button type="button" onClick={() => move(i, -1)} className="text-xs text-muted hover:text-deep-green">↑</button>
                <button type="button" onClick={() => move(i, 1)} className="text-xs text-muted hover:text-deep-green">↓</button>
                <button type="button" onClick={() => remove(i)} className="text-xs text-muted hover:text-red-600">remove</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="btn-primary">Save form</button>
        {saved && <span className="text-sm text-forest">Saved ✓</span>}
      </div>
    </form>
  );
}
