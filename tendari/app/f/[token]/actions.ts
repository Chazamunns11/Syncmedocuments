"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function submitForm(formData: FormData) {
  const token = String(formData.get("token") || "");
  if (!token) return;

  // Build a payload object from all submitted fields (except the token).
  const payload: Record<string, string> = {};
  for (const [key, value] of formData.entries()) {
    if (key === "token") continue;
    payload[key] = String(value);
  }

  const supabase = createClient();
  await supabase.rpc("submit_form", { p_token: token, p_payload: payload });
  redirect(`/f/${token}?sent=1`);
}
