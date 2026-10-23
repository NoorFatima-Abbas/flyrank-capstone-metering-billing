# Build log

I built this capstone project hands-on, writing and debugging the core logic, architecture fixes, and test suites myself. I used an AI assistant only for generating initial boilerplate scaffolding, migration templates, and syntax references, while taking full responsibility for testing, resolving edge cases, and verifying every component locally.

## Architectural Ownership & Implementation
- **Core Architecture & Schema:** Designed and verified the database schema, Alembic migration flows, and transactional boundaries.
- **Metering & Concurrency:** Implemented `MeterService`, custom quota enforcement using `SELECT ... FOR UPDATE` row locks to prevent race conditions at limits, pricing calculations, and the `/usage` rollup endpoints.
- **Billing & Webhooks:** Configured Stripe Checkout integration, webhook signature verification, payload handling, and the background retry jobs for failed events.
- **Testing & Verification:** Authored, refactored, and executed the comprehensive test suite (`pytest`) to validate edge cases across idempotency, quotas, pricing tiers, and webhook replays.

## Technical Hurdles Overcome & Self-Authored Fixes
- **Pricing Assertion Correction:** Discovered a discrepancy in a pricing test where the assertion expected `595,000` micro-dollars instead of the correct calculation of `585,000`. Verified the pricing math manually and corrected the test expectation.
- **Alembic `env.py` Scope Fix:** Fixed a `NameError` caused by `config.set_main_option(...)` being placed prior to `config = context.config` initialization; repositioned the statements correctly.
- **Database Driver Configuration:** Resolved SQLAlchemy connection issues by explicitly configuring the driver connection string from `postgresql://` to `postgresql+psycopg2://` to match the installed environment packages.
- **Test Plan Tier Correction:** Investigated a 429 quota failure on a large token request, identifying that the test was executing against a Free tier tenant instead of a Pro tier tenant, and re-allocated it properly.
- **Foreign Key Cleanup & Fixtures:** Resolved foreign key violation errors during test teardowns (where `DELETE FROM tenants` failed due to lingering `subscriptions` data) by writing a centralized `tests/conftest.py` fixture to clean tables in the correct relational order before each test run.
- **Table Count Verification:** Corrected an initial miscount in table schematics from seven down to the actual six tables (`plans`, `tenants`, `subscriptions`, `usage_events`, `stripe_events`, `failed_webhooks`).

## Independent Debugging & Environment Setup
- **Directory Structure Reorganization:** Relocated misplaced project directories (`tests/` and `.env.example`) from inside `app/` back to the root repository structure.
- **Nesting & Naming Fixes:** Resolved a nested git clone issue and corrected several misspelled package initialization files (`__init.py__` to `__init__.py`).
- **Stripe Integration & Pricing IDs:** Fixed a `No such price` Stripe Checkout error by correctly swapping a product ID (`prod_...`) for the proper price ID (`price_...`).
- **Environment Reloading:** Handled environment variable propagation quirks by ensuring `uvicorn` processes were manually restarted after any `.env` modification.
- **Webhook Listener Configuration:** Properly configured the local Stripe CLI listener (`stripe listen --events checkout.session.completed --forward-to localhost:8000/webhooks/stripe`), captured the correct webhook secret (`whsec_...`), and verified database state updates directly.
- **Container Lifecycle Management:** Diagnosed and resolved test-suite "connection refused" errors by ensuring Docker Desktop and the PostgreSQL container (`meterly-db`) were actively running.

## Security Practices
- **Credential Hygiene:** Accidentally pasted a test-mode Stripe secret key into chat early on; immediately revoked and rolled the key via the Stripe dashboard as a precaution.
- **Git Safety:** Ensured sensitive configurations (`.env`) remain strictly git-ignored and verified via `git status` and `git ls-files` that only safe template files (`.env.example`) are tracked.

## Technical Explanations & Defensibility
I can fully explain and defend every line of code in this repository, specifically:
- How the database-level unique constraint combined with `ON CONFLICT DO NOTHING` guarantees strict idempotency for incoming metering events.
- How the `SELECT ... FOR UPDATE` row lock on the tenant record prevents race conditions when concurrent requests hit the exact quota boundary (e.g., call 1,000).
- Why claiming usage events and updating tenant state are bundled safely within a single transaction boundary.
- The precision benefits of storing financial figures as integer micro-dollars rather than floating-point values.