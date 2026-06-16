import { NextResponse, type NextRequest } from "next/server";
import { routeClient } from "@/lib/supabase/route";
import { createAdminClient, hasAdmin } from "@/lib/supabase/admin";
import { googleConfigured, exchangeCodeForTokens, GOOGLE_SCOPES } from "@/lib/google";

export async function GET(request: NextRequest) {
  const settings = new URL("/dashboard/settings", request.url);
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state"); // account id from connect

  // Keep the user's session intact across the OAuth round-trip.
  const { supabase, applyCookies } = routeClient(request);
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!code || !googleConfigured() || !hasAdmin()) {
    settings.searchParams.set("google", "error");
    return applyCookies(NextResponse.redirect(settings));
  }

  // Resolve the account: prefer the signed-in user; fall back to the state param.
  let accountId: string | null = null;
  if (user) {
    const { data } = await supabase.from("users").select("account_id").eq("id", user.id).single();
    accountId = data?.account_id ?? null;
  }
  if (!accountId && state) accountId = state;
  if (!accountId) {
    settings.searchParams.set("google", "error");
    return applyCookies(NextResponse.redirect(settings));
  }

  const tokens = await exchangeCodeForTokens(code);
  if (!tokens.access_token) {
    settings.searchParams.set("google", "error");
    return applyCookies(NextResponse.redirect(settings));
  }

  const admin = createAdminClient();
  const row: Record<string, unknown> = {
    account_id: accountId,
    provider: "google",
    access_token: tokens.access_token,
    token_expiry: new Date(Date.now() + (tokens.expires_in ?? 3600) * 1000).toISOString(),
    scope: GOOGLE_SCOPES,
    connected_at: new Date().toISOString(),
  };
  if (tokens.refresh_token) row.refresh_token = tokens.refresh_token;

  await admin.from("integrations").upsert(row, { onConflict: "account_id,provider" });

  settings.searchParams.set("google", "connected");
  return applyCookies(NextResponse.redirect(settings));
}
