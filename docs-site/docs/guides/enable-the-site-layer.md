---
title: Enable the site layer
area: utility
surface: selfhost
---

# Enable the site layer

The site layer is the optional part of OHM that tracks **who visited the site
and how it looks** — a visitor gate, batched telemetry, whitelabel theme
config, and the Mission Control page. It is **off by default**, and an instance
that never enables it is not degraded; it is the normal deployment.

It never grants application permissions. Whether you may create a design or
manage API keys comes from your OHM API key, not from anything here. See
[the architecture note](https://github.com/binaryLady/OHM/blob/main/docs/architecture/site-layer.md)
for why that boundary matters.

Everything below runs in the Supabase **SQL editor**. None of it is reachable
from a browser client — that is deliberate.

## 1. Create a project and run the schema

Create a Supabase project, open the SQL editor, and run
[`supabase/schema.sql`](https://github.com/binaryLady/OHM/blob/main/supabase/schema.sql)
in full.

It creates four tables — `ohmgr_visitors`, `ohmgr_telemetry_events`,
`ohmgr_site_config`, `ohmgr_admin_secrets` — with row-level security on all
four, and the `SECURITY DEFINER` functions that are the only way in. The script
is idempotent, so re-running it is safe.

Confirm it landed:

```sql
select table_name
from information_schema.tables
where table_schema = 'public' and table_name like 'ohmgr_%'
order by table_name;
-- expect: ohmgr_admin_secrets, ohmgr_site_config,
--         ohmgr_telemetry_events, ohmgr_visitors
```

Check the **functions** too. The tables can land while the functions do not, and
the client's 404 is on a function, so the query above alone would not catch it:

```sql
select routine_name
from information_schema.routines
where routine_schema = 'public' and routine_name like 'ohmgr_%'
order by routine_name;
-- expect ohmgr_track, ohmgr_gate_signin and ohmgr_is_admin among them
```

Finally, confirm the anon key may actually call it. A function that exists but
was never granted to `anon` returns the same 404 through PostgREST, from a
different cause:

```sql
select has_function_privilege('anon', 'public.ohmgr_track(jsonb)', 'execute');
-- expect: true
```

## 2. Set the operator token

The operator token is what unlocks unmasked visitor records and config
publishing. Only its SHA-256 hash is stored, so the token itself exists nowhere
in the database.

Generate a long random string yourself, then:

```sql
insert into public.ohmgr_admin_secrets (id, token_hash)
values (1, encode(digest('PASTE-A-LONG-RANDOM-TOKEN-HERE', 'sha256'), 'hex'))
on conflict (id) do update
  set token_hash = excluded.token_hash, updated_at = now();
```

If `digest` is not available, enable pgcrypto first:

```sql
create extension if not exists pgcrypto;
```

Verify the token works — this returns `true` only for the right string:

```sql
select public.ohmgr_check_admin('PASTE-THE-SAME-TOKEN-HERE');
```

Keep the token in a password manager. The UI holds it in `sessionStorage` for
one tab and never persists it.

## 3. Grant an operator marker (optional)

`is_admin` on a visitor row is a *marker*, not the credential — it decides
whether Mission Control offers the operator card, while the token above is what
actually authorises anything. It is grantable only from here:

```sql
update public.ohmgr_visitors
   set is_admin = true
 where email = 'you@example.com';
```

The visitor row is created when that email first signs in at the gate, so sign
in once before running this.

## 4. Point the app at the project

Set both variables on your deployment and rebuild:

```bash
NEXT_PUBLIC_OHM_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_OHM_SUPABASE_ANON_KEY=<the anon key>
```

They are `NEXT_PUBLIC_` because the anon key is public by design: with RLS on
every table, it can only call the whitelisted RPCs, and the privileged ones
check the operator token server-side before returning anything.

## 5. Write the gate (optional)

Once the layer is on, opening `/mission-control` without a visitor record on
that device raises the sign-in gate. Nothing else is gated: the dashboard,
designs, facilities and matching stay open to everyone, because site sign-in is
not an OHM permission.

The wording is yours. Empty strings mean "use the built-in copy", so you can set
one field and leave the rest:

```sql
select public.ohmgr_publish_config('PASTE-THE-SAME-TOKEN-HERE', jsonb_build_object(
  'gate', jsonb_build_object(
    'enabled', true,
    'title',   'Sign in to Mission Control',
    'body',    'So your visit has a record you own.',
    'fine',    'Unverified, kept on this device, and no permissions in OHM.'
  )
));
```

Set `"enabled": false` if this instance should ask nobody to sign in. Mission
Control then shows the unsigned view with no dialog and no sign-in button.

## 6. Verify the boundary holds

Run these as the **anon** role (a fresh SQL editor session is not anon — use
the REST endpoint with the anon key, or the API docs' "Run" button):

```sql
-- Privileged RPCs must refuse without the token.
select public.ohmgr_admin_visitors('wrong-token');   -- expect: unauthorized
select public.ohmgr_admin_stats('wrong-token');      -- expect: unauthorized

-- Masked reads must never return a raw email.
select * from public.ohmgr_visitors_masked('you@example.com');

-- Direct table access must be refused by RLS.
select * from public.ohmgr_visitors;                 -- expect: no rows / denied
```

A visitor can only mutate their own row:

```sql
select public.ohmgr_update_own_name('you@example.com', 'New name');  -- ok
select public.ohmgr_update_own_name('someone@else.com', 'Nope');     -- refused
```

## Turning it off

Unset the two environment variables and rebuild. The app returns to its default
posture: no gate, no telemetry, `/mission-control` 404s, no nav entry, and
theme and mode continue to work from the device. The Supabase client is
code-split, so a build with the layer off never fetches it.

## Troubleshooting

**`404` on `/rest/v1/rpc/ohmgr_track`** — the environment variables are set but
the schema has not been run in that project. Run step 1, then check both
verification queries there: the function may be missing, or present but not
granted to `anon`, and PostgREST reports the two identically.

The client goes dormant after the first 404 rather than retrying every page
view, so one such error in the console is expected until the schema lands. That
dormancy is per page load, not per session — **hard-reload after running the
schema**, or a tab that was open beforehand stays quiet and keeps looking broken.

**`unauthorized` from every operator call** — the token in the browser does not
hash to what is stored. Re-run step 2 and paste the same string into Mission
Control.

**Telemetry silently absent** — expected when the layer is off. Telemetry is
fail-soft by design and must never break a page; matching designs to facilities
is the job that matters.
