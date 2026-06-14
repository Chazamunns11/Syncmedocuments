"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { verifyContactId } from "@/lib/contact";

export async function createDeal(formData: FormData) {
  const account = await getAccount();
  if (!account) return;

  const title = String(formData.get("title") || "").trim();
  const stage_id = String(formData.get("stage_id") || "");
  if (!title || !stage_id) return;

  const supabase = createClient();
  const { data: stage } = await supabase
    .from("stages")
    .select("pipeline_id")
    .eq("id", stage_id)
    .single();
  if (!stage) return;

  const contact_id = await verifyContactId(supabase, String(formData.get("contact_id") || "") || null);

  await supabase.from("deals").insert({
    account_id: account.accountId,
    pipeline_id: stage.pipeline_id,
    stage_id,
    contact_id,
    title,
  });

  revalidatePath("/dashboard/pipeline");
}

/** Move a deal to another stage. Called from the drag-and-drop board (Client Component). */
export async function moveDealById(id: string, stage_id: string) {
  if (!id || !stage_id) return;
  const supabase = createClient();

  // Verify the target stage is in the caller's account (RLS-scoped select):
  // prevents pointing a deal at another tenant's stage.
  const { data: stage } = await supabase
    .from("stages")
    .select("id")
    .eq("id", stage_id)
    .single();
  if (!stage) return;

  await supabase
    .from("deals")
    .update({ stage_id, updated_at: new Date().toISOString() })
    .eq("id", id);
  revalidatePath("/dashboard/pipeline");
}
