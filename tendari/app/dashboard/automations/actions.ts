"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { TEMPLATES } from "@/lib/automation-templates";

export async function addWorkflowFromTemplate(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const key = String(formData.get("template") || "");
  const t = TEMPLATES[key];
  if (!t) return;

  const supabase = createClient();
  await supabase.from("workflows").insert({
    account_id: account.accountId,
    name: t.name,
    trigger_type: t.trigger_type,
    steps: t.steps,
  });
  revalidatePath("/dashboard/automations");
}

export async function toggleWorkflow(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  const { data: row } = await supabase.from("workflows").select("active").eq("id", id).single();
  if (!row) return;
  await supabase.from("workflows").update({ active: !row.active }).eq("id", id);
  revalidatePath("/dashboard/automations");
}

export async function deleteWorkflow(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("workflows").delete().eq("id", id);
  revalidatePath("/dashboard/automations");
}
