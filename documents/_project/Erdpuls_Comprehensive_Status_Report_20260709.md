# Erdpuls — An Open Living Lab Protocol

## Comprehensive Status Report (Network / OER Initiative Level)

**Report Date:** 9 July 2026
**Prepared by:** Claude (Anthropic PBC), in collaboration with Michel Garand
**Module:** Erdpuls — `erdpuls.ubec.network`
**Canonical name:** *UBEC Erdpuls — An Open Living Lab Protocol* (per the protocol whitepaper)
**Scope:** the Erdpuls **protocol / network** as a whole — location-agnostic. **Erdpuls
Müllrose** appears here only as *one initiative* within the protocol (its flagship reference
implementation), not as the subject of the report.
**Supersedes:** the Müllrose-framed reports in `_project/` (Jan 2026), and the interim
9 July draft that inherited their Müllrose framing.

---

## Note on Framing (why this report was re-scoped)

The earlier status reports were titled "Erdpuls Müllrose Project" because, when they were
written, Erdpuls *was* a single site in Müllrose. That is no longer the correct frame. The
July 2026 work — the network/flagship split in the application and the `documents/`
reorganisation in commit `50fe101` — generalised Erdpuls into an **open living lab protocol**
of which Müllrose is one **initiative**. This report is therefore written at the protocol /
network level. Place-specific matters (the Müllrose campus, its buildings, its garden, its
local funding) belong to the Müllrose initiative and are scoped as such in §4, not treated as
the identity of Erdpuls as a whole.

---

## Verification Basis and Boundary

Grounded in direct inspection of the canonical repository
`github.com/ubeccommon/erdpuls_dashboard` (branch `main`, verified at commit `50fe101`,
9 July 2026), plus a close reading of the reorganised `documents/` set.

- **Repo-verified** — confirmed by reading files, routes, schema, git history, and the
  document tree.
- **Requires live verification** — depends on the running state of Hetzner `ubec-common`
  (49.13.167.206): the `ubec-erdpuls.service` unit, the live nginx vhost, the deployed tree
  position, and live PostgreSQL object counts. Not reachable during preparation; confirm by
  SSH before treating as fact. Nothing about live runtime is asserted here as verified.

---

## Executive Summary

Erdpuls is an **open living lab protocol**: a replicable pattern for a Living Laboratory and
Makerspace Garden that any bioregion, farm, school, or community can adopt on its own ground.
Its defining claim — stated in the canonical whitepaper — is that it is "a protocol rather
than a place," so it can take root anywhere. The protocol's **digital commons and four-element
token economy are live and site-independent**; what does not yet exist anywhere, Müllrose
included, is a full *physical* Erdpuls campus. That is the protocol's invitation, not a
completed deliverable.

The software module at `erdpuls.ubec.network` now expresses this two-tier model directly: the
root is a **network directory of initiatives**, and **Erdpuls Müllrose** is the **flagship
reference implementation** at `/muellrose`, which new initiatives are modelled on. In the
July consolidation the application was moved onto the shared UBEC design system, its
documentation licence corrected to CC BY-SA 4.0, Ukrainian added as a fourth language, and the
database schema reconstructed into a single canonical fresh-install file. The reorganised
`documents/` set mirrors the app: `protocol/` (location-agnostic OER) ↔ `/`, and
`initiatives/<slug>/` ↔ `/<slug>`.

The principal remaining work is breadth and hygiene: extending translation coverage (both UI
and OER), generalising any residually Müllrose-specific shared pages, making the initiatives
directory data-driven ahead of a second initiative, removing duplicated documents left by the
reorg, and rotating secrets exposed in earlier sessions.

---

## 1. What Erdpuls Is (Protocol-Level Orientation)

Erdpuls addresses the **Values–Action Gap** — the documented chasm in which a large majority
of young Europeans value sustainability but only a minority act on it — by uniting, on a
single site, a garden landscape (the Living Laboratory) and an adjacent making space (the
Makerspace) as one hybrid where science and making happen in the same square metres. It is
anchored in Ubuntu ("I am because we are") and embeds cooperation, reciprocity, mutualism, and
regeneration structurally through a token economy.

