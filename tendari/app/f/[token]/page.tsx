import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Logo } from "@/components/logo";
import { submitForm } from "./actions";

export const dynamic = "force-dynamic";

type Field = { key: string; label: string; type: string; required?: boolean; options?: string[] };
type FormDef = { name: string; fields: Field[] };

export default async function PublicFormPage({
  params,
  searchParams,
}: {
  params: { token: string };
  searchParams: { sent?: string };
}) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    notFound();
  }
  const supabase = createClient();
  const { data } = await supabase.rpc("get_form_full", { p_token: params.token });
  if (!data) notFound();
  const form = data as FormDef;
  const fields = form.fields?.length
    ? form.fields
    : [
        { key: "first_name", label: "First name", type: "text", required: true },
        { key: "email", label: "Email", type: "email", required: true },
      ];

  const sent = searchParams.sent === "1";

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex justify-center"><Logo /></div>
        <div className="card">
          {sent ? (
            <div className="py-8 text-center">
              <h1 className="text-xl font-semibold text-deep-green">Thank you! 🌱</h1>
              <p className="mt-2 text-sm text-muted">Your details are in — we&apos;ll be in touch soon.</p>
            </div>
          ) : (
            <>
              <h1 className="text-xl font-semibold text-deep-green">{form.name}</h1>
              <form action={submitForm} className="mt-6 space-y-4">
                <input type="hidden" name="token" value={params.token} />
                {fields.map((f, i) => (
                  <div key={`${f.key}-${i}`}>
                    {f.type !== "checkbox" && <label className="label">{f.label}{f.required ? " *" : ""}</label>}
                    {f.type === "textarea" ? (
                      <textarea name={f.key} required={f.required} className="input min-h-24" />
                    ) : f.type === "select" ? (
                      <select name={f.key} required={f.required} className="input" defaultValue="">
                        <option value="" disabled>Choose…</option>
                        {(f.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : f.type === "checkbox" ? (
                      <label className="flex items-center gap-2 text-sm text-ink">
                        <input type="checkbox" name={f.key} value="yes" required={f.required} />
                        {f.label}
                      </label>
                    ) : (
                      <input
                        name={f.key}
                        type={f.type === "email" ? "email" : f.type === "number" ? "number" : f.type === "date" ? "date" : f.type === "phone" ? "tel" : "text"}
                        required={f.required}
                        className="input"
                      />
                    )}
                  </div>
                ))}
                <button className="btn-primary w-full">Send</button>
              </form>
            </>
          )}
        </div>
        <p className="mt-4 text-center text-xs text-muted">Powered by Tendari</p>
      </div>
    </main>
  );
}
