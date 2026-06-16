import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

type CookieToSet = { name: string; value: string; options: CookieOptions };

/**
 * Supabase client for Route Handlers that REDIRECT. Any auth cookies the client
 * wants to set are buffered and must be copied onto the response you return via
 * `applyCookies(res)` — otherwise a refreshed session is lost and the user is
 * logged out (the classic OAuth-callback logout bug).
 */
export function routeClient(request: NextRequest) {
  const jar: CookieToSet[] = [];
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          jar.push(...cookiesToSet);
        },
      },
    },
  );

  function applyCookies(res: NextResponse) {
    for (const c of jar) res.cookies.set(c.name, c.value, c.options);
    return res;
  }

  return { supabase, applyCookies };
}
