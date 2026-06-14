import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Logo } from "@/components/logo";
import { submitLead } from "./actions";

export const dynamic = "force-dynamic";

export default async function PublicFormPage({
  params,
  searchParams,
}: {
  params: { token: string };
  searchParams: { sent?: string };
}) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    notFound();
  }
  const supabase = createClient();
  const { data: name } = await supabase.rpc("get_form", { p_token: params.token });
  if (!name) notFound();

  const sent = searchParams.sent === "1";

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex justify-center">
          <Logo />
        </div>
        <div className="card">
          {sent ? (
            <div className="py-8 text-center">
              <h1 className="text-xl font-semibold text-deep-green">Thank you! 🌱</h1>
              <p className="mt-2 text-sm text-muted">Your details are in — we&apos;ll be in touch soon.</p>
            </div>
          ) : (
            <>
              <h1 className="text-xl font-semibold text-deep-green">{name as string}</h1>
              <p className="mt-1 text-sm text-muted">Pop your details in and we&apos;ll get back to you.</p>
              <form action={submitLead} className="mt-6 space-y-4">
                <input type="hidden" name="token" value={params.token} />
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">First name</label>
                    <input name="first_name" className="input" required />
                  </div>
                  <div>
                    <label className="label">Last name</label>
                    <input name="last_name" className="input" />
                  </div>
                </div>
                <div>
                  <label className="label">Email</label>
                  <input name="email" type="email" className="input" required />
                </div>
                <div>
                  <label className="label">Phone</label>
                  <input name="phone" className="input" />
                </div>
                <div>
                  <label className="label">Message</label>
                  <textarea name="message" className="input min-h-20" placeholder="What would you like help with?" />
                </div>
                <button className="btn-primary w-full">Send</button>
              </form>
            </>
          )}
        </div>
        <p className="mt-4 text-center text-xs text-muted">Powered by Tendari</p>
      </div>
    </main>
  );
}
