import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { FormBuilder } from "@/components/form-builder";

type Field = { key: string; label: string; type: string; required: boolean; options?: string[] };
type Form = { id: string; name: string; token: string; active: boolean; fields: Field[] };

export default async function FormEditorPage({ params }: { params: { id: string } }) {
  const supabase = createClient();
  const { data } = await supabase
    .from("forms")
    .select("id, name, token, active, fields")
    .eq("id", params.id)
    .single();
  if (!data) notFound();
  const form = data as Form;
  const base = process.env.NEXT_PUBLIC_SITE_URL || "";

  return (
    <div>
      <Link href="/dashboard/forms" className="text-sm text-muted hover:text-deep-green">← Back to forms</Link>
      <h1 className="mt-3 text-2xl font-semibold text-deep-green">Edit form</h1>
      <div className="mt-2 space-y-0.5 text-sm">
        <p className="text-muted">
          Public link:{" "}
          <a href={`${base}/f/${form.token}`} target="_blank" className="text-forest hover:underline">
            {base ? `${base}/f/${form.token}` : `/f/${form.token}`}
          </a>
        </p>
        <p className="text-xs text-muted">Webhook (POST JSON): <code>{base ? `${base}/api/hooks/${form.token}` : `/api/hooks/${form.token}`}</code></p>
      </div>

      <div className="mt-6">
        <FormBuilder id={form.id} initialName={form.name} initialFields={form.fields || []} />
      </div>
    </div>
  );
}
