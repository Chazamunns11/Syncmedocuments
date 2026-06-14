-- Tendari — tasks / manual follow-ups (Phase 1.5, works offline before the automation engine).

create table if not exists public.tasks (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  contact_id  uuid references public.contacts(id) on delete set null,
  title       text not null,
  due_on      date,
  done        boolean not null default false,
  created_at  timestamptz not null default now()
);
create index if not exists tasks_account_idx on public.tasks(account_id, done, due_on);

alter table public.tasks enable row level security;

drop policy if exists tenant_tasks on public.tasks;
create policy tenant_tasks on public.tasks
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());
