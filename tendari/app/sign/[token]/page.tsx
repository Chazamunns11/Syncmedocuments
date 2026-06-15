import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Logo } from "@/components/logo";
import { signContract } from "./actions";

export const dynamic = "force-dynamic";

type Contract = { title: string; body: string; status: string; signed_name: string | null };

export default async function SignPage({
  params,
  searchParams,
}: {
  params: { token: string };
  searchParams: { signed?: string; error?: string };
}) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    notFound();
  }
  const supabase = createClient();
  const { data } = await supabase.rpc("get_contract", { p_token: params.token });
  if (!data) notFound();
  const c = data as Contract;

  const justSigned = searchParams.signed === "1";
  const alreadySigned = c.status === "signed";
  const voided = c.status === "void";

  return (
    <main className="flex min-h-screen items-start justify-center px-6 py-10">
      <div className="w-full max-w-2xl">
        <div className="mb-6 flex justify-center"><Logo /></div>
        <div className="card">
          <h1 className="text-xl font-semibold text-deep-green">{c.title}</h1>

          <div className="mt-4 max-h-[50vh] overflow-y-auto whitespace-pre-wrap rounded-xl bg-canvas p-4 text-sm text-ink">
            {c.body}
          </div>

          {voided ? (
            <p className="mt-6 rounded-lg bg-deep-green/10 px-3 py-2 text-sm text-muted">This contract is no longer active.</p>
          ) : justSigned || alreadySigned ? (
            <div className="mt-6 rounded-lg bg-mint/60 px-4 py-4 text-center">
              <p className="font-semibold text-deep-green">Signed ✓</p>
              <p className="mt-1 text-sm text-muted">
                Thank you{c.signed_name ? `, ${c.signed_name}` : ""}. A copy has been recorded.
              </p>
            </div>
          ) : (
            <form action={signContract} className="mt-6">
              <input type="hidden" name="token" value={params.token} />
              <label className="label">Type your full name to sign</label>
              <input name="name" className="input" required placeholder="Your full name" />
              {searchParams.error === "1" && (
                <p className="mt-2 text-sm text-red-600">Couldn&apos;t sign — the link may have expired.</p>
              )}
              <p className="mt-2 text-xs text-muted">By typing your name and clicking below, you agree to the terms above.</p>
              <button className="btn-primary mt-4 w-full">Agree &amp; sign</button>
            </form>
          )}
        </div>
        <p className="mt-4 text-center text-xs text-muted">Powered by Tendari</p>
      </div>
    </main>
  );
}
