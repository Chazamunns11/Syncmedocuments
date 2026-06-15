-- Tendari — outbound webhooks. Adds a 'webhook' automation step that POSTs to a URL
-- (Zapier / Make / n8n) via pg_net. Inbound webhooks reuse lead-form tokens
-- (see app /api/hooks/[token]).

create extension if not exists pg_net;

create or replace function public.process_workflow_runs()
returns void language plpgsql security definer set search_path = public, extensions, net as $$
declare
  r record; w_steps jsonb; w_active boolean; step jsonb; stype text; cname text; v_step int; v_tag uuid;
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
              next_run_at = now() + make_interval(days => coalesce((step->>'days')::int,0), mins => coalesce((step->>'minutes')::int,0))
          where id = r.id;
        exit;
      elsif stype = 'add_tag' then
        select id into v_tag from public.tags where account_id = r.account_id and lower(name) = lower(step->>'name') limit 1;
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
                (now() + make_interval(days => coalesce((step->>'offset_days')::int,0)))::date);
      elsif stype = 'notify' then
        insert into public.notifications (account_id, type, title, body)
        values (r.account_id, 'automation', coalesce(step->>'title','Automation'),
                replace(coalesce(step->>'body',''), '{name}', cname));
      elsif stype = 'webhook' then
        begin
          perform net.http_post(
            url := step->>'url',
            body := jsonb_build_object('event', 'automation', 'contact_id', r.contact_id, 'name', cname),
            headers := '{"Content-Type": "application/json"}'::jsonb
          );
        exception when others then
          null; -- never let a bad webhook URL fail the run
        end;
      else
        null;
      end if;
      v_step := v_step + 1;
      update public.workflow_runs set current_step = v_step where id = r.id;
    end loop;
  end loop;
end; $$;

revoke execute on function public.process_workflow_runs() from public, anon, authenticated;
