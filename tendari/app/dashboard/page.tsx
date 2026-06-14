import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { getAccount } from "@/lib/account";
import { ReplayTourButton } from "@/components/onboarding-tour";

export default async function DashboardHome() {
  const account = await getAccount();
  const supabase = createClient();

  const [{ count: contacts }, { count: openDeals }, { count: openTasks }] = await Promise.all([
    supabase.from("contacts").select("*", { count: "exact", head: true }),
    supabase
      .from("deals")
      .select("*", { count: "exact", head: true })
      .eq("status", "open"),
    supabase
      .from("tasks")
      .select("*", { count: "exact", head: true })
      .eq("done", false),
  ]);

  const stats = [
    { label: "Contacts", value: contacts ?? 0, href: "/dashboard/contacts" },
    { label: "Open deals", value: openDeals ?? 0, href: "/dashboard/pipeline" },
    { label: "Follow-ups", value: openTasks ?? 0, href: "/dashboard/tasks" },
  ];

  const checklist = [
    { done: true, label: "Create your account", href: "/dashboard" },
    { done: (contacts ?? 0) > 0, label: "Add your first contact", href: "/dashboard/contacts" },
    { done: (openDeals ?? 0) > 0, label: "Add a deal to your pipeline", href: "/dashboard/pipeline" },
  ];
  const completed = checklist.filter((c) => c.done).length;
  const pct = Math.round((completed / checklist.length) * 100);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">
        Welcome{account?.userName ? `, ${account.userName.split(" ")[0]}` : ""} 👋
      </h1>
      <p className="mt-1 text-muted">Here&apos;s your coaching practice at a glance.</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {stats.map((s) => (
          <Link key={s.label} href={s.href} className="card transition hover:shadow-md">
            <p className="text-sm text-muted">{s.label}</p>
            <p className="mt-2 text-3xl font-semibold text-deep-green">{s.value}</p>
          </Link>
        ))}
      </div>

      {/* Getting-started checklist */}
      <div className="mt-8 card">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-deep-green">Get started</h2>
          <span className="text-sm text-muted">{completed}/{checklist.length} done</span>
        </div>

        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-mint">
          <div className="h-full rounded-full bg-forest transition-all" style={{ width: `${pct}%` }} />
        </div>

        <ul className="mt-5 space-y-2.5">
          {checklist.map((c) => (
            <li key={c.label}>
              <Link href={c.href} className="flex items-center gap-3 rounded-lg p-2 hover:bg-mint/40">
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                    c.done ? "bg-forest text-white" : "border border-deep-green/20 text-transparent"
                  }`}
                >
                  ✓
                </span>
                <span className={`text-sm ${c.done ? "text-muted line-through" : "text-ink"}`}>{c.label}</span>
              </Link>
            </li>
          ))}
        </ul>

        <div className="mt-5 flex flex-wrap gap-3">
          <ReplayTourButton className="btn-primary" label="Take the tour" />
          <Link href="/dashboard/guide" className="btn-ghost">How to use Tendari</Link>
        </div>
      </div>
    </div>
  );
}
