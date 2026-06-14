"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

export async function createDeal(formData: FormData) {
  const account = await getAccount();
  if (!account) return;

  const title = String(formData.get("title") || "").trim();
  const stage_id = String(formData.get("stage_id") || "");
  const contact_id = String(formData.get("contact_id") || "") || null;
  if (!title || !stage_id) return;

  const supabase = createClient();
  const { data: stage } = await supabase
    .from("stages")
    .select("pipeline_id")
    .eq("id", stage_id)
    .single();
  if (!stage) return;

  await supabase.from("deals").insert({
    account_id: account.accountId,
    pipeline_id: stage.pipeline_id,
    stage_id,
    contact_id,
    title,
  });

  revalidatePath("/dashboard/pipeline");
}

export async function moveDeal(formData: FormData) {
  const id = String(formData.get("id") || "");
  const stage_id = String(formData.get("stage_id") || "");
  await moveDealById(id, stage_id);
}

/** Typed variant for the drag-and-drop board (called from a Client Component). */
export async function moveDealById(id: string, stage_id: string) {
  if (!id || !stage_id) return;
  const supabase = createClient();
  await supabase
    .from("deals")
    .update({ stage_id, updated_at: new Date().toISOString() })
    .eq("id", id);
  revalidatePath("/dashboard/pipeline");
}
