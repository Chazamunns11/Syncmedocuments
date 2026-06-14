import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tendari — the coach-first CRM that runs your follow-ups for you",
  description:
    "A simple, flat-priced CRM built for solo online coaches. Pipeline, booking, payments, contracts and automated follow-ups — without the bloat or bill shock.",
  icons: { icon: "/brand/logo-mark.svg" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  );
}
