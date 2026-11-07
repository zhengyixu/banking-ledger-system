from fastapi import FastAPI

from ledger_service.errors import register_exception_handlers
from ledger_service.routers import accounts, customers

app = FastAPI(title="Ledger Service")
register_exception_handlers(app)

# Everything business-related lives under /v1 so a future breaking change can ship as /v2.
app.include_router(customers.router, prefix="/v1")
app.include_router(accounts.router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
