-- Tendari — in-app notifications. Lead-form and booking submissions notify the coach.

create table if not exists public.notifications (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  type        text not null default 'info',
  title       text not null,
  body        text,
  read        boolean not null default false,
  created_at  timestamptz not null default now()
);
create index if not exists notifications_account_idx
  on public.notifications(account_id, read, created_at desc);

alter table public.notifications enable row level security;

drop policy if exists tenant_notifications on public.notifications;
create policy tenant_notifications on public.notifications
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

-- Re-create submit_lead to also raise a notification for the coach.
create or replace function public.submit_lead(
  p_token   text,
  p_first   text,
  p_last    text,
  p_email   text,
  p_phone   text,
  p_message text
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  v_account uuid;
  v_contact uuid;
  v_name    text;
begin
  select account_id into v_account from public.forms where token = p_token and active = true;
  if v_account is null then
    return false;
  end if;

  if p_email is not null and length(trim(p_email)) > 0 then
    select id into v_contact from public.contacts
      where account_id = v_account and lower(email) = lower(trim(p_email)) limit 1;
  end if;

  if v_contact is null then
    insert into public.contacts (account_id, first_name, last_name, email, phone, source)
    values (v_account, nullif(trim(p_first),''), nullif(trim(p_last),''),
            nullif(trim(p_email),''), nullif(trim(p_phone),''), 'form')
    returning id into v_contact;
  end if;

  insert into public.activities (account_id, contact_id, type, title, body)
  values (v_account, v_contact, 'form_submission', 'Form submission', nullif(trim(p_message), ''));

  v_name := nullif(trim(both ' ' from coalesce(p_first,'') || ' ' || coalesce(p_last,'')), '');
  insert into public.notifications (account_id, type, title, body)
  values (v_account, 'lead', 'New lead',
          coalesce(v_name, p_email, 'Someone') || ' submitted a form');

  return true;
end;
$$;

-- Re-create submit_booking to also raise a notification.
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
  v_name     text;
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

  v_name := nullif(trim(both ' ' from coalesce(p_first,'') || ' ' || coalesce(p_last,'')), '');

  insert into public.bookings (account_id, contact_id, meeting_type_id, starts_at, ends_at, name, email)
  values (v_account, v_contact, v_mt, p_start, v_end, v_name, nullif(trim(p_email),''));

  insert into public.activities (account_id, contact_id, type, title, body)
  values (v_account, v_contact, 'booking', 'Booked a call', to_char(p_start, 'YYYY-MM-DD HH24:MI UTC'));

  insert into public.notifications (account_id, type, title, body)
  values (v_account, 'booking', 'New booking',
          coalesce(v_name, p_email, 'Someone') || ' booked for ' || to_char(p_start, 'DD Mon HH24:MI UTC'));

  return true;
end;
$$;
