"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

export async function markAllRead() {
  const supabase = createClient();
  await supabase.from("notifications").update({ read: true }).eq("read", false);
  revalidatePath("/dashboard/notifications");
  revalidatePath("/dashboard");
}

export async function markRead(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("notifications").update({ read: true }).eq("id", id);
  revalidatePath("/dashboard/notifications");
  revalidatePath("/dashboard");
}

export async function deleteNotification(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("notifications").delete().eq("id", id);
  revalidatePath("/dashboard/notifications");
  revalidatePath("/dashboard");
}
