import Link from "next/link";
import { Logo } from "@/components/logo";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="text-center">
        <div className="mb-6 flex justify-center"><Logo /></div>
        <h1 className="text-3xl font-semibold text-deep-green">Page not found</h1>
        <p className="mx-auto mt-2 max-w-sm text-muted">
          That link doesn&apos;t lead anywhere. It may have moved, or the form/booking link is no longer active.
        </p>
        <Link href="/" className="btn-primary mt-6">Back to home</Link>
      </div>
    </main>
  );
}
