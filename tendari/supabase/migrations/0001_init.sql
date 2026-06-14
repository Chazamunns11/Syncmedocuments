-- Tendari — initial schema (Phase 0–1): tenancy, contacts, pipeline, activities.
-- Multi-tenant isolation via Row-Level Security keyed on the caller's account_id.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Tenancy
-- ---------------------------------------------------------------------------
create table if not exists public.accounts (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  slug          text unique not null,
  plan          text not null default 'trial',
  trial_ends_at timestamptz not null default (now() + interval '14 days'),
  created_at    timestamptz not null default now()
);

create table if not exists public.users (
  id          uuid primary key references auth.users(id) on delete cascade,
  account_id  uuid not null references public.accounts(id) on delete cascade,
  email       text,
  name        text,
  role        text not null default 'owner',
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Pipeline
-- ---------------------------------------------------------------------------
create table if not exists public.pipelines (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  name        text not null,
  is_default  boolean not null default false,
  created_at  timestamptz not null default now()
);

create table if not exists public.stages (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  pipeline_id uuid not null references public.pipelines(id) on delete cascade,
  name        text not null,
  position    int  not null default 0,
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Contacts
-- ---------------------------------------------------------------------------
create table if not exists public.contacts (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  first_name  text,
  last_name   text,
  email       text,
  phone       text,
  source      text,
  notes       text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists contacts_account_idx on public.contacts(account_id, created_at desc);
create unique index if not exists contacts_account_email_idx
  on public.contacts(account_id, lower(email)) where email is not null;

create table if not exists public.deals (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  contact_id  uuid references public.contacts(id) on delete set null,
  pipeline_id uuid not null references public.pipelines(id) on delete cascade,
  stage_id    uuid not null references public.stages(id) on delete cascade,
  title       text not null,
  value_cents bigint not null default 0,
  status      text not null default 'open',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists deals_account_idx on public.deals(account_id, stage_id);

create table if not exists public.activities (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  contact_id  uuid references public.contacts(id) on delete cascade,
  type        text not null default 'note',
  title       text,
  body        text,
  created_at  timestamptz not null default now()
);
create index if not exists activities_contact_idx on public.activities(account_id, contact_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Helper: the caller's account_id (security definer bypasses RLS on users)
-- ---------------------------------------------------------------------------
create or replace function public.current_account_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select account_id from public.users where id = auth.uid()
$$;

-- ---------------------------------------------------------------------------
-- Row-Level Security: every table scoped to the caller's account
-- ---------------------------------------------------------------------------
alter table public.accounts   enable row level security;
alter table public.users      enable row level security;
alter table public.pipelines  enable row level security;
alter table public.stages     enable row level security;
alter table public.contacts   enable row level security;
alter table public.deals      enable row level security;
alter table public.activities enable row level security;

-- accounts: a user can see their own account
drop policy if exists tenant_accounts on public.accounts;
create policy tenant_accounts on public.accounts
  for all using (id = public.current_account_id())
  with check (id = public.current_account_id());

-- users: rows within the caller's account
drop policy if exists tenant_users on public.users;
create policy tenant_users on public.users
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

-- generic account-scoped tables
drop policy if exists tenant_pipelines on public.pipelines;
create policy tenant_pipelines on public.pipelines
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_stages on public.stages;
create policy tenant_stages on public.stages
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_contacts on public.contacts;
create policy tenant_contacts on public.contacts
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_deals on public.deals;
create policy tenant_deals on public.deals
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_activities on public.activities;
create policy tenant_activities on public.activities
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

-- ---------------------------------------------------------------------------
-- On signup: create account + user row + default pipeline with starter stages
-- ---------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_account  uuid;
  v_pipeline uuid;
begin
  insert into public.accounts (name, slug)
  values (
    coalesce(new.raw_user_meta_data->>'business_name', 'My Coaching Business'),
    'acct-' || replace(new.id::text, '-', '')
  )
  returning id into v_account;

  insert into public.users (id, account_id, email, name)
  values (
    new.id,
    v_account,
    new.email,
    coalesce(new.raw_user_meta_data->>'name', new.email)
  );

  insert into public.pipelines (account_id, name, is_default)
  values (v_account, 'Clients', true)
  returning id into v_pipeline;

  insert into public.stages (account_id, pipeline_id, name, position) values
    (v_account, v_pipeline, 'Lead', 1),
    (v_account, v_pipeline, 'Discovery Call', 2),
    (v_account, v_pipeline, 'Proposal', 3),
    (v_account, v_pipeline, 'Active Client', 4),
    (v_account, v_pipeline, 'Renewal', 5),
    (v_account, v_pipeline, 'Past', 6);

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
