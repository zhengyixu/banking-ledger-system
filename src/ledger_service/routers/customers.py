"""HTTP layer for customers: parse the request, call the service, shape the response.

No business rules live here, and no error mapping either: services raise domain errors and
`errors.py` turns them into 404/409 responses in one place.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from ledger_service.db import SessionDep
from ledger_service.schemas import CustomerCreate, CustomerRead
from ledger_service.services import customers as customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, session: SessionDep, response: Response):
    customer = customer_service.create_customer(session, data)
    response.headers["Location"] = f"/v1/customers/{customer.id}"
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, session: SessionDep):
    return customer_service.get_customer(session, customer_id)


@router.get("", response_model=list[CustomerRead])
def list_customers(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return customer_service.list_customers(session, limit=limit, offset=offset)
