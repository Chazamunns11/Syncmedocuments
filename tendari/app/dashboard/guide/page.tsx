import Link from "next/link";
import { LogoMark } from "@/components/logo";
import { ReplayTourButton } from "@/components/onboarding-tour";

const sections = [
  {
    title: "1. Add your contacts",
    body: "Contacts are the heart of Tendari — every client and lead. Add them one at a time (a first name is enough), import a CSV from your old tool, or let them come in through a lead form. Organise with tags and search any time.",
    link: { href: "/dashboard/contacts", label: "Open Contacts" },
  },
  {
    title: "2. Work your pipeline",
    body: "The Pipeline shows where everyone stands: Lead → Discovery → Proposal → Active → Renewal → Past. Drag a card between columns, set a deal value, and mark deals Won or Lost. The header totals your open pipeline.",
    link: { href: "/dashboard/pipeline", label: "Open Pipeline" },
  },
  {
    title: "3. Get booked",
    body: "Set your weekly availability and create a meeting type, then share your /b/ link. Clients pick a slot themselves and instantly become a contact with a booking on their timeline.",
    link: { href: "/dashboard/booking", label: "Set up Booking" },
  },
  {
    title: "4. Capture leads",
    body: "Create a lead form and share its link. Every submission lands as a contact automatically — no copy-paste, no missed enquiries.",
    link: { href: "/dashboard/forms", label: "Create a form" },
  },
  {
    title: "5. Stay on top with follow-ups",
    body: "Add follow-ups with due dates so nothing slips. Automated follow-up sequences (and payments) are on the way — your manual list becomes automatic.",
    link: { href: "/dashboard/tasks", label: "Open Follow-ups" },
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
