# meterly: usage metering and billing engine

FlyRank backend capstone. Meters usage exactly once, enforces plan quotas, calculates cost in integer micro-dollars, and syncs plans from Stripe test mode through verified, deduplicated webhooks.

## Architecture

```
Client -> POST /generate (Idempotency-Key, X-Tenant-Id)
            -> MeterService.record
               | lock tenant row (FOR UPDATE)
               | key seen before? -> return original (replayed: true)
               | subscription inactive? -> 402
               | usage + request > limit? -> 429 + Retry-After
               | insert usage_event (UNIQUE tenant_id, idempotency_key)
GET /usage  <- rollup(usage_events) -> used, limit, cost
POST /checkout -> Stripe Checkout (test mode)
Stripe --signed webhook--> POST /webhooks/stripe
               | bad signature -> 400, nothing written
               | event id already in stripe_events -> ignored (200)
               | one transaction: claim event + update plan
               | failure -> failed_webhooks, retried by background job
```

Layers: `routers` (HTTP) -> `services` (rules) -> `repositories` (SQL). Migrations via Alembic.

## Plans

| Plan | API calls / month | AI tokens / month |
|---|---|---|
| Free | 1,000 | 100,000 |
| Pro | 50,000 | 5,000,000 |

## Pricing (micro-dollars, 1 USD = 1,000,000)

API call 1,000 each. Per 1M tokens: fresh input 300,000, cached input 75,000, output 2,500,000. Reasoning tokens bill at the output rate. All money is integer math, rounded once.

## Quota rule

Reaching exactly the limit is allowed. The next request returns 429 (active plan, quota used) or 402 (lapsed subscription). Rejected requests record nothing.

## Run

```
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --port 8000
```

Fill `.env` with your Stripe test-mode key, price ID and webhook secret (`stripe listen --events checkout.session.completed,customer.subscription.updated,customer.subscription.deleted --forward-to localhost:8000/webhooks/stripe`).

Tests: `python -m pytest tests -q` (needs the database running).

## Limitations

Stripe test mode only. No invoicing, proration or overage billing. Tenant identity comes from the `X-Tenant-Id` header with no authentication. The retry job is an in-process thread, not a separate worker.