-- Tendari — store each account's timezone so dates/overdue render in the coach's zone.

alter table public.accounts
  add column if not exists timezone text not null default 'UTC';
