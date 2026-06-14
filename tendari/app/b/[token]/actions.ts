"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function submitBooking(formData: FormData) {
  const token = String(formData.get("token") || "");
  const start = String(formData.get("start") || "");
  if (!token || !start) return;

  const supabase = createClient();
  const { data: ok } = await supabase.rpc("submit_booking", {
    p_token: token,
    p_start: start,
    p_first: String(formData.get("first_name") || ""),
    p_last: String(formData.get("last_name") || ""),
    p_email: String(formData.get("email") || ""),
    p_phone: String(formData.get("phone") || ""),
  });

  if (ok === false) {
    // Slot was taken or invalid — send them back to pick again.
    redirect(`/b/${token}?taken=1`);
  }
  redirect(`/b/${token}?booked=1`);
}
