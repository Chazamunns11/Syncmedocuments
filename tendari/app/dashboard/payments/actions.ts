"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { verifyContactId } from "@/lib/contact";
import { parseMoneyToCents } from "@/lib/format";

export async function addPayment(formData: FormData) {
  const account = await getAccount();
  if (!account) return;

  const amount_cents = parseMoneyToCents(String(formData.get("amount") || ""));
  if (amount_cents <= 0) return;
  const note = String(formData.get("note") || "").trim() || null;
  const method = String(formData.get("method") || "").trim() || null;
  const paid_on = String(formData.get("paid_on") || "") || undefined;

  const supabase = createClient();
  const contact_id = await verifyContactId(supabase, String(formData.get("contact_id") || "") || null);

  const { data: row } = await supabase
    .from("payments")
    .insert({ account_id: account.accountId, contact_id, amount_cents, note, method, paid_on })
    .select("id")
    .single();

  if (contact_id && row) {
    await supabase.from("activities").insert({
      account_id: account.accountId,
      contact_id,
      type: "payment",
      title: "Payment received",
      body: note,
    });
  }
  revalidatePath("/dashboard/payments");
  if (contact_id) revalidatePath(`/dashboard/contacts/${contact_id}`);
}

export async function deletePayment(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("payments").delete().eq("id", id);
  revalidatePath("/dashboard/payments");
}
