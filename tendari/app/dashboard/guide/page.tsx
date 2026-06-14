import Link from "next/link";
import { LogoMark } from "@/components/logo";
import { ReplayTourButton } from "@/components/onboarding-tour";

const sections = [
  {
    title: "1. Add your contacts",
    body: "Contacts are the heart of Tendari — every client and lead you work with. Go to Contacts, fill the one-line form (a first name is enough), and they're in. No modals, no required fields you don't have yet.",
    link: { href: "/dashboard/contacts", label: "Open Contacts" },
  },
  {
    title: "2. Work your pipeline",
    body: "The Pipeline shows where everyone stands: Lead → Discovery → Proposal → Active → Renewal → Past. Add a deal, then move it along with a single dropdown. A glance tells you who needs you next.",
    link: { href: "/dashboard/pipeline", label: "Open Pipeline" },
  },
  {
    title: "3. Let follow-ups run themselves (coming soon)",
    body: "Soon you'll build simple automations — “when a lead is added, wait 2 days, then send this email”. You set it once; Tendari does the chasing so nothing slips.",
  },
  {
    title: "4. Get booked & paid (coming soon)",
    body: "Connect your calendar for a branded booking page with reminders, and take payment through your own Stripe — with no surcharge from us, ever.",
  },
];

export default function GuidePage() {
  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-deep-green">How to use Tendari</h1>
          <p className="mt-1 text-muted">Built to be obvious. Here&apos;s the whole thing in four steps.</p>
        </div>
        <ReplayTourButton className="btn-primary self-start" />
      </div>

      <div className="mt-8 space-y-4">
        {sections.map((s) => (
          <div key={s.title} className="card flex gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-mint">
              <LogoMark className="h-5 w-5 text-forest" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-deep-green">{s.title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.body}</p>
              {s.link && (
                <Link href={s.link.href} className="mt-3 inline-block text-sm font-medium text-forest">
                  {s.link.label} →
                </Link>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 card bg-mint/40">
        <h2 className="text-lg font-semibold text-deep-green">Our promise</h2>
        <p className="mt-1.5 text-sm text-muted">
          No bill shock. You own your data and your payments. If something here ever feels complicated,
          that&apos;s a bug — tell us.
        </p>
      </div>
    </div>
  );
}
