"""Fill the DEV database with lots of fake ledger data, to practise EXPLAIN / indexing.

    uv run python scripts/seed.py            # 1 hot account (300k rows) + 200 small ones
    uv run python scripts/seed.py --reset    # delete previously seeded rows first
    uv run python scripts/seed.py --hot 50000 --accounts 50 --per-account 200

Not part of the app or the tests. It only touches rows whose customer email starts with
"seed-", and refuses to run if other customers exist. Deposits only, so the ledger
invariant (balance == SUM(transactions.amount)) holds for every seeded account.

Everything is generated inside Postgres with generate_series: 500k rows in seconds,
where 500k ORM objects would take minutes.
"""

import argparse
import sys

from sqlalchemy import create_engine, text

from ledger_service.config import settings

SEED_EMAIL_LIKE = "seed-%@example.com"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hot", type=int, default=300_000, help="rows on the one hot account")
    parser.add_argument("--accounts", type=int, default=200, help="number of small accounts")
    parser.add_argument("--per-account", type=int, default=1_000, help="rows per small account")
    parser.add_argument("--reset", action="store_true", help="delete seeded rows first")
    args = parser.parse_args()

    engine = create_engine(settings.database_url)
    db_name = engine.url.database or ""
    if db_name.endswith("_test"):
        sys.exit(f"Refusing to seed the test database {db_name!r}: it is wiped every run.")

    with engine.begin() as conn:
        if args.reset:
            conn.execute(
                text(
                    """
                    DELETE FROM transactions WHERE account_id IN (
                        SELECT a.id FROM accounts a JOIN customers c ON c.id = a.customer_id
                        WHERE c.email LIKE :like)
                    """
                ),
                {"like": SEED_EMAIL_LIKE},
            )
            conn.execute(
                text(
                    "DELETE FROM accounts WHERE customer_id IN "
                    "(SELECT id FROM customers WHERE email LIKE :like)"
                ),
                {"like": SEED_EMAIL_LIKE},
            )
            conn.execute(
                text("DELETE FROM customers WHERE email LIKE :like"), {"like": SEED_EMAIL_LIKE}
            )

        existing = conn.execute(text("SELECT count(*) FROM customers")).scalar_one()
        if existing:
            sys.exit(f"{existing} customers already exist. Use --reset (only removes seed rows).")

        # 1 hot account + N small ones, one customer each.
        conn.execute(
            text(
                """
                INSERT INTO customers (name, email)
                SELECT 'Seed customer ' || g, 'seed-' || g || '@example.com'
                FROM generate_series(0, :n) AS g
                """
            ),
            {"n": args.accounts},
        )
        conn.execute(
            text(
                "INSERT INTO accounts (customer_id, currency, balance) "
                "SELECT id, 'USD', 0.00 FROM customers WHERE email LIKE :like ORDER BY id"
            ),
            {"like": SEED_EMAIL_LIKE},
        )

        # Hot account = the first one. A deposit every 100 s, oldest first, so ids grow
        # with time like in real life.
        conn.execute(
            text(
                """
                INSERT INTO transactions (account_id, amount, kind, created_at)
                SELECT (SELECT min(id) FROM accounts),
                       round((1 + random() * 99)::numeric, 2),
                       'deposit',
                       now() - (:n - g) * interval '100 seconds'
                FROM generate_series(1, :n) AS g
                """
            ),
            {"n": args.hot},
        )
        # Small accounts: a deposit every 10 minutes.
        conn.execute(
            text(
                """
                INSERT INTO transactions (account_id, amount, kind, created_at)
                SELECT a.id,
                       round((1 + random() * 99)::numeric, 2),
                       'deposit',
                       now() - (:per - g) * interval '10 minutes'
                FROM accounts a, generate_series(1, :per) AS g
                WHERE a.id > (SELECT min(id) FROM accounts)
                ORDER BY g, a.id
                """
            ),
            {"per": args.per_account},
        )
        # Keep the ledger invariant true.
        conn.execute(
            text(
                "UPDATE accounts a SET balance = s.total FROM "
                "(SELECT account_id, sum(amount) AS total FROM transactions GROUP BY account_id) s "
                "WHERE s.account_id = a.id"
            )
        )

    # ANALYZE outside the transaction: refresh planner statistics so EXPLAIN is realistic.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ANALYZE customers, accounts, transactions"))
        hot_id, count = conn.execute(
            text("SELECT min(id), (SELECT count(*) FROM transactions) FROM accounts")
        ).one()
    print(f"Seeded {count:,} transactions into {db_name!r}. Hot account id = {hot_id}.")


if __name__ == "__main__":
    main()
