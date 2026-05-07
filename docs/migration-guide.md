# Migration guide

Manual version of the same fast workflow the AI agent should follow.

Goal: move selected Supabase calls behind the gateway without rewriting
the app. Keep Auth, Realtime, and browser-native flows on
`supabase-js`.

## Step 1. Install the gateway next to your app

You have two options:

- Terminal: copy the files and folders with commands
- Drag and drop: manually move `api-gateway/`, `frontend-example/api-client.ts`, and `docs/` into your app project

Terminal version from your existing project root:

```bash
cp -R /path/to/supabase-fastapi-gateway/api-gateway   ./
cp /path/to/supabase-fastapi-gateway/frontend-example/api-client.ts \
   ./src/lib/api-client.ts
mkdir -p ./docs/api-gateway
cp -R /path/to/supabase-fastapi-gateway/docs/* ./docs/api-gateway/
```

After that, open your coding agent in your real app repo and paste:

```text
docs/api-gateway/agent-prompt.md
```

The agent should do a quick scan, pick the safest first domain, and
implement it without turning the migration into a long audit exercise.

Configure environment:

```bash
cd api-gateway
cp .env.example .env
# fill SUPABASE_URL, SUPABASE_ANON_KEY, FRONTEND_ORIGIN
```

Frontend `.env`:

```
VITE_API_URL=http://localhost:8000
```

Run it:

```bash
cd api-gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl http://127.0.0.1:8000/api
```

If your app sets a Content Security Policy, add `http://localhost:8000` (and later your production gateway URL) to `connect-src`.

---

## Step 2. Analyze quickly

Do a fast scan to find migration candidates. Run these from the repo
root:

```bash
grep -rn "supabase.functions.invoke" src/
grep -rn "supabase.from(" src/
grep -rn "supabase.storage" src/
grep -rn "supabase.channel(" src/
grep -rn "supabase.co" src/
```

You do not need a full spreadsheet or a long written plan. Just figure
out the smallest safe first slice and move it.

---

## Step 3. Implement the first domain, or a few tiny safe ones

Choose a domain where:

- the calls are simple CRUD on user-owned rows,
- there is no Realtime, no streaming, no file upload involved,
- there are roughly ≤ 10 call sites.

Good first picks: profile, user preferences, notes, feedback, settings.

Avoid first: billing, payments, anything authenticated with extra Stripe
webhooks, anything that streams, anything that uploads files.

You can batch 2-3 tiny low-risk domains in one run if they are clearly
independent and still easy to verify together. Do not batch broad or
high-risk domains.

Then implement immediately.

---

## Step 4. Add the gateway routes

Open `api-gateway/app/routes/` and follow the patterns in `profile.py`, `functions.py`, and `storage.py`:

1. Use `Depends(get_bearer_token)` for authenticated routes.
2. Read the user id from the token with `get_user_id_from_token(token)` for user-scoped queries. Never trust a user id sent in the request body.
3. Validate input with a `pydantic.BaseModel` and `model_config = {"extra": "forbid"}`.
4. Talk to Supabase only through `app/services/supabase_rest.py`, `supabase_functions.py`, or `supabase_storage.py`.
5. Register the new router in `app/main.py`.

For each Edge Function you want to expose, add **one named route** (e.g. `POST /v1/billing/create-checkout`). Do not add a generic catch-all route.

Keep route names simple and resource-oriented. Good examples:

- `GET /v1/profile`
- `PATCH /v1/profile`
- `POST /v1/contact`
- `GET /v1/reviews`
- `POST /v1/newsletter`

Avoid verbose function-like names such as:

- `/v1/get-user-profile-data`
- `/v1/create-newsletter-subscription-entry`
- `/v1/fetch-all-published-reviews`

---

## Step 5. Replace the frontend calls

In `src/lib/api-client.ts` (the helper you copied) you have a `createApiClient` factory. Wire it up once, e.g. in `src/lib/api.ts`:

```ts
import { supabase } from "@/integrations/supabase/client";
import { createApiClient } from "@/lib/api-client";

export const api = createApiClient({
  baseUrl: import.meta.env.VITE_API_URL,
  getAccessToken: async () => {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  },
});
```

Then, in each call site for the chosen domain, swap the call:

```ts
// Before
const { data, error } = await supabase
  .from("profiles")
  .select("*")
  .eq("user_id", userId)
  .single();

// After
const { data, error } = await api.get<Profile>("/v1/profile");
```

```ts
// Before
const { data, error } = await supabase.functions.invoke("example-function", {
  body: { input_text },
});

// After
const { data, error } = await api.post<ExampleResponse>("/v1/functions/example", {
  body: { input_text },
});
```

Keep `{ data, error }` destructuring identical so your React components don't change.

---

## Step 6. Verify

- `curl http://127.0.0.1:8000/api` returns `{"status":"ok"}`.
- Open the migrated screen in the app. In DevTools → Network, the migrated calls should hit `localhost:8000` (or your gateway domain), not `*.supabase.co`. Auth and any remaining Realtime calls should still hit `*.supabase.co` // that's correct.
- Run `npm run typecheck` and `npm run lint` (or your project's equivalent).

---

## Step 7. Recheck once or twice, then move on

After implementation, do one or two quick rechecks for leftover calls in
the same migrated domain or domains. Clean up anything obvious, then
stop. Do not get stuck in a loop of endlessly rescanning.

Then move to the next-easiest domain. Small PRs are still better than
"migrate everything" PRs, because they are reviewable and easier to
revert.

When the agent finishes a run, the final response should be minimal. Do
not ask it for a long summary of what changed. The file diff already
shows that. Only surface blockers, required user action, or the next
useful domain if needed.

---

## Common pitfalls

- **PostgREST returns arrays even for single rows.** When you migrated a `.single()` call, your gateway route should return the first element (`rows[0]`) or a 404 if missing. The `profile.py` example does this.
- **`PATCH` with no body fields.** PostgREST happily updates zero columns and returns 200. The `profile.py` example explicitly rejects this with 400.
- **CORS errors after deploying.** Update `FRONTEND_ORIGIN` to the production frontend origin (no trailing slash).
- **CSP errors in production.** Add the production gateway URL to your `connect-src` directive.
- **`auth.uid()` returning `null` inside an Edge Function or RLS check.** You forgot to forward the bearer token in the gateway route. Every authenticated route must call the upstream with `Authorization: Bearer <token>` // the helpers in `app/services/` already do this when you pass `token=`.
