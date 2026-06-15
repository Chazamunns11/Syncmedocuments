-- Tendari — automation engine.
-- A workflow = a trigger + an ordered list of steps (jsonb). Events enqueue a
-- workflow_run; a worker (process_workflow_runs, run by pg_cron) advances each
-- run, executing immediate steps and pausing on 'wait' steps.

create table if not exists public.workflows (
  id           uuid primary key default gen_random_uuid(),
  account_id   uuid not null references public.accounts(id) on delete cascade,
  name         text not null,
  trigger_type text not null,                 -- contact_created | booking_created | tag_added
  steps        jsonb not null default '[]'::jsonb,
  active       boolean not null default true,
  created_at   timestamptz not null default now()
);

create table if not exists public.workflow_runs (
  id           uuid primary key default gen_random_uuid(),
  account_id   uuid not null references public.accounts(id) on delete cascade,
  workflow_id  uuid not null references public.workflows(id) on delete cascade,
  contact_id   uuid references public.contacts(id) on delete cascade,
  current_step int not null default 0,
  status       text not null default 'active', -- active | waiting | done
  next_run_at  timestamptz not null default now(),
  created_at   timestamptz not null default now()
);
create index if not exists workflow_runs_due_idx on public.workflow_runs(status, next_run_at);

alter table public.workflows     enable row level security;
alter table public.workflow_runs enable row level security;

drop policy if exists tenant_workflows on public.workflows;
create policy tenant_workflows on public.workflows
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

drop policy if exists tenant_workflow_runs on public.workflow_runs;
create policy tenant_workflow_runs on public.workflow_runs
  for all using (account_id = public.current_account_id())
  with check (account_id = public.current_account_id());

-- Enqueue a run for every active workflow matching an event.
create or replace function public.enqueue_workflows(p_account uuid, p_trigger text, p_contact uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
  insert into public.workflow_runs (account_id, workflow_id, contact_id)
  select w.account_id, w.id, p_contact
    from public.workflows w
   where w.account_id = p_account and w.active = true and w.trigger_type = p_trigger;
end; $$;

-- Event triggers.
create or replace function public.tg_contacts_enqueue()
returns trigger language plpgsql security definer set search_path = public as $$
begin perform public.enqueue_workflows(new.account_id, 'contact_created', new.id); return new; end; $$;

create or replace function public.tg_bookings_enqueue()
returns trigger language plpgsql security definer set search_path = public as $$
begin perform public.enqueue_workflows(new.account_id, 'booking_created', new.contact_id); return new; end; $$;

create or replace function public.tg_tags_enqueue()
returns trigger language plpgsql security definer set search_path = public as $$
begin perform public.enqueue_workflows(new.account_id, 'tag_added', new.contact_id); return new; end; $$;

drop trigger if exists contacts_enqueue on public.contacts;
create trigger contacts_enqueue after insert on public.contacts
  for each row execute function public.tg_contacts_enqueue();

drop trigger if exists bookings_enqueue on public.bookings;
create trigger bookings_enqueue after insert on public.bookings
  for each row execute function public.tg_bookings_enqueue();

drop trigger if exists contact_tags_enqueue on public.contact_tags;
create trigger contact_tags_enqueue after insert on public.contact_tags
  for each row execute function public.tg_tags_enqueue();

-- The worker: advance all due runs. Step types: wait, add_tag, create_task, notify.
create or replace function public.process_workflow_runs()
returns void language plpgsql security definer set search_path = public as $$
declare
  r       record;
  w_steps jsonb;
  w_active boolean;
  step    jsonb;
  stype   text;
  cname   text;
  v_step  int;
  v_tag   uuid;
begin
  for r in
    select * from public.workflow_runs
     where status in ('active','waiting') and next_run_at <= now()
     order by next_run_at limit 200 for update skip locked
  loop
    select steps, active into w_steps, w_active from public.workflows where id = r.workflow_id;
    if w_steps is null or w_active is not true then
      update public.workflow_runs set status = 'done' where id = r.id; continue;
    end if;

    select coalesce(nullif(trim(coalesce(c.first_name,'') || ' ' || coalesce(c.last_name,'')), ''), c.email)
      into cname from public.contacts c where c.id = r.contact_id;
    if cname is null then cname := 'there'; end if;

    v_step := r.current_step;
    loop
      step := w_steps -> v_step;
      if step is null then
        update public.workflow_runs set status = 'done', current_step = v_step where id = r.id; exit;
      end if;
      stype := step->>'type';

      if stype = 'wait' then
        update public.workflow_runs
          set status = 'waiting', current_step = v_step + 1,
              next_run_at = now() + make_interval(
                days => coalesce((step->>'days')::int, 0),
                mins => coalesce((step->>'minutes')::int, 0))
          where id = r.id;
        exit;

      elsif stype = 'add_tag' then
        select id into v_tag from public.tags
          where account_id = r.account_id and lower(name) = lower(step->>'name') limit 1;
        if v_tag is null then
          insert into public.tags (account_id, name) values (r.account_id, step->>'name') returning id into v_tag;
        end if;
        if r.contact_id is not null then
          insert into public.contact_tags (account_id, contact_id, tag_id)
          values (r.account_id, r.contact_id, v_tag) on conflict do nothing;
        end if;

      elsif stype = 'create_task' then
        insert into public.tasks (account_id, contact_id, title, due_on)
        values (r.account_id, r.contact_id,
                replace(coalesce(step->>'title', 'Follow up'), '{name}', cname),
                (now() + make_interval(days => coalesce((step->>'offset_days')::int, 0)))::date);

      elsif stype = 'notify' then
        insert into public.notifications (account_id, type, title, body)
        values (r.account_id, 'automation',
                coalesce(step->>'title', 'Automation'),
                replace(coalesce(step->>'body', ''), '{name}', cname));

      else
        null; -- unknown / reserved (e.g. send_email) -> skip for now
      end if;

      v_step := v_step + 1;
      update public.workflow_runs set current_step = v_step where id = r.id;
    end loop;
  end loop;
end; $$;

-- Internal functions: not part of the public API.
revoke execute on function public.enqueue_workflows(uuid, text, uuid) from public, anon, authenticated;
revoke execute on function public.process_workflow_runs() from public, anon, authenticated;
revoke execute on function public.tg_contacts_enqueue() from public, anon, authenticated;
revoke execute on function public.tg_bookings_enqueue() from public, anon, authenticated;
revoke execute on function public.tg_tags_enqueue() from public, anon, authenticated;
