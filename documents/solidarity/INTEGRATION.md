---
title: "Integration — Solidarity Module in erdpuls_dashboard"
subtitle: "Native FastAPI router, per initiative, tested inside the real Erdpuls application"
author: "Michel Garand"
date: "August 2026"
version: "v0.4"
lang: "en"
license: "CC BY-SA 4.0"
project: "Solidarity Financing 2026 (working title)"
status: "living draft v0.4 — native-module integration notes; internal until the hosts have read and agreed"
document: "INTEGRATION.md"
type: "prototype-artifact"
---

*The answer to "do we need Flask": no. The whole ubec.network platform runs FastAPI, and erdpuls_dashboard already ships FastAPI, uvicorn, SQLAlchemy, PostgreSQL, Jinja2, bcrypt auth, and a role system with a facilitator role. The prototype is a native module of that codebase — the Flask standalone (v0.1, v0.2) is superseded and kept only as history.*

* * *

## What Changed Since v0.3

These notes were written when the module was one router mounted at a single hard-coded path. Three things have happened since, and v0.3 no longer describes what is running.

Financing became per initiative. The router mounts at /{initiative_slug}/solidarity, with a chooser at /solidarity listing the initiatives a facilitator may open. Nothing about the model is bound to one place; each initiative keeps its own sessions, budgets, rounds and settlements.

The budget can be laid open. A session's budget may be shown to people registered for the linked offering and to members of the initiative — lines and sums only, no token, no per-family pledge, and no pledge form. The round is still held in a room.

Money is handled in more than one currency without ever being silently converted. Contribution rates are per currency; where a conversion is genuinely needed the rate comes from Frankfurter (api.frankfurter.dev) against EUR and is frozen onto the contribution at the moment of giving. It is never recomputed afterwards, so a record says what it said on the day.

* * *

## The Module Today

**Schema.** db/scripts/012_solidarity_financing.sql creates a dedicated `solidarity` schema in the existing ubec_erdpuls database, extended by the migrations that followed it (013, 014, 017 through 022, 024). No Erdpuls table is touched; rollback is one DROP SCHEMA. The invariants live in the schema rather than in application code: the status enum makes an untagged figure unrepresentable, pledges carry a token and never a household, and the optional token-to-household mapping is a table the report views do not join. No child data has a column to live in.

**Router.** app/routers/solidarity.py, at v1.4. Two routers are registered: the per-initiative module and the chooser. Auth is Erdpuls's own get_current_user plus has_role_or_higher for the facilitator role, and, since v1.1, membership of the initiative being opened — a facilitator elsewhere is not a facilitator here. Raw SQL through SQLAlchemy text() against the solidarity schema.

**Templates.** templates/solidarity/ — nine screens extending the Erdpuls base.html, plus one shared stylesheet, _styles.html, which all nine include. The module wears the platform's own frame and navigation.

**Tests.** documents/solidarity/ holds the smoke tests, one per behaviour that could quietly break: access and membership, budget editing and the freeze, offering links, currency rates and conversion, the open budget, session and user deletion, and the phone layout. They run against the real application on the server after a deploy.

* * *

## The Screens on a Phone

Added at module v1.4. Below 640px each record table drops its header row and becomes one card per row, every cell labelled from its own header; totals lay out as a line, name left and figure right, as on paper; each form field takes its own row with finger-sized controls; and inputs are set at 16px so iOS does not zoom the page when one is tapped.

This matters most for the open budget, which is the one screen a family reads rather than a facilitator: a six-column table scrolled sideways on a phone is not a budget laid open. The Ukrainian labels come from the same conditionals already in that template, so the participant view is labelled in the language it is read in.

Two core Erdpuls pages were corrected in the same pass, outside this module: the progress card on the offering and contribute pages stayed pinned when the layout collapsed to one column, so it covered the text as a phone scrolled. It now scrolls with the page below 900px.

What the tests can prove is that the markup is there. How it reads on a real phone, in Ukrainian, at the screen size a family actually carries, is still to be checked by looking.

* * *

## Updating the Server

Changes arrive as a self-extracting installer script, run from the root of a checkout. The order matters, and the installer step comes first: running git before it produces a confusing clean tree and nothing to commit.

```bash
cd /home/ubec/ubec_commons/ubec_erdpuls
bash ~/install_<name>.sh --force
python3 documents/solidarity/smoke_test_<name>.py
git add -A && git commit -m "<what changed>"
git push
```

Then the served checkout follows the remote rather than being installed into a second time, so the two trees stay identical:

```bash
cd /srv/ubec/erdpuls
git pull
sudo systemctl restart ubec-erdpuls.service
```

A migration, where one is needed, is applied with psql against ubec_erdpuls before the restart. Template-only updates need none, and say so in their header.

* * *

## Access and Standing

Access is by Erdpuls account with role facilitator or higher, plus membership of the initiative — both assigned through the existing admin screens. The module is not linked from any public initiative page and must not be until the hosts have read and agreed; a test asserts exactly this.

Later, if the participants want families entering their own pledges from their own accounts, the member role and the per-route gates are already in place to build on. That is a participants' decision, not a default — and the working assumption remains the opposite one: the folded slip in a box is a stronger guarantee of anonymity than any login.

Cryptocurrency rails are deferred, not rejected, and nothing in the schema or the router anticipates them. They are reopened when the participants decide on rails, when professional legal and tax advice has been taken, and when Ukraine's virtual-assets framework is in force.

* * *

## License and Attribution

These notes are part of Solidarity Financing 2026 (working title) and are licensed under CC BY-SA 4.0. The module code joins erdpuls_dashboard under its license (GNU AGPL v3.0).

Michel Garand | Solidarity Financing | CC BY-SA 4.0

Contact: stewardship@ubec.network
