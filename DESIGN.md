# Design: Usage Metering & Billing Engine

## Problem
A backend service that answers three questions for each tenant: how much have they used, what does it cost, and have they hit their plan limit. It meters usage exactly once per request, enforces quotas before the action, calculates cost, and mirrors subscription state from Stripe test mode.

## Data model
All money is stored as integer micro-dollars (1 USD = 1,000,000) in BIGINT columns. No floats anywhere.

| Table | Columns |
|---|---|
| tenants | id (PK), name, plan_id (FK), subscription_status, stripe_customer_id, created_at |
| plans | id (PK), name, api_calls_limit, ai_tokens_limit |
| subscriptions | id (PK), tenant_id (FK), stripe_subscription_id (unique), status, current_period_end |
| usage_events | id (PK), tenant_id (FK), type (api_call / ai_tokens), quantity, input_tokens, cached_input_tokens, output_tokens, reasoning_tokens, cost_micros, request_hash, idempotency_key, created_at |
| stripe_events | event_id (PK, `evt_...`), type, processed_at |

Constraints and indexes:
- `UNIQUE (tenant_id, idempotency_key)` on usage_events
- Index on `usage_events (tenant_id, created_at)` for monthly rollups

Seed plans: Free = 1,000 calls and 100k tokens per month. Pro = 50,000 calls and 5M tokens per month.

Pricing constants live in config, as micro-dollars:
- API call: 1,000 per call
- Input tokens: 300,000 per 1M
- Cached input tokens: 75,000 per 1M
- Output tokens: 2,500,000 per 1M
- Reasoning tokens: billed at the output rate

Cost = (fresh input x input rate + cached x cached rate + (output + reasoning) x output rate) / 1,000,000, in integer math, rounded once at the end. Fresh input = total input minus cached input.

## API surface
| Method | Path | Purpose |
|---|---|---|
| POST | /generate | Dummy billable endpoint. Needs `Idempotency-Key` and `X-Tenant-Id` headers. Records usage, checks quota, returns cost. |
| GET | /usage | Rollup for the current month: used, limit, cost. |
| POST | /checkout | Creates a Stripe Checkout session for Pro. |
| POST | /webhooks/stripe | Signature-verified, deduplicated plan sync. |
| GET | /health | Liveness check. |

## Idempotency
- The unique constraint on `(tenant_id, idempotency_key)` plus `INSERT ... ON CONFLICT DO NOTHING` decides the winner, so two simultaneous requests cannot both insert.
- If the insert returns no row, the original event is fetched and the original response is returned. No new event.
- `request_hash` is compared on a replay. Same key with a different body returns 422.

## Quota rule
- Check: current usage + requested quantity vs plan limit, inside the same transaction as the insert.
- Reaching exactly the limit is allowed. At 1,000 of 1,000 calls, request 1,000 succeeds and request 1,001 is rejected.
- 429 Too Many Requests: active plan, quota exhausted. Body includes used, limit, and a message to upgrade.
- 402 Payment Required: subscription lapsed or unpaid.
- Rejected requests record no usage.

## Webhooks
1. Verify the signature against the raw body. Forged returns 400 and nothing is written.
2. In one transaction, insert the event id into `stripe_events` and apply the plan/status update.
3. If the insert conflicts, the event is a repeat. Skip it and return 200.
Handled events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`.

## Layers
- **HTTP (routers):** parse and validate requests, map errors to status codes, no business logic.
- **Logic (services):** MeterService, QuotaService, PricingService, BillingService. Pure rules, no SQL.
- **Data (repositories):** SQL and transactions only. Migrations via Alembic.
- **Background job:** failed webhook processing is retried with a failure log.

## Secrets
Stripe API key and `whsec_` secret live in `.env` only, are git-ignored, are never logged, and are listed with placeholders in `.env.example`.

## Non-goal
No invoicing, proration, or overage billing in the core build. These stay as stretch goals.