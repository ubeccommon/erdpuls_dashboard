# Module Spec — UBEC Erdpuls
**Project:** UBEC DAO · Ubuntu Bioregional Economic Commons DAO
**Module:** Erdpuls — `erdpuls.ubec.network`
**Purpose of this doc:** canonical, current-state spec + open threads for the Erdpuls
module. Seed for the Erdpuls Project knowledge base. Read at session start; update at
session close. **Truth hierarchy: git repo > this spec > conversation.**
**Last updated:** 9 July 2026 (end of initiatives DB + propose→review→publish session)

---

## YOUR FIRST ACTION
Read this spec, then the shared `INSTRUCTIONS.md` (global rules). Inspect the live
repo `https://github.com/ubeccommon/erdpuls_dashboard` and the running service before
proposing changes — never guess server state; verify with `ls`/`cat`/`git log`.
**Verify the repo HEAD first** — this spec can lag the repo.

## MANDATORY CORE RULES (every session)
- **Reason from facts only.** Never guess missing info; if unclear, stop and ask.
- **Coding is exact.** Verify endpoints (`/openapi.json`), files (`ls`/`cat`), and
  render templates through the app's Jinja env before deploying. Run SQL against a real
  PG16 before shipping a migration (a real bug — see §Config gotchas — was only caught
  by executing it).
