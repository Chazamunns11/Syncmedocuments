-- Tendari — contracts & e-signature. Coach creates a contract; client signs via a
-- public link (typed signature). Signing is done via SECURITY DEFINER functions so
-- no tenant data is exposed.

create table if not exists public.contracts (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references public.accounts(id) on delete cascade,
  contact_id  uuid references public.contacts(id) on delete set null,
  title       text not null,
  body        text not null,
  token       text not null unique default replace(gen_random_uuid()::text, '-', ''),
  status      text not null default 'sent',   -- sent | signed | void
  signed_name text,
  signed_at   timestamptz,
  created_at  timestamptz not null default now()
);
create index if not exists contracts_account_idx on public.contracts(account_id, created_at desc);

alter table public.contracts enable row level security;

drop policy if exists tenant_contracts on public.contracts;
create policy tenant_contracts on public.contracts
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

-- Public: fetch a contract for signing (only meaningful fields).
create or replace function public.get_contract(p_token text)
returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'title', title, 'body', body, 'status', status, 'signed_name', signed_name
  )
  from public.contracts where token = p_token
$$;

-- Public: sign a contract.
create or replace function public.sign_contract(p_token text, p_name text)
returns boolean language plpgsql security definer set search_path = public as $$
declare
  v_id uuid; v_account uuid; v_contact uuid; v_title text;
begin
  select id, account_id, contact_id, title
    into v_id, v_account, v_contact, v_title
    from public.contracts where token = p_token and status = 'sent';
  if v_id is null then
    return false;
  end if;
  if p_name is null or length(trim(p_name)) = 0 then
    return false;
  end if;

  update public.contracts
    set status = 'signed', signed_name = trim(p_name), signed_at = now()
    where id = v_id;

  if v_contact is not null then
    insert into public.activities (account_id, contact_id, type, title, body)
    values (v_account, v_contact, 'contract', 'Contract signed', v_title || ' — signed by ' || trim(p_name));
  end if;

  insert into public.notifications (account_id, type, title, body)
  values (v_account, 'contract', 'Contract signed', trim(p_name) || ' signed “' || v_title || '”');

  return true;
end; $$;

grant execute on function public.get_contract(text) to anon, authenticated;
grant execute on function public.sign_contract(text, text) to anon, authenticated;
