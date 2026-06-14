"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Logo } from "@/components/logo";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [business, setBusiness] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const supabase = createClient();
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { name, business_name: business },
        emailRedirectTo:
          (process.env.NEXT_PUBLIC_SITE_URL || "") + "/dashboard",
      },
    });
    setLoading(false);
    if (error) return setError(error.message);
    if (data.session) {
      router.push("/dashboard");
      router.refresh();
    } else {
      setInfo("Check your email to confirm your account, then log in.");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Link href="/"><Logo /></Link>
        </div>
        <div className="card">
          <h1 className="text-xl font-semibold text-deep-green">Start your free trial</h1>
          <p className="mt-1 text-sm text-muted">14 days. No surcharge on your payments. Cancel anytime.</p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="label">Your name</label>
              <input className="input" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label className="label">Business name</label>
              <input className="input" placeholder="e.g. Clarity Coaching" value={business} onChange={(e) => setBusiness(e.target.value)} />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {info && <p className="text-sm text-forest">{info}</p>}
            <button className="btn-primary w-full" disabled={loading}>
              {loading ? "Creating…" : "Create account"}
            </button>
          </form>
        </div>
        <p className="mt-4 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-forest">Log in</Link>
        </p>
      </div>
    </main>
  );
}
