from fastapi import FastAPI

from ledger_service.routers import customers

app = FastAPI(title="Ledger Service")

# Everything business-related lives under /v1 so a future breaking change can ship as /v2.
app.include_router(customers.router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
