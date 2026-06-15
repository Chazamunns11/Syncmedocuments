-- Tendari — schedule the automation worker with pg_cron (every minute).
-- Kept separate from 0009 so a cron issue never rolls back the engine itself.
-- If pg_cron isn't available on your plan, enable it in the Supabase dashboard
-- (Database → Extensions → pg_cron) and re-run the cron.schedule line below.

create extension if not exists pg_cron;

do $$
begin
  perform cron.unschedule('tendari_workflows');
exception when others then
  null;
end $$;

select cron.schedule('tendari_workflows', '* * * * *', 'select public.process_workflow_runs();');
