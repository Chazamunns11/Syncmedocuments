"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

export async function addContact(formData: FormData) {
  const account = await getAccount();
  if (!account) return;

  const first_name = String(formData.get("first_name") || "").trim();
  const last_name = String(formData.get("last_name") || "").trim();
  const email = String(formData.get("email") || "").trim() || null;
  const phone = String(formData.get("phone") || "").trim() || null;
  if (!first_name && !email) return;

  const supabase = createClient();
  await supabase.from("contacts").insert({
    account_id: account.accountId,
    first_name,
    last_name,
    email,
    phone,
    source: "manual",
  });

  revalidatePath("/dashboard/contacts");
}

export async function deleteContact(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("contacts").delete().eq("id", id);
  revalidatePath("/dashboard/contacts");
}

export async function updateContact(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase
    .from("contacts")
    .update({
      first_name: String(formData.get("first_name") || "").trim(),
      last_name: String(formData.get("last_name") || "").trim(),
      email: String(formData.get("email") || "").trim() || null,
      phone: String(formData.get("phone") || "").trim() || null,
      notes: String(formData.get("notes") || "").trim() || null,
      updated_at: new Date().toISOString(),
    })
    .eq("id", id);
  revalidatePath(`/dashboard/contacts/${id}`);
  revalidatePath("/dashboard/contacts");
}

export async function addNote(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const contact_id = String(formData.get("contact_id") || "");
  const body = String(formData.get("body") || "").trim();
  if (!contact_id || !body) return;

  const supabase = createClient();
  await supabase.from("activities").insert({
    account_id: account.accountId,
    contact_id,
    type: "note",
    body,
  });
  revalidatePath(`/dashboard/contacts/${contact_id}`);
}
