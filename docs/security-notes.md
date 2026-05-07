# Security notes

This gateway improves your security posture only if you keep it explicit and reviewable. If you turn it into a transparent proxy, you lose most of the benefit.

## What this template gives you now

- **Single trusted origin.** CORS allows exactly one frontend origin (`FRONTEND_ORIGIN`). No wildcards.
- **Bearer-token enforcement.** Authenticated routes use `Depends(get_bearer_token)`. No silent fallthrough on missing or malformed `Authorization` headers.
- **User id is read from the token, not the body.** `get_user_id_from_token()` extracts `sub` from the JWT payload. Routes that need to scope queries to a user use it; they never accept a `user_id` in JSON.
- **Strict request validation.** Pydantic models use `extra = "forbid"` so unknown fields are rejected.
- **Path-traversal block on storage.** The `/v1/storage/public/...` route refuses paths that contain `..` segments.
- **No generic proxy route.** Every exposed Supabase call is a named handler.
- **Anon key only.** The template never asks for the Supabase service-role key. RLS policies on Supabase decide what each user can read or write.

## What you still need before production

### 1. JWT verification

This template **does not** cryptographically verify the JWT at the gateway. It decodes the payload to extract `sub` for query scoping, but Supabase is the source of truth for token validity. That is fine when:

- the gateway always forwards the token to Supabase, and
- Supabase rejects expired or tampered tokens.

It is **not** fine if you add a route that does useful work without calling Supabase. For those routes, verify the token against Supabase's JWKS using `python-jose` or `authlib`.

### 2. Rate limiting and abuse protection

There is no rate limiting in the template. For a public gateway, add at minimum:

- IP-based rate limiting (e.g. `slowapi`, or your reverse proxy / CDN).
- Per-user rate limiting on expensive routes (anything that triggers an LLM call, an email, a PDF generation).
- A request body size limit (FastAPI default is generous; clamp it via your reverse proxy).

### 3. Logging and observability

Decide what you log and what you do not. **Never log:**

- bearer tokens, even partially,
- request bodies that may contain personal data,
- the Supabase anon key.

Do log: method, path, status code, latency, and a hashed user id if you need to correlate. Send logs to a destination outside the gateway host.

### 4. Production secrets

- The `.env` file is for local dev only. In production, inject `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `FRONTEND_ORIGIN` via your platform's secret manager (Fly, Render, Scalingo, AWS Parameter Store, etc.).
- Add `.env` to `.gitignore` (this template already does, but double-check after copying).
- Rotate the anon key if it ever appears in a screenshot, blog post, or commit history. Rotate the *service-role* key immediately if it leaks anywhere // it bypasses RLS.

### 5. Service-role key, only if you must

If you genuinely need admin access for a specific route (server-side cron, GDPR export, admin tooling), introduce a `SUPABASE_SERVICE_ROLE_KEY` env variable, but:

- never read it from a route that's reachable by an end-user without an extra authorization check,
- document in the route's docstring why it needs admin access,
- ideally split admin routes into a separate gateway deployment that is not exposed to the public internet.

### 6. Frontend CSP

Update your frontend Content Security Policy `connect-src` to include the gateway URL (and **remove** any `*.supabase.co` entry that's no longer needed). Two example states:

```
# during migration: both gateway and Supabase
connect-src 'self' http://localhost:8000 https://api.your-domain.com https://*.supabase.co wss://*.supabase.co;

# end state: only gateway + Realtime/Auth on Supabase
connect-src 'self' https://api.your-domain.com wss://*.supabase.co;
```

### 7. Remove old frontend Supabase calls

Migrating a route does not remove the original `supabase.functions.invoke("foo")` call automatically. Once a route is fully behind the gateway:

- search the repo for the old function name to make sure no caller is left,
- consider revoking the corresponding Edge Function from public invocation if Supabase exposes that toggle, so an attacker can't call it directly bypassing the gateway.

### 8. Storage privacy

The `/v1/storage/public/...` route only serves files from a single allow-listed public bucket. **Do not** generalize this route to accept a bucket parameter, and do not point it at a private bucket. For private files, write a separate route that:

- authenticates the caller,
- checks they are allowed to read the specific object,
- asks Supabase Storage for a short-lived signed URL,
- either redirects the caller to that URL or streams it server-side.

---

## Production checklist

- [ ] `FRONTEND_ORIGIN` set to the production frontend URL, no trailing slash.
- [ ] Secrets injected via the platform's secret manager, not committed.
- [ ] CSP `connect-src` updated.
- [ ] Rate limiting in place at the gateway or reverse proxy.
- [ ] Logging excludes tokens and PII.
- [ ] No `service-role` key exposed to public routes.
- [ ] Old `supabase.functions.invoke(...)` calls removed for migrated functions.
- [ ] API check wired to your platform's uptime checks.
