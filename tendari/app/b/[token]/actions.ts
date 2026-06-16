"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient, hasAdmin } from "@/lib/supabase/admin";
import { googleConfigured, refreshAccessToken, createCalendarEvent } from "@/lib/google";

export async function submitBooking(formData: FormData) {
  const token = String(formData.get("token") || "");
  const start = String(formData.get("start") || "");
  const first = String(formData.get("first_name") || "");
  const last = String(formData.get("last_name") || "");
  const email = String(formData.get("email") || "");
  if (!token || !start) return;

  const supabase = createClient();
  const { data: ok } = await supabase.rpc("submit_booking", {
    p_token: token,
    p_start: start,
    p_first: first,
    p_last: last,
    p_email: email,
    p_phone: String(formData.get("phone") || ""),
  });

  if (ok === false) {
    // Slot was taken or invalid — send them back to pick again.
    redirect(`/b/${token}?taken=1`);
  }

  // Best-effort: mirror the booking to the coach's Google Calendar if connected.
  await pushToGoogleCalendar(token, start, `${first} ${last}`.trim(), email);

  redirect(`/b/${token}?booked=1`);
}

async function pushToGoogleCalendar(token: string, startISO: string, who: string, email: string) {
  if (!hasAdmin() || !googleConfigured()) return;
  try {
    const admin = createAdminClient();
    const { data: mt } = await admin
      .from("meeting_types")
      .select("account_id, name, duration_min")
      .eq("token", token)
      .single();
    if (!mt) return;

    const { data: intg } = await admin
      .from("integrations")
      .select("access_token, refresh_token, token_expiry")
      .eq("account_id", mt.account_id)
      .eq("provider", "google")
      .single();
    if (!intg) return;

    let access = intg.access_token as string | null;
    const expired = !intg.token_expiry || new Date(intg.token_expiry).getTime() < Date.now() + 60_000;
    if (expired && intg.refresh_token) {
      const refreshed = await refreshAccessToken(intg.refresh_token as string);
      if (refreshed.access_token) {
        access = refreshed.access_token;
        await admin
          .from("integrations")
          .update({
            access_token: refreshed.access_token,
            token_expiry: new Date(Date.now() + (refreshed.expires_in ?? 3600) * 1000).toISOString(),
          })
          .eq("account_id", mt.account_id)
          .eq("provider", "google");
      }
    }
    if (!access) return;

    const endISO = new Date(new Date(startISO).getTime() + mt.duration_min * 60_000).toISOString();
    await createCalendarEvent(access, {
      summary: `${mt.name}${who ? ` — ${who}` : ""}`,
      description: "Booked via Tendari",
      startISO,
      endISO,
      attendeeEmail: email || undefined,
    });
  } catch {
    // never block the booking on a calendar hiccup
  }
}
