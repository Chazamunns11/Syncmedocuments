"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LogoMark } from "@/components/logo";

type Step = {
  badge: string;
  title: string;
  body: string;
  cta?: { label: string; href: string };
};

const steps: Step[] = [
  {
    badge: "Welcome",
    title: "This is Tendari — your calm command centre",
    body: "Everything you need to run your coaching practice lives here, and nothing you don't. This 30-second tour shows you around. You can replay it any time from “How to use”.",
  },
  {
    badge: "Step 1",
    title: "Add your people in Contacts",
    body: "Your clients and leads live in Contacts. Adding one takes five seconds — just a name is enough to start. Everything else hangs off the contact: bookings, payments, notes.",
    cta: { label: "Go to Contacts", href: "/dashboard/contacts" },
  },
  {
    badge: "Step 2",
    title: "Track everyone in your Pipeline",
    body: "The Pipeline is a simple board: Lead → Discovery → Proposal → Active → Renewal → Past. Drag a client between columns, set a deal value, and mark deals won or lost.",
    cta: { label: "Open Pipeline", href: "/dashboard/pipeline" },
  },
  {
    badge: "Step 3",
    title: "Get booked & capture leads",
    body: "Set your availability and share your booking link so clients book themselves in. Add a lead form and every submission becomes a contact automatically.",
    cta: { label: "Set up Booking", href: "/dashboard/booking" },
  },
  {
    badge: "Coming next",
    title: "Payments & automatic follow-ups",
    body: "Soon you'll take payment through your own Stripe (no surcharge) and set up “wait 3 days, then email” automations. We'll guide you through each one when it lands.",
  },
  {
    badge: "You're set",
    title: "That's the whole tool",
    body: "Honestly — that's it. Tendari is built to stay this simple. Start by adding your first contact.",
    cta: { label: "Add my first contact", href: "/dashboard/contacts" },
  },
];

const STORAGE_KEY = "tendari_onboarded_v1";

export function OnboardingTour() {
  const [open, setOpen] = useState(false);
  const [i, setI] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!window.localStorage.getItem(STORAGE_KEY)) setOpen(true);
    const handler = () => {
      setI(0);
      setOpen(true);
    };
    window.addEventListener("tendari:tour", handler);
    return () => window.removeEventListener("tendari:tour", handler);
  }, []);

  function close() {
    setOpen(false);
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {}
  }

  if (!open) return null;
  const step = steps[i];
  const last = i === steps.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-deep-green/30 p-4 backdrop-blur-sm sm:items-center">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-soft">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 rounded-full bg-mint px-3 py-1 text-xs font-semibold text-deep-green">
            <LogoMark className="h-4 w-4 text-forest" /> {step.badge}
          </span>
          <button onClick={close} className="text-xs text-muted hover:text-deep-green">
            Skip tour
          </button>
        </div>

        <h2 className="mt-4 text-xl font-semibold text-deep-green">{step.title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>

        {step.cta && (
          <Link
            href={step.cta.href}
            onClick={close}
            className="btn-ghost mt-4 w-full"
          >
            {step.cta.label}
          </Link>
        )}

        {/* Progress + controls */}
        <div className="mt-6 flex items-center justify-between">
          <div className="flex gap-1.5">
            {steps.map((_, idx) => (
              <span
                key={idx}
                className={`h-1.5 rounded-full transition-all ${
                  idx === i ? "w-5 bg-forest" : "w-1.5 bg-deep-green/15"
                }`}
              />
            ))}
          </div>
          <div className="flex gap-2">
            {i > 0 && (
              <button onClick={() => setI(i - 1)} className="btn-ghost px-4 py-2 text-xs">
                Back
              </button>
            )}
            {last ? (
              <button onClick={close} className="btn-primary px-5 py-2 text-xs">
                Done
              </button>
            ) : (
              <button onClick={() => setI(i + 1)} className="btn-primary px-5 py-2 text-xs">
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Small button that re-opens the tour from anywhere. */
export function ReplayTourButton({
  className = "",
  label = "Replay the walkthrough",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <button
      onClick={() => window.dispatchEvent(new Event("tendari:tour"))}
      className={className || "btn-ghost"}
    >
      {label}
    </button>
  );
}