- **All code Python** unless the service requires otherwise (HTML/CSS/JS, nginx).
- **EU-hosted only** (Hetzner). No AWS/GCP/Azure/**Cloudflare** (Cloudflare banned).
- **Bunny Fonts only** (`fonts.bunny.net`) — never Google Fonts (GDPR).
- **Locked terminology:** stewards (not users), regenerative (not sustainable),
  bioregional (one word), commons.
- **Copyright:** `© 2024–2026 Michel Garand` · **CC BY-SA 4.0** · GNU AGPL v3.0.
- Deploy scripts run as `ubec`; only `nginx -t` / `systemctl reload nginx` need sudo;
  nginx writes via `sudo tee`. **DB migrations run as the `postgres` superuser** (there
  is no `ubec` DB role) — see §Config gotchas.

---

## PLATFORM CONTEXT
- **Server:** Hetzner CPX42 · `ubec-common` · `49.13.167.206` · user `ubec`
- **Stack:** Ubuntu · nginx 1.24 · PostgreSQL 16 · FastAPI/uvicorn (Jinja2 app)
- **Erdpuls port:** uvicorn `127.0.0.1:8004` (Hub is 8003; 8000/8001 also in use)
- **Service:** `ubec-erdpuls.service` (systemd, User=ubec, WorkingDir=/srv/ubec/erdpuls,
  EnvironmentFile=/srv/ubec/erdpuls/.env, `uvicorn app.main:app --port 8004 --workers 2`)
- **External data dir:** `/srv/ubec/erdpuls-data/initiatives/` — runtime-created,
  per-initiative folders (see §Initiatives). **Outside the git repo**, owned by `ubec`.
- **Design CDN:** `design.ubec.network/v1/` — `ubec-design-system.css`, `nav-styles.css`,
  `ubec-nav.js` (served from `/srv/ubec/design-cdn/`, tracked in `ubec-common` at `/srv/ubec`)
- **Fonts:** Bunny — DM Serif Display, DM Sans, JetBrains Mono

## GIT / DEPLOY MODEL (deploy-by-pull)
- **Canonical app repo:** `github.com/ubeccommon/erdpuls_dashboard`
- **Source of truth (edit here):** `~/ubec_commons/ubec_erdpuls` → commit → `git push`
- **Live (deploy target):** `/srv/ubec/erdpuls` → `git pull` → restart if app code changed
- Both trees track the same remote/branch (`main`); `.env` and `venv/` are gitignored,
  so `git pull` never touches secrets or the venv.
- Working pattern: author + **render-test in a clone** → `git format-patch` → **scp the
  patch to the server** → `git am -3` in source-of-truth → push → pull to live.
  (Design-CDN changes commit at `/srv/ubec`.)
- **Never `git add -A` on the server** — it grabs untracked leftovers (caused an
  accidental commit + revert). Stage explicit paths.
- **Deploy ordering when a migration is involved:** `git pull` → run the migration →
  restart. Never restart new DB-reading code before its migration has run (the app 500s
  / the landing errors on the missing table/column otherwise).

---

## CURRENT STATE (verified this session, on PG16 + full app import)

### Architecture — network tier + flagship + initiatives directory
- **`/`** → `home()` renders `templates/network.html`: general **UBEC Erdpuls** intro +
  **directory of initiatives**, now **DB-backed and published-only** (reads
  `get_published_initiatives(db)` → only `is_published = true` rows). Müllrose seed
  renders as the flagship card.
- **`/muellrose`** → `muellrose()` renders `templates/index.html`: **Erdpuls Müllrose**,
  the flagship / **reference implementation** (offerings, fund_balance). Unchanged.
- **`/initiatives/start`** (GET+POST, **public, no login**) → `templates/initiatives_start.html`:
  propose an initiative. Creates a row **unpublished** (honeypot, slug validation,
  cannot self-declare `active`; **no filesystem write at submit**). The network landing's
  "Start an initiative" CTA points here (was Living Labs register).
- **`/admin/initiatives`** (admin/moderator) → `templates/admin/initiatives.html`:
  **review queue** — pending proposals with **Approve** / **Reject(=delete)**, plus
  published initiatives with **Unpublish** / **Delete**. Approve sets `is_published=true`
  **and creates the external data folder** (folder-on-approve). The admin *create* form/
  route was **removed** (admins review, they don't author).
- nginx: the app owns `/` (no static `location = /` blocks); Erdpuls vhost is just
  `.well-known` (acme + stellar.toml), dotfile deny, and `location /` → `:8004`. **No
  `/login` etc. blocks** — the app owns all app paths.

### Initiatives — data model & workflow (open threads #3 + #4: DONE)
- **Table `erdpuls_threshold.initiatives`** backs the directory (config-module step was
  intermediate and is superseded). Columns: `id, slug (unique, ^[a-z0-9-]+$), name,
  location, status ∈ {active,forming,coming_soon}, flagship, has_page, route, url,
  blurb_en (NOT NULL) / blurb_de / blurb_pl / blurb_uk, sort_order, is_published (default
  FALSE), submitter_name, submitter_email, created_at, updated_at`.
- **Workflow:** public **propose** (`/initiatives/start`, unpublished) → admin **review**
  (`/admin/initiatives`) → **publish** (appears on `/`). Reject = delete.
- **`app/initiatives.py`** = data-access layer + helpers: `get_initiatives(db)` (all, for
  admin), `get_published_initiatives(db)` (public `/`), `get_initiative(db, slug)`,
  `slugify`, `validate_slug` (format / RESERVED_SLUGS / taken), `initiative_data_path`,
  `create_data_dir`. The ORM `Initiative` model provides `.href` (property) and
  `.blurb_for(lang)` (EN fallback) — the template contract.
- **External per-initiative folders:** created **on approve** at
  `settings.initiatives_data_dir/<slug>/` (default `/srv/ubec/erdpuls-data/initiatives`),
  from `documents/initiatives/_TEMPLATE/`. **Never written into the repo tree** (deploy-
  by-pull safe). Slug is validated + re-`slugify`d → path-traversal-safe. These folders
  live only on the server (outside git); curated developer docs still go in
  `documents/initiatives/<slug>/` in the repo.

### Auth (fixed this session)
- Canonical session = signed **`erdpuls_session`** cookie (`app/auth.py`:
  `set_session_cookie` / `verify_session_token`, `httponly` + `samesite=lax` + `secure`).
  `auth.get_current_user_optional` reads it. Login (`/login`) sets it.
- **Bug fixed:** `web.py` previously shadowed `get_current_user_optional` with a version
  reading a phantom `user_id` cookie that nothing set, so login "did nothing" on public
  pages. `web.py` now imports the canonical `auth.get_current_user_optional` (as
  `admin.py` / `api.py` already do). **Do not reintroduce a `user_id`-cookie reader.**

### OER Library — live aggregation from `ubeccommon.github.io`
- **Not stored in this repo.** `/library` is a live aggregator/renderer over a
  **separate** repo: `github.com/ubeccommon/ubeccommon.github.io` (branch `main`,
  the "UBEC Open" Pages site). Service module: **`app/services/oer_library.py`**.
- **Content roots (only these are indexed):**
  `Pattern_Language_of_Place/oer/docs/{EN,DE,PL}/` (OER curriculum + `soil/`
  sub-collections) and `Pattern_Language_of_Place/Learning_Pathways/{EN,DE,PL}/`.
  Language is detected from the path segment `EN`/`DE`/`PL` (case-insensitive),
  **NOT** the filename. Companion PDFs: same filename stem under `.../{LANG}/pdf/`.
  Excluded even inside roots: `index.md`, `README`, `/standards/`, `/audit/`,
  `00_METADATA`, and the `*.py` tooling / `ERDPULS_*` standard docs.
- **Fetch strategy (rate-limit-aware):** the recursive file **tree** comes from
  the **GitHub API** (`git/trees/main?recursive=1`) — the *only* call that counts
  against rate limits; optional `GITHUB_TOKEN` env lifts 60→5,000 req/hr. Raw
  bodies come from **`raw.githubusercontent.com`** (no auth, no API limit).
  Markdown → HTML rendered server-side with the `markdown` lib (tables,
  fenced_code, toc, attr_list, def_list, nl2br). In-memory cache, **30-min TTL**
  (tree + raw); index previews fetched concurrently via `asyncio.gather`.
- **Routes (`app/routers/web.py`):** `GET /library` → `library/index.html`
  (grouped by collection, optional `lang_filter`); `GET /library/resource?path=…`
  → `library/detail.html` (rendered MD; path sanitised — rejects `..` / leading
  `/`); `GET /library/pathways` → `library/pathways.html` (full-page iframe embed
  of the pre-rendered GitHub Pages HTML pathway maps; **EN+DE live, PL commented
  out** pending publication).
- **Licensing split:** the service module is **AGPL v3.0** (code); rendered
  resources are stamped **CC BY-SA 4.0** (Michel Garand) as content.

### Database
- DB `ubec_erdpuls`, schema **`erdpuls_threshold`** (app sets `search_path` per connection
  to `erdpuls_threshold, public`; no `create_all`). Canonical fresh-install file
  **`db/schema_complete.sql`** — verified on PG16: **10 tables** (9 + initiatives),
  views, seeds. Migrations under `db/scripts/`: **`010_initiatives.sql`** (table + Müllrose
  seed + grants), **`011_initiatives_review.sql`** (is_published + submitter_* + publish
  flagship). Both idempotent. Grants to role **`ubec_erdpuls_app`** (table-level grant
  covers the new columns).
- `users.role` default `'member'`. Admin user `admin@ubec.network` exists (active, hashed).

### i18n
- **Supported: EN / DE / PL / UK.** New surfaces (`network.html`, `initiatives_start.html`,
  `admin/initiatives.html`) have inline EN/DE/PL/UK; missing per-initiative blurbs fall
  back to EN. Coverage on older pages still varies (open thread #1). CDN nav still not
  given `uk`.

### Repo commits landed this session (on `main`)
- `d40d05d` network landing: data-driven initiatives directory (config module).
- DB-backed directory + dashboard registration (this arrived as an unpushed local commit
  of **unclear provenance**; it was **audited against real PG16, not trusted** — one real
  migration bug was found and fixed — then deployed). Tip after this + fix = `efd2f97`.
- `efd2f97` fix(db): 010 migration — `SET search_path` before `CREATE EXTENSION`
  (otherwise uuid-ossp lands in `public` and `uuid_generate_v4()` fails on a fresh schema).
- `434c8c7` initiatives: propose → review → publish workflow (public form, review queue,
  folder-on-approve, admin-create removed; `011` migration).
- `0b06b23` fix(auth): web pages read the real `erdpuls_session` cookie (login now works
  end-to-end). **`origin/main` HEAD at time of writing = `0b06b23`** — verify it hasn't moved.

### Config / env gotchas (hard-won)
- `.env`: `DATABASE_URL` must use **`127.0.0.1`** (not `localhost`) and an **alphanumeric**
  DB password (`%`/`$` break parsing/heredoc). `SECRET_KEY` set.
  **`BASE_URL=https://erdpuls.ubec.network`** (config.py defaults to `.eu` — wrong).
- **`INITIATIVES_DATA_DIR`** defaults to `/srv/ubec/erdpuls-data/initiatives` (config.py);
  `mkdir -p` it, owned by `ubec`, **outside the repo**. Only needs setting in `.env` to
  override the default path.
- `requirements.txt` needs `markdown` (OER library).
- **OER library** (`app/services/oer_library.py`) calls the GitHub **tree** API
  (rate-limited); set **`GITHUB_TOKEN`** in the service env to raise 60→5,000
  req/hr. Raw doc bodies use `raw.githubusercontent.com` (unlimited, no auth).
  30-min in-memory cache, so edits in `ubeccommon.github.io` take ≤30 min to show.
- **Migrations run as `postgres`, not `ubec`:** `psql -d ubec_erdpuls` as OS-user `ubec`
  fails with `role "ubec" does not exist`. Use
  `cat db/scripts/0NN.sql | sudo -u postgres psql -d ubec_erdpuls -v ON_ERROR_STOP=1`.

---

## LOCKED DECISIONS
- **Erdpuls Müllrose is the permanent working reference implementation**, kept intact at
  `/muellrose`; seeded as the flagship initiatives row (protected: can't be
  unpublished/deleted from the dashboard).
- **`/` is the network directory** of *published* initiatives (DB-backed).
- **Initiatives are authored publicly and moderated:** propose (`/initiatives/start`,
  unpublished) → admin review (`/admin/initiatives`) → publish. Admins review, not author.
- **Runtime-created initiative folders live in an external, gitignored data dir**
  (`/srv/ubec/erdpuls-data/…`), never in the repo tree — created on approve.
- Erdpuls uses **its own app-local auth + `/set-lang`**; canonical session cookie is
  `erdpuls_session` (Hub-SSO "Sign in" in the CDN nav is a **Phase-2 seam**).
- Canonical Erdpuls backend = **`erdpuls_dashboard`** (Collective Threshold app), NOT the
  earlier archived app (`/srv/ubec/_archive/erdpuls-oldapp-*`).

---

## OPEN THREADS (priority order)
1. **Rotate DB app-role + admin secrets (was #6 — now top priority).** The
   `ubec_erdpuls_app` password appeared repeatedly in terminal output this session.
   `ALTER ROLE ubec_erdpuls_app WITH PASSWORD '<new-alphanumeric>';` → update
   `DATABASE_URL` in `/srv/ubec/erdpuls/.env` → restart → scrub `~/.bash_history`.
2. **Extend DE/PL/UK coverage to remaining templates** — add missing language branches
   (esp. `uk`) across `/muellrose`, about, legal/*, model_*, offerings, auth. EN is base/
   fallback; ongoing native review of DE/PL/UK.
   **OER-library UK — DONE:** `_LANG_DIRS` now maps UK (`oer_library.py`), so the 16
   `UK/` OER docs + UK pathway in `ubeccommon.github.io` are indexed; `_COLLECTION_LABELS`
   gained `uk` labels (pending native review), the `library/index.html` filter chip row
   gained Українська, and `_PATHWAY_URLS["uk"]` is wired to the (live) UK maps HTML.
   Remaining: native review of the `uk` collection labels; optionally enable `pl`
   pathway maps (its HTML now also exists on Pages).
3. **De-Müllrose the shared/network-level pages** — `about`, `legal/imprint|privacy|terms`
   (also confirm **CC BY-SA**, verify Impressum details), `model_*`: make copy generic /
   protocol-level; keep place-specifics under `/muellrose`.
4. **Initiatives follow-ups (nice-to-haves):** an **edit** action in the review queue
   (fix a blurb/status before approving); **reviewer email notification** on new
   proposals; optional basic rate-limiting on the public `/initiatives/start` POST
   (currently honeypot only). Consider a generic `/{slug}` initiative page for
   dashboard-approved initiatives (currently card-only or external URL).
5. **Verify Müllrose interactive flows** — click offerings/contribute/login/dashboard
   under `/muellrose`; fix any link/redirect that assumes `/` = Müllrose home.
6. **`INSTRUCTIONS.md` §12/§13 + changelog** — reflect Erdpuls initiatives + auth fix;
   apply `patch_instructions_erdpuls_deploy.py` (dry-run first).
7. **Cleanup** — remove `templates/base.html.pre-consolidation` and the
   `.pre-consolidation` nginx vhost once satisfied.
8. **Phase 2** — Hub SSO; unify the nav "Sign in" with real single-sign-on.

## DONE (this session)
- **#3 data-driven directory** — DB-backed (`initiatives` table).
- **#4 "Start an initiative" onboarding** — public propose → admin review → publish.
- **Login bug** — public pages now read the real `erdpuls_session` session cookie.
- **OER library UK** — Ukrainian resources now surface in `/library` (indexer language
  map + filter chip + pathway-maps URL); template already carried `uk` UI strings.

## NOT IN SCOPE (Erdpuls module)
Keycloak/SSO build-out, token-reward on-chain logic, `mapservice`/`bioregional`
migrations, ecosystem-wide `uk` on other services, Hub management dashboard.

## CONNECTIONS
| Service | Relationship |
|---|---|
| `iot.ubec.network` (Hub) | observations target; future SSO; nav "Sign in" |
| `living-labs.ubec.network` | steward registration (some CTAs link here) |
| `design.ubec.network` | shared CSS + `ubec-nav.js` |
| `ubec.network` | portal; Erdpuls service card |
| `ubeccommon.github.io` (UBEC Open) | OER source — `/library` live-aggregates the `Pattern_Language_of_Place` repo via GitHub tree API + raw CDN |
| Stellar | UBECrc reciprocity token (Phase 2 logic) |

---
*© 2024–2026 Michel Garand · CC BY-SA 4.0 · GNU AGPL v3.0*
*Developed with Claude (Anthropic PBC)*
