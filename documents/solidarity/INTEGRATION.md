---
title: "Integration — Solidarity Module in erdpuls_dashboard"
subtitle: "Native FastAPI router, tested inside the real Erdpuls application"
author: "Michel Garand"
date: "August 2026"
version: "v0.3"
lang: "en"
license: "CC BY-SA 4.0"
project: "Solidarity Financing 2026 (working title)"
status: "living draft v0.3 — native-module integration notes; internal until the hosts have read and agreed"
document: "INTEGRATION.md"
type: "prototype-artifact"
---

*The answer to "do we need Flask": no. The whole ubec.network platform runs FastAPI, and erdpuls_dashboard already ships FastAPI, uvicorn, SQLAlchemy, PostgreSQL, Jinja2, bcrypt auth, and a role system with a facilitator role. The prototype is now a native module of that codebase — the Flask standalone (v0.1, v0.2) is superseded and kept only as history.*

* * *

## What Was Verified

Read from the public ubeccommon repos: erdpuls_dashboard runs FastAPI 0.109 with uvicorn, SQLAlchemy 2.0.25 against PostgreSQL (database ubec_erdpuls, schema erdpuls_threshold, search_path set per connection), Jinja2 templates extending base.html, session-cookie auth with secure cookies, and RBAC with roles member, creator, facilitator, moderator, admin.

Then verified live: the module below was installed into a checkout of erdpuls_dashboard, the full application booted with it, and a fifteen-check test drove the entire financing flow through Erdpuls's real login and role system — anonymous refused, member role refused with 403, admin passing, and the sums-only guarantee holding on every screen. The public initiative page is untouched: no solidarity link appears on it.

* * *

## The Module — Four Pieces

1. **db/scripts/012_solidarity_financing.sql** — creates a dedicated `solidarity` schema in the existing ubec_erdpuls database. No Erdpuls table is touched; rollback is one DROP SCHEMA. All invariants live in the schema: status enum (untagged figures unrepresentable), token-only pledges, optional token-to-household mapping that report views never join, no child data anywhere.
2. **app/routers/solidarity.py** — the FastAPI router, prefix /erdpuls-verkhovyna/solidarity. Auth is Erdpuls's own get_current_user plus has_role_or_higher(role, "facilitator"): the platform's existing facilitator role is exactly the round facilitator. Raw SQL via SQLAlchemy text() against the solidarity schema.
3. **templates/solidarity/** — seven templates extending the Erdpuls base.html, so the module wears the platform's own frame and navigation.
4. **smoke_test_native.py** — the fifteen checks, runnable on the server after deploy.

* * *

## Install on the Server

```bash
cd /path/to/erdpuls_dashboard
cp solidarity.py app/routers/
cp -r templates/solidarity templates/
psql -U erdpuls -d ubec_erdpuls -f db/scripts/012_solidarity_financing.sql
```

Then two lines in app/main.py, after the existing include_router calls:

```python
from .routers.solidarity import router as solidarity_router
app.include_router(solidarity_router)
```

Restart the Erdpuls service. No new dependency, no new process, no proxy change, no new database: the module rides everything already running.

* * *

## Access and Standing

Access is by Erdpuls account with role facilitator or higher — assign the role through the existing admin screens. The module is not linked from the public Erdpuls Verkhovyna page and must not be until the hosts have read and agreed; the fifteenth check asserts exactly this. Later, if the participants want the families entering their own pledges from their own accounts, the member role and per-route gates are already in place to build on — that is a participants' decision, not a default.

* * *

## License and Attribution

These notes are part of Solidarity Financing 2026 (working title) and are licensed under CC BY-SA 4.0. The module code joins erdpuls_dashboard under its license (GNU AGPL v3.0).

Michel Garand | Solidarity Financing | CC BY-SA 4.0

Contact: stewardship@ubec.network
