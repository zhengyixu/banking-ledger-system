"""Pydantic schemas: the *API contract*, deliberately separate from the ORM models.

Why separate? `Customer` (ORM) mirrors the table. `CustomerCreate` / `CustomerRead` mirror
what clients may send and see. Keeping them apart means a new DB column never leaks into
the API by accident, and a client can't set fields like `id` or `created_at`.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerCreate(BaseModel):
    # Trim whitespace before validating, so "   " counts as empty and fails min_length.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        # Emails are treated as case-insensitive: "A@x.com" and "a@x.com" are one person.
        # Normalising here (not in the DB) keeps the unique constraint simple.
        return value.lower()


class CustomerRead(BaseModel):
    # from_attributes lets Pydantic read straight off an ORM object (customer.id, ...).
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime
