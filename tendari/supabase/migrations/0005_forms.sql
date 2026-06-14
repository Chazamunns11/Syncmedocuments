-- Tendari — public lead-capture forms.
-- A form has a public token. Anonymous visitors submit via SECURITY DEFINER
-- functions (get_form / submit_lead) so no tenant data is exposed via RLS.

create table if not exists public.forms (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  name        text not null,
  token       text not null unique default replace(gen_random_uuid()::text, '-', ''),
  active      boolean not null default true,
  created_at  timestamptz not null default now()
);

alter table public.forms enable row level security;

drop policy if exists tenant_forms on public.forms;
create policy tenant_forms on public.forms
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

-- Public: fetch an active form's name by token (no tenant data leaked).
create or replace function public.get_form(p_token text)
returns text
language sql
stable
security definer
set search_path = public
as $$
  select name from public.forms where token = p_token and active = true
$$;

-- Public: submit a lead. Creates/links a contact in the form's account and
-- logs a form_submission activity. Runs as definer to bypass RLS safely.
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
begin
  select account_id into v_account from public.forms where token = p_token and active = true;
  if v_account is null then
    return false;
  end if;

  if p_email is not null and length(trim(p_email)) > 0 then
    select id into v_contact
      from public.contacts
      where account_id = v_account and lower(email) = lower(trim(p_email))
      limit 1;
  end if;

  if v_contact is null then
    insert into public.contacts (account_id, first_name, last_name, email, phone, source)
    values (
      v_account,
      nullif(trim(p_first), ''),
      nullif(trim(p_last), ''),
      nullif(trim(p_email), ''),
      nullif(trim(p_phone), ''),
      'form'
    )
    returning id into v_contact;
  end if;

  insert into public.activities (account_id, contact_id, type, title, body)
  values (v_account, v_contact, 'form_submission', 'Form submission', nullif(trim(p_message), ''));

  return true;
end;
$$;

grant execute on function public.get_form(text) to anon, authenticated;
grant execute on function public.submit_lead(text, text, text, text, text, text) to anon, authenticated;
