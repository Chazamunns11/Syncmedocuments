"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";

function toMinutes(hhmm: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm.trim());
  if (!m) return null;
  const min = Number(m[1]) * 60 + Number(m[2]);
  return min >= 0 && min <= 1440 ? min : null;
}

export async function createMeetingType(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const name = String(formData.get("name") || "").trim();
  const duration_min = Math.max(5, Math.min(480, Number(formData.get("duration") || 30) || 30));
  if (!name) return;

  const supabase = createClient();
  await supabase.from("meeting_types").insert({ account_id: account.accountId, name, duration_min });
  revalidatePath("/dashboard/booking");
}

export async function deleteMeetingType(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("meeting_types").delete().eq("id", id);
  revalidatePath("/dashboard/booking");
}

export async function addAvailability(formData: FormData) {
  const account = await getAccount();
  if (!account) return;
  const weekday = Number(formData.get("weekday"));
  const start_min = toMinutes(String(formData.get("start") || ""));
  const end_min = toMinutes(String(formData.get("end") || ""));
  if (!(weekday >= 0 && weekday <= 6) || start_min === null || end_min === null || end_min <= start_min) {
    return;
  }

  const supabase = createClient();
  await supabase
    .from("availability_rules")
    .insert({ account_id: account.accountId, weekday, start_min, end_min });
  revalidatePath("/dashboard/booking");
}

export async function deleteAvailability(formData: FormData) {
  const id = String(formData.get("id") || "");
  if (!id) return;
  const supabase = createClient();
  await supabase.from("availability_rules").delete().eq("id", id);
  revalidatePath("/dashboard/booking");
}
