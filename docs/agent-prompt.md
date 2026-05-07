# Agent Migration Prompt

Run at the root of the user's app. The template was cloned to `./supabase-fastapi-gateway/`.

Goal: migrate React + Supabase apps to the FastAPI gateway with low token usage and fast repeated `Next` runs. Correctness matters more than commentary.

Do Phases 0-5 in order. Stop only on a hard blocker.

## Working style

- Keep output short.
- The user will usually just type `Next`.
- Intermediate runs should be compact and practical.
- Do not repeat long explanations, plans, or verification summaries.
- Scan only when needed. Reuse prior inventory unless code changed.
- Do not rescan the whole app if prior inventory is still valid.
- Optional: keep one tiny migration-state note only if it clearly avoids repeated scanning.
- Re-run gateway health checks only if gateway code changed.
- Keep auth and realtime on `supabase-js`.
- Migrate only data, functions, and storage calls.
- Use explicit routes only: one route per resource or function.
- No generic proxy routes.
- Do not refactor unrelated code.
- Do not edit the cloned template README or unrelated template docs during app migration.
- Do production deployment readiness only after the migration is complete and working locally.

## Phase 0 // Place files

Move:
- `supabase-fastapi-gateway/api-gateway/` -> `./api-gateway/`
- `supabase-fastapi-gateway/frontend-example/api-client.ts` -> `./src/lib/api-client.ts`
- `supabase-fastapi-gateway/docs/` -> `./docs/api-gateway/`

If `./api-gateway/` already exists, ask before overwriting.

After the required moves, inspect what is left in `supabase-fastapi-gateway/`:
- if only template leftovers remain, such as `.git`, `README*`, `LICENSE*`, `.gitignore`, or similar template metadata, remove them and then remove the folder
- also remove starter-only example folders or files that are no longer needed after the required moves, but only if they clearly came from the template
- do not delete anything that looks like user app code, user content, or anything you did not just clone from the template
- if unsure whether a leftover is template-only, stop and ask once

## Phase 1 // Configure env

```bash
cd api-gateway && cp .env.example .env
```

Fill from existing app env files:
- `SUPABASE_URL` or `VITE_SUPABASE_URL`
- `SUPABASE_ANON_KEY` or `VITE_SUPABASE_ANON_KEY` or `SUPABASE_PUBLISHABLE_KEY`

Detect the frontend dev origin the app is actually using before filling `FRONTEND_ORIGIN`:
- check existing app env files, package scripts, Vite config, Next config, Docker/devcontainer config, or other local dev config
- do not assume `http://localhost:5173` or any other default port
- use the real frontend dev origin if it is discoverable, such as `http://localhost:8080`
- if the configured origin appears wrong for the current app, update it or clearly tell the user what to change
- do not force the user to change how the frontend is started just to match the gateway

Then fill:
- `FRONTEND_ORIGIN`

Add frontend API URL with the app's env prefix:

```text
VITE_API_URL=http://localhost:8000
```

If a value is still missing after one focused search, ask once. Never put `service_role` in the frontend.

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
- Migration is not complete until both direct and indirect Supabase usage paths were checked.

Scan for:
- `supabase.functions.invoke(`
- `supabase.from(`
- `supabase.storage.`
- `/functions/v1/`
- `/rest/v1/`
- `/storage/v1/`
- imports/usages of shared helpers or wrappers such as `supabaseClient`, `integrations/supabase/client`, shared hooks, services, helpers, or clients that may hide Supabase access

If direct matches are sparse, inspect the shared helper layer before declaring the app done.

Build inventory by area with:
- kind: `data` | `functions` | `storage`
- files
- call count
- note whether usage is direct or hidden behind a shared helper

No-op path:
- if the inventory confirms no direct or indirect frontend data/function/storage usage to migrate, still complete Phases 0, 1, 2, and 4
- confirm the inventory is empty
- finish cleanly without inventing migration work

Per run:
1. Pick a safe chunk from the inventory.
2. Add route files under `api-gateway/app/routes/` and register them in `app/main.py`.
3. Use `supabase_rest`, `supabase_functions`, and `supabase_storage`.
4. Authenticated routes must use `Depends(get_bearer_token)`.
5. Public routes may allow anon access; if a bearer token is present and useful, it may still be forwarded upstream.
6. User-scoped routes must read user id from the bearer token, not the body.
7. Route shape: collection read `GET /v1/posts`; single resource read `GET /v1/posts/{slug}`; use named action routes only when truly function-like; user-scoped read/write routes require bearer token and user id from token.
8. Update frontend call sites through `src/lib/api-client.ts`.
9. Remove obsolete frontend Supabase helper/wrapper files only when they are no longer used and safe to delete.
10. Run only minimal checks for the changed chunk.

Intermediate verification:
- prefer existing project build/typecheck/lint commands over inventing new checks
- `build` is often a better final lightweight confidence check than noisy lint
- confirm changed files still pass the lightest relevant existing check
- confirm migrated calls no longer hit direct Supabase URLs
- if gateway startup fails specifically because of `--reload` watcher or environment permission issues, retry without `--reload`
- do not print long verification notes

When all migration work is complete:
- run the stronger final verification pass
- re-scan once to confirm no remaining direct data/function/storage calls
- confirm shared helpers/wrappers/hooks no longer hide remaining Supabase data/function/storage usage
- run the broader health checks
- remove template-only leftovers that are no longer needed after migration, including starter markdown files, example folders, and temporary documentation assets that came from the template and are no longer useful in the migrated app
- examples of removable template-only leftovers may include `docs/agent-prompt.md`, `docs/assets/Exemple-api-doc.png`, unused starter example folders, and other template guidance files or images that were only meant to bootstrap the migration
- do not delete docs, markdown files, or examples that the user appears to have edited, adopted, or kept for real project use
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
<one closing line chosen by state>
```

Use plain-English area labels only. If a category is done, write `0 files // none`.

Closing line rules:
- if migration work is still left, write `Type "Next" to continue.`
- if the listed migration work is done but a broader repo scan is the logical next step, write `next step: run a wider scan for any remaining direct Supabase usage`
- if everything has been checked, template-only leftovers have been cleaned up, and there is truly nothing left to migrate, write `all done, you can commit`

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
all done, you can commit
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

## Phase 5 // Production deployment readiness

When the local migration is complete and working, prepare the gateway for production deployment.

First detect the intended host:
- `Vercel`
- `VPS / Docker / Nginx`
- `Railway`
- `Fly.io`
- `AWS`
- `unknown`

Do not assume the same setup for every project.
If the host is not clear from the repo or deployment config, ask the user what he is using before setting up deployment files.

If using `Vercel`:
- create or verify a Vercel-compatible FastAPI entrypoint
- use `api-gateway` as the API project Root Directory
- add `vercel.json` only if required
- ensure `/health` works publicly
- ensure production rewrites do not expose docs directly

Production security:
- never expose `/docs`, `/redoc`, or `/openapi.json` publicly
- keep docs available locally only
- use `ENVIRONMENT=production` to disable public docs

Deployment guidance:
- recommend a separate deployment project for the API gateway
- explain branch tracking if the user is deploying from a migration branch
- ask the user if he needs guidance for this setup part
