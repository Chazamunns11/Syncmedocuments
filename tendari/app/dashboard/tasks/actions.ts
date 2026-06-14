"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

export async function addTask(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const title = String(formData.get("title") || "").trim();
  const due_on = String(formData.get("due_on") || "") || null;
  if (!title) return;

  const supabase = createClient();
  await supabase.from("tasks").insert({
    account_id: account.accountId,
    title,
    due_on,
  });
  revalidatePath("/dashboard/tasks");
}

export async function toggleTask(formData: FormData) {
  const id = String(formData.get("id") || "");
  const done = String(formData.get("done") || "") === "true";
  if (!id) return;
  const supabase = createClient();
  await supabase.from("tasks").update({ done: !done }).eq("id", id);
  revalidatePath("/dashboard/tasks");
}

export async function deleteTask(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("tasks").delete().eq("id", id);
  revalidatePath("/dashboard/tasks");
}
