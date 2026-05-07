# Agent Migration Prompt

Run at the root of the user's app. The template was cloned to `./supabase-fastapi-gateway/`.

Goal: migrate React + Supabase apps to the FastAPI gateway with low token usage and fast repeated `Next` runs. Correctness matters more than commentary.

Do Phases 0-4 in order. Stop only on a hard blocker.

## Working style

- Keep output short.
- The user will usually just type `Next`.
- Intermediate runs should be compact and practical.
- Do not repeat long explanations, plans, or verification summaries.
- Scan only when needed. Reuse prior inventory unless code changed.
- Re-run gateway health checks only if gateway code changed.
- Keep auth and realtime on `supabase-js`.
- Migrate only data, functions, and storage calls.
- Use explicit routes only: one route per resource or function.
- No generic proxy routes.
- Do not refactor unrelated code.

## Phase 0 // Place files

Move:
- `supabase-fastapi-gateway/api-gateway/` -> `./api-gateway/`
- `supabase-fastapi-gateway/frontend-example/api-client.ts` -> `./src/lib/api-client.ts`
- `supabase-fastapi-gateway/docs/` -> `./docs/api-gateway/`

Delete the empty `supabase-fastapi-gateway/` folder. If `./api-gateway/` already exists, ask before overwriting.

## Phase 1 // Configure env

```bash
cd api-gateway && cp .env.example .env
```

Fill from existing app env files:
- `SUPABASE_URL` or `VITE_SUPABASE_URL`
- `SUPABASE_ANON_KEY` or `VITE_SUPABASE_ANON_KEY` or `SUPABASE_PUBLISHABLE_KEY`
- `FRONTEND_ORIGIN`

Add frontend API URL with the app's env prefix:

```text
VITE_API_URL=http://localhost:8000
```

If a value is still missing after one search, ask once. Never put `service_role` in the frontend.

## Phase 2 // Verify gateway

Run once per session, or again only if gateway code changed:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
```

Confirm:

```text
GET http://127.0.0.1:8000/api -> {"status":"ok"}
```

## Phase 3 // Migrate

Rules:
- One inventory-based scan of `src/` when needed.
- Migrate a meaningful chunk each run.
- Small related areas can be batched together.
- If an area is centralized in a shared helper or hook, migrate it there.
- Frontend response shape stays `{ data, error }`.
- Do not weaken RLS or move secrets client-side.

Scan for:
- `supabase.functions.invoke(`
- `supabase.from(`
- `supabase.storage.`
- `/functions/v1/`
- `/rest/v1/`
- `/storage/v1/`

Build inventory by area with:
- kind: `data` | `functions` | `storage`
- files
- call count

Per run:
1. Pick a safe chunk from the inventory.
2. Add route files under `api-gateway/app/routes/` and register them in `app/main.py`.
3. Use `supabase_rest`, `supabase_functions`, and `supabase_storage`.
4. Authenticated routes must use `Depends(get_bearer_token)`.
5. User-scoped routes must read user id from the bearer token, not the body.
6. Update frontend call sites through `src/lib/api-client.ts`.
7. Run only minimal checks for the changed chunk.

Intermediate verification:
- confirm changed files still typecheck or lint if that project already has those commands
- confirm migrated calls no longer hit direct Supabase URLs
- do not print long verification notes

When all migration work is complete:
- run the stronger final verification pass
- re-scan once to confirm no remaining direct data/function/storage calls
- run the broader health checks
- say migration is complete

## Per-run final output

Intermediate runs:

```text
<one short sentence saying what was done.>

migrated this run:
- <area label>
- <area label>

remaining:
- data: <N files> // <short labels>
- functions: <N files> // <short labels>
- storage: <N files> // <short labels>

estimated runs left: <N>
Type "Next" to continue.
```

Use plain-English area labels only. If a category is done, write `0 files // none`.

Final complete run:

```text
Migration is complete.

migrated this run:
- <area label>

remaining:
- data: 0 files // none
- functions: 0 files // none
- storage: 0 files // none

estimated runs left: 0
```

## Phase 4 // Leave a rules file

Create `docs/api-gateway/AGENTS.md` with:

```markdown
# Coding rules for this app

Frontend talks to a FastAPI gateway in front of Supabase for data, functions, and storage.

- No new Supabase Edge Functions; add a route under `api-gateway/app/routes/`.
- No direct `supabase.from(...)`, `supabase.functions.invoke(...)`, or `supabase.storage.*` in frontend code.
- Always go through `src/lib/api-client.ts`.
- Auth and Realtime stay on `supabase-js`.
- Resource-style routes only.
- `service_role` never enters the frontend.
- User-scoped routes read user id from the bearer token, never from the body.
```

Then add to repo-root `CLAUDE.md` and/or `AGENTS.md`:

```text
Before adding any feature that touches Supabase, read docs/api-gateway/AGENTS.md.
```