The canonical whitepaper (`documents/protocol/whitepaper/EN/`) defines the protocol through:

- **Seven Pillars** — Sustainability Literacy (Head), Citizen Science (Practice), Permaculture
  Design & Bio-Materials (Hands), Circular Economy & Repair (Loop), Reciprocal Economics
  (Exchange), Heritage Conservation & Place Identity (Roots), and Contemplative Practice &
  Ecological Consciousness (Heart).
- **Five functional domains** organising the making (circular-economy workshop / repair café,
  bio-materials laboratory, environmental sensing & data, digital fabrication, and the garden/
  residency capacity).
- **A four-element Stellar token economy** — UBEC (Air / Diversity, gateway access), UBECrc
  (Water / Reciprocity, earned through citizen science), UBECgpi (Earth / Mutualism, stable
  value), UBECtt (Fire / Regeneration, catalytic transformation).
- **The 4A pathway** — Awareness → Acknowledgement → Attitude → Action.
- **An adoption pattern**, not a franchise: three phases — Germinate, Grow, Mature & Radiate —
  by which any community brings an initiative into being at locally chosen scale, each mature
  initiative lowering the threshold for the next.

These are cited here as orientation; the whitepaper is the authoritative source and should not
be restated in full in a status report.

---

## 2. The Collective Threshold Model (protocol funding mechanism)

The funding mechanism that governs offerings across the protocol: transparent need → register
intention (separate from payment) → anonymous contribution to a collective pot → the offering
proceeds when the threshold is met → community-anonymous, operationally-known (aggregates
public, individual amounts never shown publicly). The reciprocal-economics business model adds
four **participation pathways** so no one is excluded: Full Rate, Supported Rate, Skills
Exchange, and UBECrc Tokens. This model is live on the Erdpuls Portal and is the conceptual
core exercised today by the Müllrose flagship.

---

## 3. Application Architecture — Network Tier + Initiatives (repo-verified)

The software now mirrors the protocol/initiative distinction. Confirmed in
`app/routers/web.py`:

| Route | Renders | Level | Purpose |
|-------|---------|-------|---------|
| `/` | `templates/network.html` | **Protocol / network** | UBEC Erdpuls intro + directory of location-based initiatives |
| `/muellrose` | `templates/index.html` | **Initiative** | Erdpuls Müllrose — flagship reference implementation (live offerings, regeneration fund) |
| `/set-lang/{lang}` | — | Shared | Language switch; accepts `en`, `de`, `pl`, `uk` |

`/` carries minimal context (language, optional user); `/muellrose` carries the verbatim
former single-site behaviour. This is a locked decision: `/` belongs to the network as a
whole; Müllrose is the permanent working reference implementation at `/muellrose`; new
initiatives are modelled on it.

**nginx implication (requires live verification):** the app now owns `/`; the former static
`location = / /en/ /de/ /pl/` blocks are expected to be removed, leaving the `:8004` proxy,
`.well-known`, and dotfile-deny. Confirm against the live vhost.

---

## 4. Erdpuls Müllrose — The Flagship Initiative (scoped, not the whole)

