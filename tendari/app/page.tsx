import Link from "next/link";
import { Logo, LogoMark } from "@/components/logo";

const features = [
  {
    title: "Contacts & pipeline",
    body: "A clean visual board of every client — Lead → Discovery → Active → Renewal. See where everyone stands at a glance.",
  },
  {
    title: "Booking that syncs",
    body: "A branded booking page wired to your calendar, with automatic reminders so no-shows stop costing you money.",
  },
  {
    title: "Payments, no surcharge",
    body: "Get paid through your own Stripe. We never take a cut of your client payments — unlike the course platforms.",
  },
  {
    title: "Follow-ups on autopilot",
    body: "“Wait 3 days, then email.” Build simple automations that nurture leads and onboard clients while you coach.",
  },
  {
    title: "Forms & contracts",
    body: "Intake forms and e-signed agreements that drop straight onto the client's timeline.",
  },
  {
    title: "No bill shock",
    body: "Generous email/SMS allowances, at-cost overage, and hard spend caps. Always know what you'll pay.",
  },
];

const tiers = [
  {
    name: "Solo",
    price: "$29",
    tagline: "New & bootstrapped coaches",
    points: ["CRM + pipeline", "Booking & reminders", "Payments (no surcharge)", "Email automation", "1,000 contacts"],
    featured: false,
  },
  {
    name: "Pro",
    price: "$69",
    tagline: "Working coaches",
    points: ["Everything in Solo", "SMS + full automations", "Unlimited contacts", "More email + AI credits", "Webhooks & integrations"],
    featured: true,
  },
  {
    name: "Studio",
    price: "$149",
    tagline: "Coaches with a team",
    points: ["Everything in Pro", "Up to 5 seats", "White-label booking page", "API access", "Priority support"],
    featured: false,
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo />
        <nav className="flex items-center gap-2 sm:gap-4">
          <a href="#features" className="hidden px-3 py-2 text-sm text-muted hover:text-deep-green sm:block">Features</a>
          <a href="#pricing" className="hidden px-3 py-2 text-sm text-muted hover:text-deep-green sm:block">Pricing</a>
          <Link href="/login" className="px-3 py-2 text-sm font-medium text-deep-green">Log in</Link>
          <Link href="/signup" className="btn-primary">Start free</Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-16 pt-10 sm:pt-16">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full bg-mint px-4 py-1.5 text-xs font-semibold text-deep-green">
            <LogoMark className="h-4 w-4 text-forest" /> Built for coaches, not agencies
          </span>
          <h1 className="mt-6 text-4xl font-semibold leading-tight tracking-tight text-deep-green sm:text-6xl">
            The coach-first CRM that runs your follow-ups for you.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted">
            Pipeline, booking, payments, contracts and automated follow-ups — in one simple tool.
            All the power of GoHighLevel, none of the bloat, surprise bills, or month-long setup.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/signup" className="btn-primary w-full sm:w-auto">Start your 14-day trial</Link>
            <a href="#pricing" className="btn-ghost w-full sm:w-auto">See pricing</a>
          </div>
          <p className="mt-4 text-xs text-muted">No surcharge on your payments · Cancel anytime · Set up in a day</p>
        </div>

        {/* Mock board */}
        <div className="mx-auto mt-14 max-w-4xl">
          <div className="card p-4 sm:p-6">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {["Lead", "Discovery", "Active", "Renewal"].map((col, i) => (
                <div key={col} className="rounded-xl bg-canvas p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-semibold text-deep-green">{col}</span>
                    <span className="rounded-full bg-mint px-2 text-[10px] text-deep-green">{[4, 2, 6, 1][i]}</span>
                  </div>
                  <div className="space-y-2">
                    {Array.from({ length: [2, 1, 2, 1][i] }).map((_, j) => (
                      <div key={j} className="rounded-lg border border-deep-green/10 bg-white px-3 py-2">
                        <div className="h-2 w-2/3 rounded bg-sage/60" />
                        <div className="mt-1.5 h-1.5 w-1/3 rounded bg-deep-green/10" />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="border-y border-deep-green/10 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-14 text-center">
          <h2 className="text-2xl font-semibold text-deep-green sm:text-3xl">You didn&apos;t become a coach to wrestle software.</h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted">
            All-in-one platforms are built for agencies and bury you in features you&apos;ll never use.
            Simple coach tools can&apos;t automate a thing. Tendari does the few things you actually need —
            beautifully.
          </p>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-center text-2xl font-semibold text-deep-green sm:text-3xl">Everything a solo coach needs</h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-muted">And nothing they don&apos;t.</p>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="card">
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-mint">
                <LogoMark className="h-5 w-5 text-forest" />
              </div>
              <h3 className="text-lg font-semibold text-deep-green">{f.title}</h3>
              <p className="mt-2 text-sm text-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-white">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-center text-2xl font-semibold text-deep-green sm:text-3xl">Simple, flat pricing</h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-muted">No per-seat games. No usage surprises. 2 months free on annual.</p>
          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            {tiers.map((t) => (
              <div
                key={t.name}
                className={`card flex flex-col ${t.featured ? "ring-2 ring-forest" : ""}`}
              >
                {t.featured && (
                  <span className="mb-3 w-fit rounded-full bg-forest px-3 py-1 text-xs font-semibold text-white">Most popular</span>
                )}
                <h3 className="text-lg font-semibold text-deep-green">{t.name}</h3>
                <p className="text-sm text-muted">{t.tagline}</p>
                <p className="mt-4 text-4xl font-semibold text-deep-green">
                  {t.price}<span className="text-base font-normal text-muted">/mo</span>
                </p>
                <ul className="mt-5 flex-1 space-y-2 text-sm text-ink">
                  {t.points.map((p) => (
                    <li key={p} className="flex items-start gap-2">
                      <span className="mt-1 text-forest">✓</span>
                      {p}
                    </li>
                  ))}
                </ul>
                <Link href="/signup" className={`mt-6 ${t.featured ? "btn-primary" : "btn-ghost"}`}>
                  Start free
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-5xl px-6 py-20 text-center">
        <h2 className="text-3xl font-semibold text-deep-green">Ready to let your follow-ups run themselves?</h2>
        <p className="mx-auto mt-4 max-w-xl text-muted">Start free in under five minutes. Bring your clients, keep your Stripe.</p>
        <Link href="/signup" className="btn-primary mt-8">Start your 14-day trial</Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-deep-green/10 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-8 sm:flex-row">
          <Logo />
          <p className="text-xs text-muted">© {new Date().getFullYear()} Tendari. The coach-first CRM.</p>
        </div>
      </footer>
    </main>
  );
}
