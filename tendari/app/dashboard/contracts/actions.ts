"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { verifyContactId } from "@/lib/contact";

export async function createContract(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const title = String(formData.get("title") || "").trim();
  const body = String(formData.get("body") || "").trim();
  if (!title || !body) return;

  const supabase = createClient();
  const contact_id = await verifyContactId(supabase, String(formData.get("contact_id") || "") || null);
  await supabase.from("contracts").insert({
    account_id: account.accountId,
    contact_id,
    title,
    body,
  });
  revalidatePath("/dashboard/contracts");
}

export async function voidContract(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("contracts").update({ status: "void" }).eq("id", id);
  revalidatePath("/dashboard/contracts");
}

export async function deleteContract(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("contracts").delete().eq("id", id);
  revalidatePath("/dashboard/contracts");
}
