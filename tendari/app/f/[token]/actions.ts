"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function submitLead(formData: FormData) {
  const token = String(formData.get("token") || "");
  if (!token) return;

  const supabase = createClient();
  await supabase.rpc("submit_lead", {
    p_token: token,
    p_first: String(formData.get("first_name") || ""),
    p_last: String(formData.get("last_name") || ""),
    p_email: String(formData.get("email") || ""),
    p_phone: String(formData.get("phone") || ""),
    p_message: String(formData.get("message") || ""),
  });

  redirect(`/f/${token}?sent=1`);
}
