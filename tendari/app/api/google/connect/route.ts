import { NextResponse, type NextRequest } from "next/server";
import { getAccount } from "@/lib/account";
import { googleConfigured, googleAuthUrl } from "@/lib/google";

export async function GET(request: NextRequest) {
  const settings = new URL("/dashboard/settings", request.url);

  if (!googleConfigured()) {
    settings.searchParams.set("google", "notconfigured");
    return NextResponse.redirect(settings);
  }
  const account = await getAccount();
  if (!account) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  // state = account id (re-verified against the session on callback)
  return NextResponse.redirect(googleAuthUrl(account.accountId));
}
