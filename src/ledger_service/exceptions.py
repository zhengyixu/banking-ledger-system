"""Domain exceptions: business-rule failures, expressed without any HTTP knowledge.

Services raise these; `errors.py` decides which status code each one becomes.
That keeps the business logic reusable (e.g. from a CLI, a worker, or an MCP server).

The base classes below (NotFound, Conflict) are what the HTTP layer maps, so adding a new
"not found" case needs no new handler: just subclass NotFound.
"""

from decimal import Decimal


class DomainError(Exception):
    """Base class, so callers can catch every business-rule failure at once."""


class NotFound(DomainError):
    """A referenced thing doesn't exist  ->  HTTP 404."""


class Conflict(DomainError):
    """Valid request that clashes with current state  ->  HTTP 409."""


class CustomerNotFound(NotFound):
    def __init__(self, customer_id: int) -> None:
        super().__init__(f"Customer {customer_id} not found")
        self.customer_id = customer_id


class AccountNotFound(NotFound):
    def __init__(self, account_id: int) -> None:
        super().__init__(f"Account {account_id} not found")
        self.account_id = account_id


class DuplicateEmail(Conflict):
    def __init__(self, email: str) -> None:
        super().__init__(f"A customer with email {email!r} already exists")
        self.email = email


class InsufficientFunds(DomainError):
    def __init__(self, account_id: int, balance: Decimal, requested: Decimal) -> None:
        super().__init__(f"Account {account_id} has {balance}, cannot withdraw {requested}")
        self.account_id = account_id
        self.balance = balance
        self.requested = requested
