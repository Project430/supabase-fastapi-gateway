# api-gateway

FastAPI gateway that sits between your frontend and Supabase.

## Setup

```bash
cp .env.example .env
# fill SUPABASE_URL, SUPABASE_ANON_KEY, FRONTEND_ORIGIN

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Smoke test:

```bash
curl http://127.0.0.1:8000/api
```

## Included examples

- `app/routes/profile.py` // authenticated user-scoped CRUD pattern
- `app/routes/functions.py` // one explicit route for one Edge Function
- `app/routes/storage.py` // public asset passthrough from one allow-listed bucket

## Layout

- `app/main.py` // app factory, CORS, router registration
- `app/config.py` // settings loaded from `.env`
- `app/auth.py` // bearer-token extraction + JWT `sub` decoder
- `app/routes/` // explicit route handlers only
- `app/services/` // thin clients for Supabase REST, Edge Functions, and Storage

## Adding a route

1. Create or extend a file in `app/routes/`.
2. Use `Depends(get_bearer_token)` for any route that needs an authenticated user.
3. Use `get_user_id_from_token(token)` if you need the user id and want to scope queries to that user.
4. Register the router in `app/main.py`.

Pattern to follow: route handlers do validation and shape the response, services talk to Supabase. Don't put HTTP calls directly in route handlers.

## What this gateway is not

- It does not store or cache data.
- It does not replace `supabase-js` for Auth, Realtime, or browser-side queries that genuinely belong on the client.
- It does not expose a generic `/proxy/{anything}` route. Every route is named and reviewed.
