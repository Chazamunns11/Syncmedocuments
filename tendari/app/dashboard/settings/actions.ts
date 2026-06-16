"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { createAdminClient, hasAdmin } from "@/lib/supabase/admin";

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

export async function disconnectGoogle() {
  const account = await getAccount();
  if (!account || !hasAdmin()) return;
  const admin = createAdminClient();
  await admin.from("integrations").delete().eq("account_id", account.accountId).eq("provider", "google");
  revalidatePath("/dashboard/settings");
}
