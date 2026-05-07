# supabase-fastapi-gateway

Minimal FastAPI gateway template for your web app/website which uses Supabase.

Right now your frontend probably calls Supabase directly, e.g.:

```text
https://xxxxx.supabase.co/functions/v1/generate-report
https://xxxxx.supabase.co/functions/v1/report-edit
https://xxxxx.supabase.co/functions/v1/get-report
```

With this gateway, the same calls become:

```text
https://api.yourdomain.com/v1/reports/generate
https://api.yourdomain.com/v1/reports/edit
https://api.yourdomain.com/v1/reports/get
```

It is intentionally small. Copy it into an existing React/Vite + Supabase app, then let an AI coding agent do the migration.

```text
Frontend  ->  FastAPI gateway  ->  Supabase
            api.yourdomain.com
```

## Why?

This is **not** primarily a security fix. Calling Supabase directly from the browser with a publishable/anon key is completely normal. Supabase explicitly designs for it, as long as Row Level Security is enabled and correctly configured. The real security risks are weak RLS policies or accidentally exposing the `service_role` key, and a gateway does not magically solve either of those.

What a gateway *does* give you is a better long-term **architecture and product surface**:

- `api.yourdomain.com/v1/reports/generate` reads as a real product API; `xxxxx.supabase.co/functions/v1/generate-report` reads as plumbing
- partners and customers can integrate against your own stable contract instead of your vendor's URL shape
- rate limiting, audit logging, abuse controls, and route review is clearer.
- migrating vendors later means changing the gateway, not every frontend call site
- you can talk credibly about API ownership and architecture with partners and customers

This template gives you that thin cosmetic API layer without forcing a backend rewrite.

## What is included

- `api-gateway/`: FastAPI app with CORS, settings, bearer-token handling, and explicit routes examples
  - `profile` example: authenticated user-scoped CRUD
  - `functions` example: one named route for one Edge Function
  - `storage` example: public asset passthrough from one allow-listed bucket
- `frontend-example/api-client.ts`: TypeScript client with Supabase-like `{ data, error }`
- `docs/agent-prompt.md`: prompt to hand the migration to Codex, Claude Code, Cursor, or another coding agent

What this is not:

- not a replacement for `supabase-js` Auth or Realtime
- not a generic proxy
- not a full backend framework

## How to use it

Two steps. The AI coding agent does the rest.

### 1. Create a new branch 

I would advise you to create a new branch, that you can later merge with your main branch when everything is migrated and working.

```bash
git checkout -b dev-api
```

### 2. Get the template into your app

From your app's root folder, run:

```bash
git clone https://github.com/Project430/supabase-fastapi-gateway.git
```

### 3. Hand it to your AI coding agent

Open your coding agent (Claude Code, Cursor, Codex, etc.) at your app's root and paste this one line:

```text
Read supabase-fastapi-gateway/docs/agent-prompt.md and follow it end to end.
```

The agent will place the files where they belong, wire up the Supabase environment variables, run the gateway locally, and migrate your Supabase calls one safe domain at a time.


## Security

Read `docs/security-notes.md` before production. The short version: this template is a controlled boundary, not a magic shield. Direct frontend-to-Supabase access with the anon/publishable key is fine when RLS is correctly configured // the things that actually bite are weak RLS, leaking the `service_role` key, and missing rate limiting / logging discipline. 

## Repo layout

```text
api-gateway/
  app/main.py
  app/auth.py
  app/config.py
  app/routes/profile.py
  app/routes/functions.py
  app/routes/storage.py
  app/services/supabase_rest.py
  app/services/supabase_functions.py
  app/services/supabase_storage.py
frontend-example/api-client.ts
docs/
```

## License

MIT. See `LICENSE`.

## Field Test: Lightwheel (V1.2)

- project name: Lightwheel
- result: succeeded
- approximate duration / passes: about 6 passes
- what was improved in this repo after the test: shorter agent prompt, leaner intermediate output, lighter verification flow, fewer docs/comments
- main friction discovered: repeated scans and verbose per-run summaries slowed `Next`-driven migration
- why this repo update was needed: to make repeated migration runs faster, lower-token, and easier to continue
