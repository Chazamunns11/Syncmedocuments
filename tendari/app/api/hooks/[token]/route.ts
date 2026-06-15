import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Inbound webhook: external apps POST a lead here. The {token} is a lead-form token.
// Accepts JSON or form-encoded: first_name, last_name, email, phone, message.
export async function POST(request: NextRequest, { params }: { params: { token: string } }) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    return NextResponse.json({ ok: false, error: "not configured" }, { status: 503 });
  }

  let data: Record<string, unknown> = {};
  try {
    const ct = request.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await request.json();
    } else {
      const form = await request.formData();
      data = Object.fromEntries(form.entries());
    }
  } catch {
    return NextResponse.json({ ok: false, error: "invalid body" }, { status: 400 });
  }

  const str = (k: string) => (data[k] == null ? "" : String(data[k]));

  const supabase = createClient();
  const { data: ok, error } = await supabase.rpc("submit_lead", {
    p_token: params.token,
    p_first: str("first_name") || str("firstName") || str("name"),
    p_last: str("last_name") || str("lastName"),
    p_email: str("email"),
    p_phone: str("phone"),
    p_message: str("message"),
  });

  if (error || ok === false) {
    return NextResponse.json({ ok: false, error: error?.message || "rejected" }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
