from app.repositories import usage_repo
from app.pricing import API_CALL_MICROS


def rollup(conn, tenant_id: int):
    plan = usage_repo.get_tenant_plan(conn, tenant_id)
    if plan is None:
        return None
    calls, tokens = usage_repo.get_usage(conn, tenant_id)
    token_cost = usage_repo.get_month_cost(conn, tenant_id)
    call_cost = calls * API_CALL_MICROS
    total = token_cost + call_cost
    return {
        "tenant_id": tenant_id,
        "plan": plan.plan,
        "api_calls": {"used": calls, "limit": plan.api_calls_limit},
        "ai_tokens": {"used": tokens, "limit": plan.ai_tokens_limit},
        "cost_micros": {"api_calls": call_cost, "ai_tokens": token_cost, "total": total},
        "cost_usd": f"{total / 1_000_000:.6f}",
    }