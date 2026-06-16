import { createClient } from "@/lib/supabase/server";
import { updateTag, deleteTag } from "../contacts/tag-actions";

type Tag = { id: string; name: string; color: string };

export default async function TagsPage() {
  const supabase = createClient();
  const { data } = await supabase.from("tags").select("id, name, color").order("name");
  const tags = (data as Tag[]) || [];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-deep-green">Tags</h1>
      <p className="mt-1 text-muted">Rename, recolour or remove your segments. Add tags to people from any contact.</p>

      <div className="card mt-6 p-0">
        {tags.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted">No tags yet. Add one from a contact&apos;s page.</p>
        ) : (
          <ul className="divide-y divide-deep-green/10">
            {tags.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <form action={updateTag} className="flex flex-1 items-center gap-2">
                  <input type="hidden" name="id" value={t.id} />
                  <span className="h-4 w-4 shrink-0 rounded-full" style={{ backgroundColor: t.color }} />
                  <input name="name" defaultValue={t.name} className="input max-w-xs" />
                  <input name="color" type="color" defaultValue={t.color} className="h-9 w-12 rounded border border-deep-green/15" />
                  <button className="text-xs font-medium text-forest hover:underline">Save</button>
                </form>
                <form action={deleteTag}>
                  <input type="hidden" name="id" value={t.id} />
                  <button className="text-xs text-muted hover:text-red-600">Delete</button>
                </form>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
