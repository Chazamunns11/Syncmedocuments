# Running Tendari

The database is live and fully set up: Supabase project **Tendari**
(`pzjbtialonebralirvdi`, eu-north-1), all migrations applied, RLS on every table.

## Environment variables
The app needs these (the `.env.local` file is gitignored, so it is NOT in the repo —
create it locally). The anon key is the public client key and is safe to put here.

```
NEXT_PUBLIC_SUPABASE_URL=https://pzjbtialonebralirvdi.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key from Supabase → Settings → API>
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

## Google Calendar sync (optional)
Add these env vars (server-only — do NOT prefix with NEXT_PUBLIC):
```
SUPABASE_SERVICE_ROLE_KEY=   # Supabase → Settings → API → service_role secret
GOOGLE_OAUTH_CLIENT_ID=      # Google Cloud → Credentials → OAuth client (Web app)
GOOGLE_OAUTH_CLIENT_SECRET=
```
In Google Cloud, the OAuth client's **Authorized redirect URI** must be
`<NEXT_PUBLIC_SITE_URL>/api/google/callback`, and the OAuth consent screen needs the
`.../auth/calendar.events` scope. Coaches then connect from Settings → Integrations;
new bookings are pushed to their Google Calendar automatically.

## Run locally
```bash
cd tendari
# create .env.local with the three vars above
npm install
npm run dev          # http://localhost:3000
```
In Supabase → Auth → Providers → Email, turn **off** "Confirm email" so signups log in
instantly during testing.

## Deploy (Vercel or Netlify)
1. Import the GitHub repo; set the project root/base directory to `tendari/`.
2. Add the three `NEXT_PUBLIC_*` env vars (set `NEXT_PUBLIC_SITE_URL` to the deployed URL).
3. Deploy. Update Supabase → Auth → URL configuration with the deployed domain.

## Note on this cloud session
Claude Code's web sandbox has a network egress allowlist that does not include the
Supabase host, so the live app can't be exercised from inside it (the database itself is
managed via an allowed API). To let Claude verify end-to-end here, add
`pzjbtialonebralirvdi.supabase.co` to the environment's network egress settings.
