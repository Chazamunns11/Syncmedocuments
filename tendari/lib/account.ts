import { createClient } from "@/lib/supabase/server";

export type AccountInfo = {
  userId: string;
  accountId: string;
  userName: string | null;
  businessName: string | null;
  plan: string | null;
  timezone: string;
};

/** Returns the signed-in user's account context, or null if not signed in / not provisioned. */
export async function getAccount(): Promise<AccountInfo | null> {
  // Not configured yet (e.g. before Supabase keys are set) — fail soft.
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    return null;
  }

  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data } = await supabase
    .from("users")
    .select("account_id, name, accounts(name, plan, timezone)")
    .eq("id", user.id)
    .single();

  if (!data) return null;
  const account = Array.isArray(data.accounts) ? data.accounts[0] : data.accounts;

  return {
    userId: user.id,
    accountId: data.account_id,
    userName: data.name ?? null,
    businessName: account?.name ?? null,
    plan: account?.plan ?? null,
    timezone: account?.timezone ?? "UTC",
  };
}
