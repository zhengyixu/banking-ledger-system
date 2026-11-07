"""HTTP layer for customers: parse the request, call the service, shape the response.

No business rules live here. If you find yourself writing an `if` about money or
uniqueness in a router, it probably belongs in a service.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from ledger_service.db import SessionDep
from ledger_service.exceptions import CustomerNotFound, DuplicateEmail
from ledger_service.schemas import CustomerCreate, CustomerRead
from ledger_service.services import customers as customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, session: SessionDep, response: Response):
    try:
        customer = customer_service.create_customer(session, data)
    except DuplicateEmail as exc:
        # 409 Conflict: the request is valid, but clashes with existing state.
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    response.headers["Location"] = f"/v1/customers/{customer.id}"
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, session: SessionDep):
    try:
        return customer_service.get_customer(session, customer_id)
    except CustomerNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=list[CustomerRead])
def list_customers(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return customer_service.list_customers(session, limit=limit, offset=offset)
