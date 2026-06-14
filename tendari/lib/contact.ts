import type { SupabaseClient } from "@supabase/supabase-js";

type NameParts = {
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
};

/** Display name for a contact, with a sensible fallback. */
export function contactName(c: NameParts, fallback = "Unnamed contact"): string {
  return [c.first_name, c.last_name].filter(Boolean).join(" ") || c.email || fallback;
}

/** Single-character avatar initial for a contact. */
export function contactInitial(c: NameParts): string {
  return (c.first_name?.[0] || c.email?.[0] || "?").toUpperCase();
}

/**
 * Returns the id only if the contact exists in the caller's account
 * (the select is RLS-scoped), otherwise null. Prevents storing rows that
 * reference another tenant's contact.
 */
export async function verifyContactId(
  supabase: SupabaseClient,
  id: string | null,
): Promise<string | null> {
  if (!id) return null;
  const { data } = await supabase.from("contacts").select("id").eq("id", id).single();
  return data ? id : null;
}
