from app.repositories import stripe_repo

ENDED = ("canceled", "incomplete_expired")


def _tenant_id(conn, obj: dict):
    meta = (obj.get("metadata") or {}).get("tenant_id")
    if meta:
        return int(meta)
    ref = obj.get("client_reference_id")
    if ref:
        return int(ref)
    customer = obj.get("customer")
    if customer:
        return stripe_repo.find_tenant_by_customer(conn, customer)
    return None


def apply(conn, event: dict):
    obj = event["data"]["object"]
    kind = event["type"]
    tenant_id = _tenant_id(conn, obj)
    if tenant_id is None:
        return

    if kind == "checkout.session.completed":
        stripe_repo.set_plan(conn, tenant_id, "pro", "active")
        if obj.get("subscription"):
            stripe_repo.upsert_subscription(conn, tenant_id, obj["subscription"], "active")
    elif kind == "customer.subscription.updated":
        status = obj["status"]
        if status in ENDED:
            stripe_repo.set_plan(conn, tenant_id, "free", "active")
        else:
            stripe_repo.set_plan(conn, tenant_id, "pro", status)
        stripe_repo.upsert_subscription(conn, tenant_id, obj["id"], status)
    elif kind == "customer.subscription.deleted":
        stripe_repo.set_plan(conn, tenant_id, "free", "active")
        stripe_repo.upsert_subscription(conn, tenant_id, obj["id"], "canceled")