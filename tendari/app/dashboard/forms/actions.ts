"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

export async function createForm(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const name = String(formData.get("name") || "").trim();
  if (!name) return;

  const supabase = createClient();
  await supabase.from("forms").insert({ account_id: account.accountId, name });
  revalidatePath("/dashboard/forms");
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
