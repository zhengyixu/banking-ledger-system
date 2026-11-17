# Security policy

## Supported versions

Only the `main` branch is supported. There are no released versions; fixes land on `main`.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub private vulnerability reporting:

https://github.com/zhengyixu/banking-ledger-system/security/advisories/new

Do not open a public issue or pull request for a suspected vulnerability. Include the
affected endpoint or file, steps to reproduce, and the impact you expect.

## Scope

In scope:

- The REST API (`/v1/...` routes and `/health`).
- Money movement and locking: deposits, withdrawals, transfers, row locking and the
  `balance == SUM(transactions.amount)` invariant.
- Database access: queries, migrations and anything that could lead to SQL injection or
  data corruption.
- The container image built from the `Dockerfile`.

Already known and documented in the README (reports are still welcome if you find a
concrete consequence we have not described): the API has no authentication yet.

## Development credentials

The credentials in `docker-compose.yml`, `.github/workflows/ci.yml` and the default
DSNs in `src/ledger_service/config.py` (`ledger:ledger`) are local development and CI
values for throwaway databases only. They are not used by any deployed system and are
not secrets.

## Response expectations

This is a personal portfolio project maintained on a best-effort basis. I will try to
acknowledge and fix valid reports, but there is no guaranteed response time and no bug
bounty.
