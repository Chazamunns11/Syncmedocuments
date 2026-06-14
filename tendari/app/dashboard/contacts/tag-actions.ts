"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { verifyContactId } from "@/lib/contact";

export async function addTagByName(formData: FormData) {
  const account = await getAccount();
  if (!account) return;

  const supabase = createClient();
  const contact_id = await verifyContactId(supabase, String(formData.get("contact_id") || "") || null);
  const name = String(formData.get("name") || "").trim();
  if (!contact_id || !name) return;

  // Find existing tag (case-insensitive) or create it.
  const { data: existing } = await supabase
    .from("tags")
    .select("id")
    .ilike("name", name)
    .maybeSingle();

  let tagId = existing?.id as string | undefined;
  if (!tagId) {
    const { data: created } = await supabase
      .from("tags")
      .insert({ account_id: account.accountId, name })
      .select("id")
      .single();
    tagId = created?.id;
  }
  if (!tagId) return;

  await supabase
    .from("contact_tags")
    .upsert(
      { account_id: account.accountId, contact_id, tag_id: tagId },
      { onConflict: "contact_id,tag_id", ignoreDuplicates: true },
    );

  revalidatePath(`/dashboard/contacts/${contact_id}`);
  revalidatePath("/dashboard/contacts");
}

export async function removeContactTag(formData: FormData) {
  const contact_id = String(formData.get("contact_id") || "");
  const tag_id = String(formData.get("tag_id") || "");
  if (!contact_id || !tag_id) return;

  const supabase = createClient();
  await supabase
    .from("contact_tags")
    .delete()
    .eq("contact_id", contact_id)
    .eq("tag_id", tag_id);

  revalidatePath(`/dashboard/contacts/${contact_id}`);
  revalidatePath("/dashboard/contacts");
}
