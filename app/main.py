from fastapi import FastAPI

from app.jobs import start_retry_loop
from app.routers import checkout, generate, usage, webhooks

app = FastAPI(title="Usage Metering & Billing Engine")
app.include_router(generate.router)
app.include_router(usage.router)
app.include_router(checkout.router)
app.include_router(webhooks.router)


@app.on_event("startup")
def startup():
    start_retry_loop()


@app.get("/health")
def health():
    return {"status": "ok"}