import stripe

from app.config import settings
from app.repositories import tenant_repo


class TenantNotFound(Exception):
    pass


def create_checkout(conn, tenant_id: int) -> str:
    stripe.api_key = settings.stripe_api_key
    tenant = tenant_repo.get_tenant(conn, tenant_id)
    if tenant is None:
        raise TenantNotFound()

    customer_id = tenant.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(name=tenant.name, metadata={"tenant_id": str(tenant_id)})
        customer_id = customer.id
        tenant_repo.set_customer_id(conn, tenant_id, customer_id)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=str(tenant_id),
        line_items=[{"price": settings.stripe_pro_price_id, "quantity": 1}],
        subscription_data={"metadata": {"tenant_id": str(tenant_id)}},
        success_url=f"{settings.app_base_url}/health?checkout=success",
        cancel_url=f"{settings.app_base_url}/health?checkout=cancelled",
    )
    return session.url