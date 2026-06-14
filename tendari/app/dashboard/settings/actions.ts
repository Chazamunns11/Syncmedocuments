"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

export async function updateBusinessName(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const name = String(formData.get("name") || "").trim();
  if (!name) return;

  const supabase = createClient();
  await supabase.from("accounts").update({ name }).eq("id", account.accountId);
  revalidatePath("/dashboard/settings");
  revalidatePath("/dashboard");
}
