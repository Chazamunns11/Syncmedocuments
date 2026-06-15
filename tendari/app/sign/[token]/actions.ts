"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function signContract(formData: FormData) {
  const token = String(formData.get("token") || "");
  const name = String(formData.get("name") || "").trim();
  if (!token || !name) return;

  const supabase = createClient();
  const { data: ok } = await supabase.rpc("sign_contract", { p_token: token, p_name: name });
  if (ok === false) {
    redirect(`/sign/${token}?error=1`);
  }
  redirect(`/sign/${token}?signed=1`);
}
