# Session Prompt — Add Erdpuls Initiative #2 (data-driven) + End-to-End Test

*Paste this as the first message of a new conversation, ideally inside the Erdpuls project so
the spec and `INSTRUCTIONS.md` are in scope. Fill in the “Initiative to create” block first.*

---

We're adding the **second initiative** to the Erdpuls network and using it to **test the whole
pipeline end to end**. Read the Erdpuls module spec and the global `INSTRUCTIONS.md` first,
then verify live state before proposing changes. Truth hierarchy: **git repo > spec >
conversation.**

## Where we're starting from (verified at handoff — re-verify, don't trust this blindly)

- Repo `github.com/ubeccommon/erdpuls_dashboard`, branch `main`, at **`2c804b6`** at handoff.
  Recent history: `8ce5c48` (protocol-standard reframe of README + dedupe of `documents/`),
  `5a33634` (revert of an accidental static/backup commit), `2c804b6` (`.gitignore` guard).
- Erdpuls is an **open living lab protocol**: `/` renders `templates/network.html` (the
  network **directory of initiatives**); `/muellrose` renders `templates/index.html` (the
  flagship **reference implementation**). Müllrose is one initiative, not the whole.
- **The initiatives directory is currently HARDCODED.** In `templates/network.html` the
  Müllrose card is a literal `<a class="initiative" href="/muellrose">…</a>` block with inline
  EN/DE/PL/UK conditionals; a `.initiative--soon` (dashed “coming soon”) style already exists.
  There is **no `initiatives` table** in `db/schema_complete.sql` and **no initiative model or
  admin flow** in `app/` — only route docstrings mention “initiative.” So there is no existing
  “create initiative” feature to click; this session builds the mechanism.
- `documents/initiatives/` holds `_TEMPLATE/` and `muellrose/`; the pattern is copy
  `_TEMPLATE/` → `<slug>/`.

## Your first actions

1. Read the Erdpuls spec, then `INSTRUCTIONS.md`.
2. Clone the repo and verify current state with `git log` / `ls` / `cat`: confirm HEAD,
   confirm the directory is still hardcoded, confirm there's still no initiatives table/model,
   and read `network.html`, `app/routers/web.py`, and `documents/initiatives/_TEMPLATE/`.
3. State the verification boundary explicitly: you can inspect the repo directly, but the live
   Hetzner server (`ubec-common`, `:8004`) is not reachable from the sandbox — live checks are
   run by the operator relaying terminal output. Author + render-test in a clone; hand off
   patches for the operator to apply.

## Goal & scope

**Primary:** make the initiatives directory **data-driven** (open thread #3) and add a second
initiative as the concrete test case, so `/` lists initiatives automatically instead of from
hardcoded HTML. Keep Müllrose intact at `/muellrose` as the reference implementation.

Decide, from the code you read (propose; don't guess), the implementation approach and the
per-initiative fields. Open thread #3 names: **name, location, status, blurb, url**; consider
also **slug, languages, short description, steward/lead**. Two viable approaches — recommend
one with tradeoffs before building:
- **Config/data-module** (a Python/JSON/YAML list the landing iterates over) — lightest, no DB
  change, good for a first data-driven step and this test.
- **`initiatives` table** in schema `erdpuls_threshold` — heavier; if chosen, provide an
  idempotent migration, update `db/schema_complete.sql`, and grant to `ubec_erdpuls_app`.

The full **“Start an initiative” onboarding/admin flow (open thread #4)** is likely out of
scope for this session — note it as a follow-up unless the operator asks for it.

Also create `documents/initiatives/<slug>/` from `_TEMPLATE/` for the new initiative.

## Initiative to create — FILL THIS IN

> If you want to validate the pipeline without publishing a real place yet, make this a clearly
> labelled **staging/demo** initiative (status “coming soon”), verify end-to-end, then swap in
> the real one. State which you're doing.

- **Name:** …
- **Slug (url path):** … (e.g. `/<slug>`)
- **Location:** …
- **Status:** active | forming | coming soon
- **Blurb (1–2 sentences, per language as available; EN required, DE/PL/UK if you have them):** …
- **Links / URL:** … (external site, or an internal page if it gets one)
- **Does it get its own in-app page/route, or directory-card-only for now?** …

## “Works according to plan” — test checklist

Do these in a clone before any deploy, and give the operator explicit commands + expected
output for the live checks:

- **Render:** the landing template renders through the app's Jinja env with no error; `/` now
  lists **both** Müllrose and the new initiative **from the data source**, not hardcoded HTML.
- **i18n:** the directory still renders correctly in EN/DE/PL/UK; the new card degrades to EN
  where a language is missing (consistent with current coverage).
- **Routing:** if the initiative gets a route, it resolves; nothing assumes `/` = Müllrose
  (re-check open thread #5). `/muellrose` still works unchanged.
- **Endpoints:** `/health` OK; confirm any new/changed routes against `/openapi.json` (don't
  assume an endpoint exists).
- **DB (only if you added a table):** migration is idempotent, `db/schema_complete.sql`
  updated, grants applied, `search_path`/schema `erdpuls_threshold` respected, no `create_all`.
- **Design/legal invariants intact:** Bunny Fonts only, no Google Fonts, no Cloudflare, shared
  UBEC design system, CC BY-SA footer, © 2024–2026 Michel Garand, locked terms (stewards,
  regenerative, bioregional, commons).

## Deploy guardrails (hard-won — follow exactly)

- **Author only in `~/ubec_commons/ubec_erdpuls`; treat `/srv/ubec/erdpuls` as pull-only.**
- **Never `git add -A` on the server** — it grabs untracked leftovers (this caused an
  accidental commit + revert last session). Stage explicit paths.
- Patch flow: author + render-test in a clone → `git format-patch` → **scp the patch to the
  server** → `git am` in the source-of-truth tree (use `git am -3` if the base differs; if it
  reports local uncommitted changes, inspect/stash them first) → `git push` → `git pull` on the
  live tree.
- Restart `ubec-erdpuls.service` **only if app code changed**; template/data/doc-only changes
  need just a pull (uvicorn picks up templates; confirm whether your change requires a restart).
  Only `nginx -t` / `systemctl reload nginx` need sudo.
- EU-hosted only (Hetzner); Python unless the layer requires otherwise.

## Close-out

Update the Erdpuls spec / status report at session end: record the new initiative, the
data-driven directory change, the commit SHA(s), and move open thread #3 (and #5 if verified)
forward. Flag anything still requiring live verification.
