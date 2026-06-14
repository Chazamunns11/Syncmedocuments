-- Tendari — offline booking: meeting types, weekly availability, bookings.
-- Public visitors read availability + book via SECURITY DEFINER functions.

create table if not exists public.meeting_types (
  id           uuid primary key default gen_random_uuid(),
  account_id   uuid not null references public.accounts(id) on delete cascade,
  name         text not null,
  token        text not null unique default replace(gen_random_uuid()::text, '-', ''),
  duration_min int not null default 30,
  active       boolean not null default true,
  created_at   timestamptz not null default now()
);

-- Weekly availability windows, stored as minutes-from-midnight in the account timezone.
create table if not exists public.availability_rules (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  weekday     int  not null check (weekday between 0 and 6), -- 0 = Sunday
  start_min   int  not null check (start_min between 0 and 1440),
  end_min     int  not null check (end_min between 0 and 1440)
);

create table if not exists public.bookings (
  id              uuid primary key default gen_random_uuid(),
  account_id      uuid not null references public.accounts(id) on delete cascade,
  contact_id      uuid references public.contacts(id) on delete set null,
  meeting_type_id uuid references public.meeting_types(id) on delete set null,
  starts_at       timestamptz not null,
  ends_at         timestamptz not null,
  status          text not null default 'confirmed',
  name            text,
  email           text,
  created_at      timestamptz not null default now()
);
create index if not exists bookings_account_start_idx on public.bookings(account_id, starts_at);

alter table public.meeting_types     enable row level security;
alter table public.availability_rules enable row level security;
alter table public.bookings          enable row level security;

drop policy if exists tenant_meeting_types on public.meeting_types;
create policy tenant_meeting_types on public.meeting_types
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_availability on public.availability_rules;
create policy tenant_availability on public.availability_rules
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_bookings on public.bookings;
create policy tenant_bookings on public.bookings
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

-- Public: everything a booking page needs (no tenant data leaked beyond schedule).
create or replace function public.get_booking_context(p_token text)
returns json
language sql
stable
security definer
set search_path = public
as $$
  select json_build_object(
    'name', mt.name,
    'duration_min', mt.duration_min,
    'timezone', a.timezone,
    'rules', coalesce(
      (select json_agg(json_build_object('weekday', r.weekday, 'start_min', r.start_min, 'end_min', r.end_min))
         from public.availability_rules r where r.account_id = mt.account_id), '[]'::json),
    'booked', coalesce(
      (select json_agg(json_build_object('start', b.starts_at, 'end', b.ends_at))
         from public.bookings b
        where b.account_id = mt.account_id and b.status = 'confirmed' and b.ends_at > now()), '[]'::json)
  )
  from public.meeting_types mt
  join public.accounts a on a.id = mt.account_id
  where mt.token = p_token and mt.active = true
$$;

-- Public: book a slot. Validates it's in the future and not double-booked.
create or replace function public.submit_booking(
  p_token text,
  p_start timestamptz,
  p_first text,
  p_last  text,
  p_email text,
  p_phone text
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  v_account  uuid;
  v_mt       uuid;
  v_duration int;
  v_end      timestamptz;
  v_contact  uuid;
begin
  select mt.account_id, mt.id, mt.duration_min
    into v_account, v_mt, v_duration
    from public.meeting_types mt
    where mt.token = p_token and mt.active = true;
  if v_account is null then
    return false;
  end if;

  if p_start <= now() then
    return false;
  end if;
  v_end := p_start + make_interval(mins => v_duration);

  -- Reject overlaps with existing confirmed bookings.
  if exists (
    select 1 from public.bookings b
     where b.account_id = v_account and b.status = 'confirmed'
       and b.starts_at < v_end and b.ends_at > p_start
  ) then
    return false;
  end if;

  if p_email is not null and length(trim(p_email)) > 0 then
    select id into v_contact from public.contacts
      where account_id = v_account and lower(email) = lower(trim(p_email)) limit 1;
  end if;
  if v_contact is null then
    insert into public.contacts (account_id, first_name, last_name, email, phone, source)
    values (v_account, nullif(trim(p_first),''), nullif(trim(p_last),''),
            nullif(trim(p_email),''), nullif(trim(p_phone),''), 'booking')
    returning id into v_contact;
  end if;

  insert into public.bookings (account_id, contact_id, meeting_type_id, starts_at, ends_at, name, email)
  values (v_account, v_contact, v_mt, p_start, v_end,
          trim(both ' ' from coalesce(p_first,'') || ' ' || coalesce(p_last,'')), nullif(trim(p_email),''));

  insert into public.activities (account_id, contact_id, type, title, body)
  values (v_account, v_contact, 'booking', 'Booked a call', to_char(p_start, 'YYYY-MM-DD HH24:MI UTC'));

  return true;
end;
$$;

grant execute on function public.get_booking_context(text) to anon, authenticated;
grant execute on function public.submit_booking(text, timestamptz, text, text, text, text) to anon, authenticated;
