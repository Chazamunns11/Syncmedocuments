import { NextResponse, type NextRequest } from "next/server";
import { getAccount } from "@/lib/account";
import { createAdminClient, hasAdmin } from "@/lib/supabase/admin";
import { googleConfigured, exchangeCodeForTokens, GOOGLE_SCOPES } from "@/lib/google";

export async function GET(request: NextRequest) {
  const settings = new URL("/dashboard/settings", request.url);
  const code = request.nextUrl.searchParams.get("code");

  const account = await getAccount();
  if (!account) return NextResponse.redirect(new URL("/login", request.url));

  if (!code || !googleConfigured() || !hasAdmin()) {
    settings.searchParams.set("google", "error");
    return NextResponse.redirect(settings);
  }

  const tokens = await exchangeCodeForTokens(code);
  if (!tokens.access_token) {
    settings.searchParams.set("google", "error");
    return NextResponse.redirect(settings);
  }

  const admin = createAdminClient();
  const row: Record<string, unknown> = {
    account_id: account.accountId,
    provider: "google",
    access_token: tokens.access_token,
    token_expiry: new Date(Date.now() + (tokens.expires_in ?? 3600) * 1000).toISOString(),
    scope: GOOGLE_SCOPES,
    connected_at: new Date().toISOString(),
  };
  // refresh_token is only returned on first consent — don't overwrite with null.
  if (tokens.refresh_token) row.refresh_token = tokens.refresh_token;

  await admin.from("integrations").upsert(row, { onConflict: "account_id,provider" });

  settings.searchParams.set("google", "connected");
  return NextResponse.redirect(settings);
}
