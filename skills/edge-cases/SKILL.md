---
name: edge-cases
description: Use when enumerating edge cases (EC) during planning or when reviewing a diff for bugs: empty/null, unicode, timezone, concurrency, authz, retries, partial failure
---

Consider: empty/null, unicode, timezone, concurrency, idempotency, authz boundaries, pagination, retries/timeouts, large payloads, partial failure, feature flags, migrations. Each EC needs options + Decision — never assume. Present via AskQuestion (or the `kaotim-plan` lettered fallback) with Other. Record the chosen letter/label in the plan EC row and Decision log.
