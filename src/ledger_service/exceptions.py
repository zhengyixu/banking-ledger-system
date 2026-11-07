"""Domain exceptions: business-rule failures, expressed without any HTTP knowledge.

Services raise these; `errors.py` decides which status code each one becomes.
That keeps the business logic reusable (e.g. from a CLI, a worker, or an MCP server).

The base classes below (NotFound, Conflict) are what the HTTP layer maps, so adding a new
"not found" case needs no new handler: just subclass NotFound.
"""


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


# TODO(you): give InsufficientFunds a useful constructor and message. Hints:
#   - __init__(self, account_id: int, balance: Decimal, requested: Decimal)
#   - keep the values as attributes (tests and logs can use them) and build a clear
#     message, e.g. "Account 7 has 50.00, cannot withdraw 80.00".
#   - decide: should it subclass DomainError directly, or Conflict (-> 409)? Overdraft is
#     "valid request, but the current state forbids it". 409 and 422 are both defensible;
#     pick one and be ready to explain why in an interview.
class InsufficientFunds(DomainError):
    pass
