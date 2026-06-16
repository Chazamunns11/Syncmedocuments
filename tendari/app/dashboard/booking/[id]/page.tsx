import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { MeetingTypeEditor } from "@/components/meeting-type-editor";

export default async function MeetingTypeEditorPage({ params }: { params: { id: string } }) {
  const supabase = createClient();
  const { data } = await supabase
    .from("meeting_types")
    .select("id, name, token, duration_min, description, buffer_min, min_notice_min, max_per_day, questions")
    .eq("id", params.id)
    .single();
  if (!data) notFound();
  const base = process.env.NEXT_PUBLIC_SITE_URL || "";

  return (
    <div>
      <Link href="/dashboard/booking" className="text-sm text-muted hover:text-deep-green">← Back to booking</Link>
      <h1 className="mt-3 text-2xl font-semibold text-deep-green">Edit meeting type</h1>
      <p className="mt-1 text-sm text-muted">
        Booking link:{" "}
        <a href={`${base}/b/${data.token}`} target="_blank" className="text-forest hover:underline">
          {base ? `${base}/b/${data.token}` : `/b/${data.token}`}
        </a>
      </p>
      <div className="mt-6">
        <MeetingTypeEditor mt={data} />
      </div>
    </div>
  );
}
