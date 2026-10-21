---
name: edge-cases
description: Use when enumerating edge cases (EC) during planning or when reviewing a diff for bugs: empty/null, unicode, timezone, concurrency, authz, retries, partial failure
---

Consider: empty/null, unicode, timezone, concurrency, idempotency, authz boundaries, pagination, retries/timeouts, large payloads, partial failure, feature flags, migrations. Each EC needs lettered options + Decision — never assume. Present options with the `kaotim-planning` question table (`a` / `b` / … / Other). Record letters in the plan EC row and Decision log.
