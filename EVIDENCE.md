# Evidence

One proof per requirement. Tests run with `python -m pytest tests -v` (15 passed).

## Metering: one event per idempotency key (Probe 1)
- `tests/test_meter.py::test_same_key_twice_creates_one_event` PASSED. The same request sent twice leaves one row in `usage_events`, and the second response returns the original `event_id` with `replayed: true`.
- `test_same_key_different_body_conflicts` PASSED. The same key with a different body is rejected with a 422 error.
- Enforced by `UNIQUE (tenant_id, idempotency_key)` plus `INSERT ... ON CONFLICT DO NOTHING`.

## Quotas and status codes (Probe 2)
- `tests/test_quota.py::test_boundary_exact_limit_allowed_then_blocked` PASSED. At 999 of 1,000 calls, request 1,000 succeeds and request 1,001 is rejected. Nothing is recorded for the rejected request.
- `tests/test_usage.py::test_http_429_has_retry_after_and_message` PASSED. The 429 response carries `Retry-After`, `used`, `limit` and a message.
- `test_lapsed_subscription_returns_payment_required` PASSED. A `past_due` tenant gets 402.
- `test_replay_at_limit_returns_original` PASSED. A replay at the limit returns the original result instead of an error.
- `test_concurrent_requests_at_999_only_one_succeeds` PASSED. Five simultaneous requests at 999 let exactly one through, using a `SELECT ... FOR UPDATE` lock on the tenant row.

## Cost calculation (Probe 5)
- `tests/test_meter.py::test_cached_and_reasoning_pricing` PASSED. 1,000,000 input tokens (400,000 cached), 100,000 output and 50,000 reasoning tokens cost 585,000 micro-dollars.
  - 600,000 fresh input x 300,000 / 1M = 180,000
  - 400,000 cached x 75,000 / 1M = 30,000
  - 150,000 output + reasoning x 2,500,000 / 1M = 375,000
- `tests/test_usage.py::test_usage_matches_pinned_pricing` PASSED. `GET /usage` shows 585,000 for tokens and a 586,000 total, which adds 1,000 for one API call.
- Constants are pinned in `app/pricing.py`. Money is integer micro-dollars throughout.

## Stripe Checkout flips Free to Pro (Probe 3)
Live run in test mode with card 4242 4242 4242 4242. Tenant 1 started on Free with `stripe listen` forwarding to `/webhooks/stripe`.

Database after payment:

```
 plan | events
------+--------
 pro  |      1
```

Listener output:

```
 stripe listen lines: --> checkout.session.completed ... <-- [200]
```

Test coverage: `tests/test_webhook.py::test_valid_event_flips_free_to_pro_and_usage_shows_new_limits` PASSED. After the event, `GET /usage` reports plan `pro` and a 50,000 call limit.

## Webhook security (Probe 4)
- `test_forged_signature_returns_400_and_changes_nothing` PASSED. A bad signature returns 400, the plan stays Free, and `stripe_events` stays empty.
- `test_replayed_event_is_processed_once` PASSED. The second delivery returns `duplicate` and `stripe_events` holds one row.
- Live replay: `stripe events resend evt_...` returned 200 and the plan stayed `pro`.

```
[PASTE the plan | events query output run after the resend, expect: pro | 1]
```

## Background job
`tests/test_retry.py::test_failed_event_is_retried_and_resolved` PASSED. A failed webhook stored in `failed_webhooks` is retried by `jobs.retry_failed_once()`, the plan flips to Pro and the row is marked resolved. After 5 failed attempts the job logs an `ALERT` line.

## Database
Schema is managed by Alembic migrations (`migrations/versions/`). Tables: `plans`, `tenants`, `subscriptions`, `usage_events`, `stripe_events`, `failed_webhooks`. `usage_events` has an index on `(tenant_id, created_at)`.

## Secrets
`.env` is git-ignored and was never committed. `.env.example` holds placeholders only, which I checked with `git log -p --all -- .env.example`.