"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { verifyContactId } from "@/lib/contact";

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

export async function importContacts(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const raw = String(formData.get("csv") || "").trim();
  if (!raw) return;

  // Parse simple CSV: columns first_name, last_name, email, phone (header optional).
  const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length === 0) return;
  const first = lines[0].toLowerCase();
  const hasHeader = first.includes("email") || first.includes("first") || first.includes("name");
  const rows = (hasHeader ? lines.slice(1) : lines).map((line) => {
    const [first_name = "", last_name = "", email = "", phone = ""] = line
      .split(",")
      .map((c) => c.trim());
    return {
      first_name,
      last_name,
      email: email || null,
      phone: phone || null,
    };
  }).filter((r) => r.first_name || r.email);

  if (rows.length === 0) return;

  const supabase = createClient();

  // Skip emails that already exist in this account (the unique index would
  // otherwise fail the whole batch).
  const { data: existing } = await supabase.from("contacts").select("email");
  const seen = new Set(
    (existing || []).map((e: { email: string | null }) => (e.email || "").toLowerCase()).filter(Boolean),
  );

  const toInsert = rows
    .filter((r) => !r.email || !seen.has(r.email.toLowerCase()))
    .map((r) => ({ ...r, account_id: account.accountId, source: "import" }));

  if (toInsert.length > 0) {
    await supabase.from("contacts").insert(toInsert);
  }
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
  const rawContactId = String(formData.get("contact_id") || "");
  const body = String(formData.get("body") || "").trim();
  if (!rawContactId || !body) return;

  const supabase = createClient();
  const contact_id = await verifyContactId(supabase, rawContactId);
  if (!contact_id) return;

  await supabase.from("activities").insert({
    account_id: account.accountId,
    contact_id,
    type: "note",
    body,
  });
  revalidatePath(`/dashboard/contacts/${contact_id}`);
}
