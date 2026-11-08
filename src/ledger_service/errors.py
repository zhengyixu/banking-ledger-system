"""Maps domain exceptions to HTTP responses, in ONE place.

Routers and services just raise domain errors; they never build error responses.
Starlette looks handlers up along the exception's class hierarchy (MRO), so one handler
for `NotFound` also covers CustomerNotFound, AccountNotFound and any future subclass.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ledger_service.exceptions import Conflict, InsufficientFunds, NotFound


def register_exception_handlers(app: FastAPI) -> None:
    # Same body shape FastAPI uses for its own errors: {"detail": "..."}.
    @app.exception_handler(NotFound)
    async def handle_not_found(request: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_404_NOT_FOUND)

    @app.exception_handler(Conflict)
    async def handle_conflict(request: Request, exc: Conflict) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_409_CONFLICT)

    @app.exception_handler(InsufficientFunds)
    async def handle_insufficient_funds(request: Request, exc: InsufficientFunds) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
