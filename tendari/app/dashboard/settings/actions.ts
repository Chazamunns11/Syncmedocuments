"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

export async function updateAccount(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const name = String(formData.get("name") || "").trim();
  const timezone = String(formData.get("timezone") || "").trim();
  if (!name) return;

  const patch: { name: string; timezone?: string } = { name };
  if (timezone) patch.timezone = timezone;

  const supabase = createClient();
  await supabase.from("accounts").update(patch).eq("id", account.accountId);
  revalidatePath("/dashboard/settings");
  revalidatePath("/dashboard");
}
