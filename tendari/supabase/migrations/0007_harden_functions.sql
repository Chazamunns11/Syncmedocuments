-- Tendari — tighten EXECUTE on internal SECURITY DEFINER functions.
-- The four public functions (get_form, submit_lead, get_booking_context,
-- submit_booking) stay anon-callable by design — they power the public
-- form/booking pages and are token-scoped. These two are internal.
--
-- Note: Supabase grants EXECUTE to anon/authenticated explicitly (via default
-- privileges), so we must revoke from those roles directly, not just PUBLIC.

-- Trigger function: must never be callable via the REST API.
revoke execute on function public.handle_new_user() from public, anon, authenticated;

-- RLS helper: only signed-in users need it (RLS policies run as the caller).
revoke execute on function public.current_account_id() from public, anon;
grant  execute on function public.current_account_id() to authenticated;