Müllrose is **one initiative**, presented here in its correct scope. It is the flagship
reference implementation: Müllrose, Brandenburg, in Naturpark Schlaubetal, developing a
3,000 m² living laboratory with heritage buildings. Its **place-specific** documents — the
detailed Müllrose whitepaper, local funding and partnerships, particular needs — belong under
`documents/initiatives/muellrose/`, deliberately kept out of the location-agnostic `protocol/`
set. In the app, everything place-specific lives under `/muellrose`; the network root must not
assume `/` equals Müllrose (see open thread #5). Müllrose is the model other initiatives copy,
not the definition of Erdpuls.

---

## 5. Documentation Model (repo-verified; post-spec reorg)

Commit `50fe101` (9 July 2026, **after** the module spec's 8 July "last updated") restructured
`documents/` to mirror the app and to separate concerns cleanly:

| Folder | Holds | Mirrors |
|--------|-------|---------|
| `_project/` | Project-internal technical docs — status reports, schema docs, service README | — (internal) |
| `protocol/` | Location-agnostic OER — whitepaper, collective-threshold-model, reciprocal-economics business model; per-language sub-folders; Markdown source + ODT render | `/` (network landing) |
| `initiatives/` | Per-initiative place-specific material; `_TEMPLATE/` + `muellrose/` | `/<slug>` |

**OER translation coverage (per `protocol/README.md`):** whitepaper and threshold model are
**EN only** (DE/PL/UK to follow); the business model is EN/DE/PL/UK, with UK AI-generated and
pending native review. This documentation-parity gap is distinct from the app's UI-translation
gap (§6).

**Cleanup finding — duplicated originals.** The reorg placed the protocol documents under
`protocol/<doc>/<lang>/` but left the pre-reorg originals at `documents/` root. Byte-for-byte
diffs confirm these root-level files are **identical** to the `protocol/` copies:
`erdpuls_protocol_whitepaper.md`, `erdpuls_collective_threshold_model.md`, the four
`erdpuls_reciprocal_economics_business_model_*.md`, and the five loose `.odt` files — plus the
stray LibreOffice lock file `.~lock.Erdpuls_Protocol_Whitepaper.odt#`. Roughly twelve
redundant files to remove once `protocol/` is confirmed authoritative.

---

## 6. Technical State (repo-verified file; live counts require verification)

- **Design consolidation** — `templates/base.html` rebuilt onto the shared UBEC design
  system: `data-ubec-service="erdpuls"`, Bunny Fonts, `ubec-design-system.css` +
  `nav-styles.css` + `ubec-nav.js`, self-rendered CC BY-SA footer. Removed: Google Fonts, the
  Cloudflare email-decode script + `/cdn-cgi` link, the bespoke Müllrose header/footer, the
  CC BY-NC-SA notice. App keeps its own login/logout + `/set-lang` in a slim `.app-subnav`;
  the CDN nav's Hub-SSO login and language switcher are suppressed. Satisfies the GDPR-driven
  bans on Google Fonts and Cloudflare.
- **Database** — DB `ubec_erdpuls`, schema `erdpuls_threshold`; app sets `search_path` per
  connection, no `create_all`. Canonical fresh-install schema `db/schema_complete.sql`: repo
  inspection confirms 9 tables, 6 FK references, 1 trigger, plus functions, views, seeds, and
  grants to `ubec_erdpuls_app`. Documented as 93 columns / 22 indexes; the "22" is the live
  catalogue count (includes PK/UNIQUE auto-indexes) vs. 10 explicit `CREATE INDEX` in the file
  — consistent, but confirm live with `psql`. `users.role` defaults to `member` (reconciled
  with `users_role_check`); admin bootstrapped via `create_admin.py`.
- **API surface (verified in `app/routers/api.py`, prefix `/api`)** — offerings list/detail/
  progress/create; register; contribute euro/token/hours; `fund/balance`, `fund/transactions`;
  `rates/tokens`, `rates/hours`; `session/refresh`; `admin/offerings/{id}/confirm`; plus
  `/health` and docs at `/api/docs` + `/api/redoc`. Hours rates and the 70-tokens/€1 rate are
  seeded in `schema_complete.sql`.
- **i18n (app UI)** — EN/DE/PL cover the whole app; UK covers the network landing + shell
  (`base.html`); untranslated pages fall back to EN. The shared CDN nav is intentionally not
  given `uk` yet.
- **Deployment** — deploy-by-pull on `ubec-common`: source of truth
  `~/ubec_commons/ubec_erdpuls` → push; live `/srv/ubec/erdpuls` → pull → restart
  `ubec-erdpuls.service` (nginx 1.24, PostgreSQL 16, uvicorn `:8004 --workers 2`). The bundled
  `deploy/` still ships **Caddy** artefacts (`caddy-site.conf`, `erdpuls-threshold.service`),
  which are legacy and do not match the live nginx model. Config gotchas persist:
  `DATABASE_URL` must use `127.0.0.1` with an alphanumeric password; `BASE_URL` must be set
  explicitly (config.py defaults to a wrong `.eu`); `markdown` must be present in
  `requirements.txt` (it is, `>=3.5`).

---

## 7. Change Delta Since the January 2026 Reports

1. **Frame** — single Müllrose site → **Erdpuls as a protocol** with Müllrose as one
   initiative (network directory `/` + flagship `/muellrose`).
2. Bespoke Müllrose shell → shared UBEC design system; Google Fonts and Cloudflare removed.
3. Documentation licence CC BY-NC-SA 4.0 → **CC BY-SA 4.0**; © line standardised to
   **© 2024–2026 Michel Garand**.
4. **Ukrainian (UK)** added as a fourth peer language (network landing + shell today).
5. Fresh-clone bootstrap fixed: `db/schema_complete.sql`, `markdown` dep, `create_admin.py`,
   role default → `member` (PR #2).
6. `documents/` reorganised into `_project/` + `protocol/` + `initiatives/` (protocol vs.
   place-based), mirroring the app.
7. Terminology on the network landing tightened ("13 Questions" → "13 Questions to the Soil";
   "Müllrose is the first" removed).

---

## 8. Open Threads and Priorities

1. **Extend UI translation coverage** (DE/PL/UK) to every remaining template so all four
   languages cover the whole app; ongoing native review. EN is the base/fallback.
2. **Extend OER translation coverage** — bring the whitepaper and collective-threshold-model
   to DE/PL/UK; complete native review of UK business-model text.
3. **De-Müllrose the shared/network-level pages** — `about`, `legal/*`, `model_*`: make copy
   generic and protocol-level; keep place-specifics under `/muellrose`.
4. **Make the initiatives directory data-driven** — replace the hardcoded Müllrose card in
   `network.html` with an `initiatives` table/config (name, location, status, blurb, url)
   before initiative #2.
5. **Design "Start an initiative" onboarding** — the protocol's adoption pattern needs a real
   intake flow, not just a link to Living Labs register.
6. **Verify flagship interactive flows** under `/muellrose`; fix any link/redirect assuming
   `/` = Müllrose home.
7. **Rotate secrets** (highest urgency) — DB app-role and admin passwords exposed in earlier
   history; rotate and scrub `~/.bash_history`.
8. **Cleanup** — remove the ~12 duplicated `documents/` root files and the `.~lock` file
   (§5); remove `templates/base.html.pre-consolidation`, `templates/index_orig.html`, and the
   `erdpuls.ubec.network.pre-consolidation` nginx file once satisfied.
9. **Sync the written record** — apply the `INSTRUCTIONS.md` §12/§13 + changelog patch and
   record commit `50fe101` in the spec/changelog.
10. **Phase 2 — Hub SSO**: unify the nav "Sign in" with real single sign-on.
11. **Terminology decision (for the maintainer)** — `INSTRUCTIONS.md` locks "regenerative, not
    sustainable," but the canonical whitepaper uses **"Sustainability Literacy"** as a fixed
    pillar name and in its title. Decide whether the locked rule yields to the protocol's
    established proper noun, or whether the pillar is renamed. This needs an owner decision;
    it should not be resolved by silent find-replace.

**Not in scope for this module:** Keycloak/SSO build-out, on-chain token-reward logic,
`mapservice`/`bioregional` migrations, ecosystem-wide `uk` on other services, Hub management
dashboard.

---

## 9. Risk and Attention Summary

- **Security (act first):** secrets rotation (thread #7).
- **Framing consistency:** ensure any remaining Müllrose-as-whole language (in shared pages,
  the README, older docs) is corrected to protocol-vs-initiative, matching the recent
  documents.
- **Documentation hygiene:** duplicated `documents/` root files risk drift between two copies
  of the same OER; remove them so `protocol/` is unambiguously authoritative.
- **Deployment drift:** legacy Caddy artefacts vs. the live nginx model; reconcile in `README`
  and `deploy/`.
- **Unverified runtime:** live service/nginx/DB state must be confirmed by SSH before being
  reported as fact.

---

*© 2024–2026 Michel Garand · CC BY-SA 4.0 · GNU AGPL v3.0*
*This project is being developed with assistance from Claude (Anthropic PBC). All strategic
decisions, philosophical positions, and project commitments are those of the author.*
