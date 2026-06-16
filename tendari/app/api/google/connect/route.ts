import { NextResponse, type NextRequest } from "next/server";
import { routeClient } from "@/lib/supabase/route";
import { googleConfigured, googleAuthUrl } from "@/lib/google";

export async function GET(request: NextRequest) {
  const settings = new URL("/dashboard/settings", request.url);

  if (!googleConfigured()) {
    settings.searchParams.set("google", "notconfigured");
    return NextResponse.redirect(settings);
  }

  const { supabase, applyCookies } = routeClient(request);
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return applyCookies(NextResponse.redirect(new URL("/login", request.url)));
  }

  const { data } = await supabase.from("users").select("account_id").eq("id", user.id).single();
  if (!data?.account_id) {
    return applyCookies(NextResponse.redirect(new URL("/login", request.url)));
  }

  // state = account id (used as a fallback in the callback)
  return applyCookies(NextResponse.redirect(googleAuthUrl(data.account_id)));
}
