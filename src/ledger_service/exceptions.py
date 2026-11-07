"""Domain exceptions: business-rule failures, expressed without any HTTP knowledge.

Services raise these; the API layer decides which status code each one becomes.
That keeps the business logic reusable (e.g. from a CLI, a worker, or an MCP server).
"""


class DomainError(Exception):
    """Base class, so callers can catch every business-rule failure at once."""


class CustomerNotFound(DomainError):
    def __init__(self, customer_id: int) -> None:
        super().__init__(f"Customer {customer_id} not found")
        self.customer_id = customer_id


class DuplicateEmail(DomainError):
    def __init__(self, email: str) -> None:
        super().__init__(f"A customer with email {email!r} already exists")
        self.email = email
