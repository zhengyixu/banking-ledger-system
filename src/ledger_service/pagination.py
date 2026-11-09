"""Opaque cursors for keyset pagination.

A cursor remembers the sort key of the LAST row the client saw: (created_at, id).
The next page is "rows strictly older than that key". Clients treat it as an opaque
string, so we can change what is inside without breaking them.

It is base64 (not encryption): don't put secrets in it, and never trust it. Anything a
client sends back is untrusted input, so decoding failures become InvalidCursor (422).
"""

import base64
import binascii
from datetime import datetime

from ledger_service.exceptions import InvalidCursor
from ledger_service.models import Transaction

Cursor = tuple[datetime, int]


def encode_cursor(tx: Transaction) -> str:
    raw = f"{tx.created_at.isoformat()}|{tx.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(value: str) -> Cursor:
    try:
        created_at, tx_id = base64.urlsafe_b64decode(value.encode()).decode().split("|")
        return datetime.fromisoformat(created_at), int(tx_id)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise InvalidCursor() from None
