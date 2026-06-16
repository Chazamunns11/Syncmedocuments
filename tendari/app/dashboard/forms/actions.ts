"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

const DEFAULT_FIELDS = [
  { key: "first_name", label: "First name", type: "text", required: true },
  { key: "last_name", label: "Last name", type: "text", required: false },
  { key: "email", label: "Email", type: "email", required: true },
  { key: "phone", label: "Phone", type: "phone", required: false },
  { key: "message", label: "How can I help?", type: "textarea", required: false },
];

export async function createForm(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const name = String(formData.get("name") || "").trim();
  if (!name) return;

  const supabase = createClient();
  const { data } = await supabase
    .from("forms")
    .insert({ account_id: account.accountId, name, fields: DEFAULT_FIELDS })
    .select("id")
    .single();
  revalidatePath("/dashboard/forms");
  if (data?.id) redirect(`/dashboard/forms/${data.id}`);
}

export async function updateForm(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const name = String(formData.get("name") || "").trim();
  let fields: unknown = [];
  try {
    fields = JSON.parse(String(formData.get("fields") || "[]"));
  } catch {
    fields = [];
  }
  const supabase = createClient();
  const patch: Record<string, unknown> = { fields };
  if (name) patch.name = name;
  await supabase.from("forms").update(patch).eq("id", id);
  revalidatePath("/dashboard/forms");
  revalidatePath(`/dashboard/forms/${id}`);
}

export async function toggleForm(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  const { data: row } = await supabase.from("forms").select("active").eq("id", id).single();
  if (!row) return;
  await supabase.from("forms").update({ active: !row.active }).eq("id", id);
  revalidatePath("/dashboard/forms");
}

export async function deleteForm(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("forms").delete().eq("id", id);
  revalidatePath("/dashboard/forms");
}
