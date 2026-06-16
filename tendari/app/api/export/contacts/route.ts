import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

function csvCell(v: unknown): string {
  const s = v == null ? "" : String(v);
  return `"${s.replace(/"/g, '""')}"`;
}

export async function GET() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  // RLS scopes this to the caller's account.
  const { data } = await supabase
    .from("contacts")
    .select("first_name, last_name, email, phone, source, created_at")
    .order("created_at", { ascending: false });

  const rows = data || [];
  const header = ["First name", "Last name", "Email", "Phone", "Source", "Created"];
  const lines = [header.map(csvCell).join(",")];
  for (const r of rows) {
    lines.push(
      [r.first_name, r.last_name, r.email, r.phone, r.source, r.created_at].map(csvCell).join(","),
    );
  }
  const csv = lines.join("\r\n");

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="tendari-contacts.csv"`,
    },
  });
}
