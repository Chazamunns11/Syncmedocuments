"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/contacts", label: "Contacts" },
  { href: "/dashboard/pipeline", label: "Pipeline" },
  { href: "/dashboard/payments", label: "Payments" },
  { href: "/dashboard/booking", label: "Booking" },
  { href: "/dashboard/tasks", label: "Follow-ups" },
  { href: "/dashboard/forms", label: "Lead forms" },
  { href: "/dashboard/contracts", label: "Contracts" },
  { href: "/dashboard/automations", label: "Automations" },
  { href: "/dashboard/notifications", label: "Notifications" },
  { href: "/dashboard/settings", label: "Settings" },
  { href: "/dashboard/guide", label: "How to use" },
];

export function DashboardNav() {
  const pathname = usePathname();
  return (
    <nav className="space-y-1">
      {links.map((l) => {
        const active = pathname === l.href;
        return (
          <Link
            key={l.href}
            href={l.href}
            className={`block rounded-lg px-3 py-2 text-sm font-medium transition ${
              active
                ? "bg-mint text-deep-green"
                : "text-muted hover:bg-mint/50 hover:text-deep-green"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
