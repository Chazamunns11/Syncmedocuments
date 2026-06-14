-- Tendari — contact tags / segments.

create table if not exists public.tags (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  name        text not null,
  created_at  timestamptz not null default now()
);
create unique index if not exists tags_account_name_idx on public.tags(account_id, lower(name));

create table if not exists public.contact_tags (
  account_id  uuid not null references public.accounts(id) on delete cascade,
  contact_id  uuid not null references public.contacts(id) on delete cascade,
  tag_id      uuid not null references public.tags(id) on delete cascade,
  primary key (contact_id, tag_id)
);

alter table public.tags enable row level security;
alter table public.contact_tags enable row level security;

drop policy if exists tenant_tags on public.tags;
create policy tenant_tags on public.tags
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_contact_tags on public.contact_tags;
create policy tenant_contact_tags on public.contact_tags
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());
