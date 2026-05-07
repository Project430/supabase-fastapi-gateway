# Agent Migration Prompt

Run at the root of the user's app. The template was just cloned to `./supabase-fastapi-gateway/`.

Execute Phases 0–4 in order. Stop only on a hard blocker.

---

## How to work

- Be terse. No step-by-step narration between tool calls, no "I'm going to…" / "Now I'm…" updates. Run the work, then report results once at the end.
- Don't add explanatory comments to migrated code. The route name and the typed client function are the documentation.
- Don't refactor, rename, or "tidy" anything outside the migration scope.
- Batch tool calls when they're independent (scans, reads, file moves).
- One full-repo scan in Phase 3, not one scan per domain.

---

## Phase 0 // Place files

Move:
- `supabase-fastapi-gateway/api-gateway/` → `./api-gateway/`
- `supabase-fastapi-gateway/frontend-example/api-client.ts` → `./src/lib/api-client.ts`
- `supabase-fastapi-gateway/docs/` → `./docs/api-gateway/`

Delete the empty `supabase-fastapi-gateway/` folder. If `./api-gateway/` already exists, ask before overwriting.

---

## Phase 1 // Configure env

```bash
cd api-gateway && cp .env.example .env
```

Fill from existing app env files (search once each):
- `SUPABASE_URL` // also `VITE_SUPABASE_URL`
- `SUPABASE_ANON_KEY` // also `VITE_SUPABASE_ANON_KEY`, `SUPABASE_PUBLISHABLE_KEY`
- `FRONTEND_ORIGIN` // Vite: `http://localhost:5173`, Next.js: `http://localhost:3000`

In the frontend env file (use the framework's prefix // `VITE_`, `NEXT_PUBLIC_`, `REACT_APP_`), add:
```
VITE_API_URL=http://localhost:8000
```

If a value is missing after one search, ask the user once. Never put `service_role` in the frontend.

---

## Phase 2 // Verify gateway (once per session)

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
```

Confirm `GET http://127.0.0.1:8000/api` returns `{"status":"ok"}`. Skip this phase on subsequent runs if the gateway is unchanged.

---

## Phase 3 // Migrate

**Rules:**
- Keep Auth and Realtime on `supabase-js`. Move only data/function/storage calls.
- Every migrated call uses an explicit named route. No generic proxies.
- Frontend response shape stays `{ data, error }`.
- Don't weaken RLS, move secrets to the frontend, or refactor unrelated files.
- If a domain is centralized in a shared hook/helper, migrate there // not in every component.

**Workflow:**

1. **Scan `src/` once, end to end** for all of:
   - `supabase.functions.invoke(`
   - `supabase.from(`
   - `supabase.storage.`
   - `/functions/v1/`, `/rest/v1/`, `/storage/v1/`

   Group every hit into domains (a domain = one product area, e.g. all profile calls, all the calls behind one feature). Build an inventory: `{ domain → { kind: data|functions|storage, files: […], call_count: N } }`. This inventory drives the rest of the phase and the final report.

2. **Migrate a meaningful chunk in one run.** Pick 2–4 related low-risk domains from the inventory and migrate them together. Skip: auth, billing, admin, file-heavy flows, anything with cross-cutting RLS implications. A "chunk" is finished when every call in those domains goes through the gateway.

   Tiny domains (1 file, 1 call) should never be migrated alone // fold them into a chunk with related work.

3. **Implement (per domain in the chunk):**
   - Add route(s) under `api-gateway/app/routes/`, register in `app/main.py`.
   - Use helpers: `supabase_rest`, `supabase_functions`, `supabase_storage`.
   - Authenticated routes: `Depends(get_bearer_token)`; user id from `get_user_id_from_token`, never from the body.
   - Resource-style paths (e.g. `POST /v1/<resource>`).
   - Update only that domain's frontend calls through `src/lib/api-client.ts`.
   - No new code comments.

4. **Verify (once, at end of chunk):**
   - Typecheck passes.
   - Migrated calls no longer hit `*.supabase.co`.
   - Lint changed files; full lint once at end of session.

**Final output (this exact format, replacing the inventory with the user's actual one):**

```
migrated this run:
- <domain> (<kind>, <N> calls across <M> files)
- <domain> (<kind>, <N> calls across <M> files)

remaining:
- data:      <N domains> / <M files>  // <short list of domain names>
- functions: <N domains> / <M files>  // <short list of domain names>
- storage:   <N domains> / <M files>  // <short list of domain names>

kept on supabase-js: auth, realtime[, …]
estimated runs left: <N>  (assume 2–4 domains per run)
```

If `remaining` is empty in a kind, write `none`. The remaining block is what the user reads to see how close the migration is to done // group, don't enumerate every file.

---

## Phase 4 // Leave a rules file for future agents

Create `docs/api-gateway/AGENTS.md` with:

```markdown
# Coding rules for this app

Frontend talks to a FastAPI gateway in front of Supabase for data, functions, and storage.

- No new Supabase Edge Functions // add a route under `api-gateway/app/routes/`.
- No direct `supabase.from(...)`, `supabase.functions.invoke(...)`, or `supabase.storage.*` in frontend code.
- Always go through `src/lib/api-client.ts`. If a call doesn't exist, add the gateway route first.
- Auth and Realtime stay on `supabase-js`.
- Resource-style routes only (e.g. `/v1/profile`).
- `service_role` never enters the frontend.
- User-scoped routes read user id from the bearer token, never from the body.

Add-feature flow: add route → register in `app/main.py` → add typed function in `api-client.ts` → call from frontend.

If direct Supabase data/function/storage calls appear in the frontend, migrate them.
```

Then add to repo-root `CLAUDE.md` and/or `AGENTS.md` (create a root `AGENTS.md` if neither exists):

> Before adding any feature that touches Supabase, read `docs/api-gateway/AGENTS.md`.

Don't duplicate the ruleset across files.
