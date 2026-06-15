import Link from "next/link";
import { redirect } from "next/navigation";
import { Logo } from "@/components/logo";
import { DashboardNav } from "@/components/dashboard-nav";
import { OnboardingTour } from "@/components/onboarding-tour";
import { getAccount } from "@/lib/account";
import { createClient } from "@/lib/supabase/server";

// The dashboard is always per-user; never statically cache it.
export const dynamic = "force-dynamic";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const account = await getAccount();
  if (!account) redirect("/login");

  const supabase = createClient();
  const { count: unread } = await supabase
    .from("notifications")
    .select("*", { count: "exact", head: true })
    .eq("read", false);

  return (
    <div className="min-h-screen lg:flex">
      {/* Sidebar */}
      <aside className="border-b border-deep-green/10 bg-white lg:w-64 lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between px-5 py-5 lg:block">
          <Link href="/dashboard"><Logo /></Link>
          <div className="mt-1 hidden text-xs text-muted lg:block">
            {account.businessName || "Your workspace"}
          </div>
          {unread ? (
            <Link
              href="/dashboard/notifications"
              className="ml-auto inline-flex items-center gap-1 rounded-full bg-forest px-2.5 py-1 text-xs font-semibold text-white lg:ml-0 lg:mt-2"
            >
              {unread} new
            </Link>
          ) : null}
        </div>
        <div className="hidden px-3 lg:block">
          <DashboardNav />
        </div>
        <div className="hidden px-5 py-5 lg:block">
          <div className="rounded-xl bg-mint/60 p-3 text-xs text-deep-green">
            Plan: <span className="font-semibold capitalize">{account.plan || "trial"}</span>
          </div>
          <form action="/auth/signout" method="post" className="mt-3">
            <button className="text-xs font-medium text-muted hover:text-deep-green">Sign out</button>
          </form>
        </div>
      </aside>

      {/* Mobile nav */}
      <div className="border-b border-deep-green/10 bg-white px-4 py-3 lg:hidden">
        <DashboardNav />
      </div>

      {/* Content */}
      <main className="flex-1 px-5 py-8 sm:px-8">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>

      {/* First-run guided walkthrough */}
      <OnboardingTour />
    </div>
  );
}
