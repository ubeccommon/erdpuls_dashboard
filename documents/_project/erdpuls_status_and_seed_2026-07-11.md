# Erdpuls — Session Status Report & Next-Session Seed Prompt
**Date:** 2026-07-11 · **Repo:** `github.com/ubeccommon/erdpuls_dashboard` (branch `main`)
**origin/main HEAD at close:** `b31afbe` (verify it hasn't moved before acting)
**Live server:** Hetzner `ubec-common` (`49.13.167.206`) · service `ubec-erdpuls.service` on :8004 · Caddy reverse-proxy · PostgreSQL 16, schema `erdpuls_threshold`

---

## 1. What this session accomplished

Two workstreams, both fully deployed and verified live: the **OER Library / Learning Pathways** feature, and **thread #3 de-Müllrosing**.

### A. OER Library — Ukrainian + pathway maps (commits `d7e0a77`, `ecd5779`, `8b5671f`, `0df9899`, `e0c68d9`)
- **How `/library` works (confirmed from code):** it is *not* stored in this repo. It live-aggregates a **separate** repo, `github.com/ubeccommon/ubeccommon.github.io` (the "UBEC Open" Pattern Language of Place content), via `app/services/oer_library.py`: the file **tree** comes from the GitHub API (`git/trees/main?recursive=1`, rate-limited — optional `GITHUB_TOKEN` lifts 60→5,000/hr), raw bodies from `raw.githubusercontent.com` (no limit), Markdown→HTML server-side with the `markdown` lib, cached in-memory 30 min.
- **UK was invisible** because `_LANG_DIRS` mapped only EN/DE/PL; language is detected from the `EN/DE/PL/UK` path segment, so all 16 `UK/` OER docs were silently dropped. Fix added `"UK":"uk"`, `uk` collection labels (machine-drafted), and the missing Українська filter chip. UK now indexes **16** resources (verified live).
- **Pathway maps rendered blank** because the page iframed `ubeccommon.github.io` cross-origin (parent sets no CSP/X-Frame-Options, so the block is Pages-side). Fixed by serving the static, self-contained map HTML **same-origin** via a new route `GET /library/pathways/frame?lang=…` (fetches raw + 30-min cache via new `oer_library.fetch_raw_html`). This removed the cross-origin / X-Frame-Options / Pages-availability dependency entirely.
- **Language surfaces made data-driven** from a single source of truth, `_PATHWAY_URLS` (in `app/routers/web.py`): the pathways toolbar tabs *and* the `/library` interactive-card badges both loop over `list(_PATHWAY_URLS)`. **PL enabled** (its maps HTML is live), so **EN/DE/PL/UK** are consistent across the landing card, the pathways tabs, and the frame route.

### B. Thread #3 de-Müllrosing (commits `5762b95`, `b31afbe`)
- **Shared network-level pages** genericized "Erdpuls Müllrose" → "Erdpuls": body copy in `model_reciprocity.html` and `model_pathways.html` (all 3 lang blocks each); `<title>` brand suffix in `offerings.html`, `offering.html`, `contribute_confirm.html`.
- **Network-wide email identity** genericized: `config.py` `smtp_from_name` default → "Erdpuls" (+ `env_example`); the **live** `send_password_reset_email` in `app/email.py` (auth imports `..email`) → "Erdpuls" in all 3 lang blocks. Confirmed live `.env` does **not** pin `SMTP_FROM_NAME`, so the code default applies.
- **Deliberately preserved (load-bearing / flagship):** `index.html` hero (rendered at `/muellrose` — it *is* the flagship page); `legal_imprint/privacy/terms.html`; `send_contribution_confirmation` email (offerings are flagship-scoped); code comments/docstrings and the `db/scripts/010_initiatives.sql` seed row `('muellrose','Erdpuls Müllrose',…)` (real flagship data).
- **Routing facts that drove the decisions:** `/` → `network.html` (already clean); `/muellrose` → `index.html` (flagship).

---

## 2. Commits landed this session (`da52214..b31afbe`)
```
b31afbe content(de-müllrose): genericise network-wide email identity to 'Erdpuls'
5762b95 content(de-müllrose): genericise shared network-level pages to 'Erdpuls'
e0c68d9 docs(spec): correct OER Library pathways to same-origin proxy; UK/PL live
8b5671f fix(library): data-driven pathway badges on landing page; enable PL
ecd5779 fix(pathways): serve maps same-origin + show all wired lang tabs (UK)
0df9899 docs(spec): document OER Library architecture; record UK support as done
d7e0a77 fix(library): surface Ukrainian (UK) OER resources
```
Spec (`documents/_project/Erdpuls_Module_Spec.md`) is current with all of the above.

---

## 3. Verified live state at close
- `/library?lang_filter=uk` → 16 UK resources; landing-card badges show EN/DE/PL/UK.
- `/library/pathways` → map renders via same-origin `/library/pathways/frame`; toolbar tabs EN/DE/PL/UK; `frame?lang=pl` and `?lang=uk` return HTTP 200.
- `/model/reciprocity`, `/model/pathways`, `/offerings` → 0 "Müllrose".
- Password-reset from-name resolves to "Erdpuls" (code default, `.env` not pinned); service `active`.

---

## 4. Open threads (priority order)

**#7 Cleanup (ready — two clear `git rm` targets surfaced this session):**
- `app/email_password_reset.py` — **dead duplicate** of `send_password_reset_email`, imported nowhere (auth uses `..email`). Still contains "Erdpuls Müllrose" (7 hits) but is unreachable.
- `templates/index_orig.html` — stale `_orig` backup, rendered by no route (contains a Müllrose location block).
- (Also per spec #7: `templates/base.html.pre-consolidation` + the `.pre-consolidation` nginx vhost — verify on server; the template artifact appears already gone.)

**#4 Initiatives follow-ups (feature work; grep shows unbuilt — verify per-file first):**
- Admin **edit** action in the review queue (fix blurb/status before approving).
- **Reviewer email notification** on new proposals.
- Optional rate-limiting on the public `/initiatives/start` POST (currently honeypot only).

**#5 Müllrose flow verification (interactive — operator click-through):** click offerings/contribute/login/dashboard under `/muellrose`; fix any link/redirect that assumes `/` = Müllrose home. Best delivered as a checklist + `curl` probes.

**#3 residual (content/operator, not code):** native review of the machine-drafted `uk` OER collection labels; the German Impressum `[Straße und Hausnummer]` TMG placeholder; PL OER *curriculum* is sparse in the source repo (content gap in `ubeccommon.github.io`, not code).

**#6 INSTRUCTIONS.md refresh:** lives outside this repo (the `patch_instructions_erdpuls_deploy.py` script is not tracked here) — needs the meta-repo / global file.

**#8 Phase 2 SSO:** Hub single-sign-on; explicitly out of near-term scope.

**Pre-existing, unresolved:** `erdpuls.org` vs `erdpuls.ubec.network` domain inconsistency in the codebase.

---

## 5. Key learnings / decisions (carry forward)
- **`_PATHWAY_URLS` is now the single source of truth** for pathway languages (tabs, badges, frame route). Add a language there and it appears everywhere; don't re-hardcode language lists in templates.
- **Same-origin proxy pattern** (`/library/pathways/frame` + `fetch_raw_html`) is the reliable way to embed external static HTML — reuse it rather than cross-origin iframes.
- **De-Müllrosing is routing-dependent:** genericize only what renders at network-level (`/`, `/model/*`, `/offerings`, network-wide emails). Keep `/muellrose` flagship copy, legal pages, contribution emails, seed data, and code comments.
- **`config.py` defaults vs `.env`:** changing a default only matters if `.env` doesn't override it — always check the live `.env` for env-driven settings.
- **Two `send_password_reset_email` exist;** only `app/email.py`'s is wired. `email_password_reset.py` is dead.
- **Discipline that held all session:** verify `origin/main` HEAD at the start of every change (it moved 6× this session as patches landed); base patches on the *current* HEAD; `git format-patch` → `git am -3`; keep the `patches/` dir untracked (don't `git add -A`).

---

## 6. Deploy workflow (deploy-by-pull)
```bash
# Author clone (has push access)
cd /home/ubec/ubec_commons/ubec_erdpuls
git checkout main && git pull                 # confirm HEAD
git am -3 patches/<patch-file>.patch
git push
# Live server (pull-only)
cd /srv/ubec/erdpuls && git pull && sudo systemctl restart ubec-erdpuls.service
```
Notes: patches land in `patches/` inside the author clone — keep untracked. Operator restarts even for template-only changes (standing preference). Claude's sandbox cannot reach the live server or `*.github.io`; use `raw.githubusercontent.com` / GitHub API to verify source content, and hand verification `curl`s to the operator for live checks.

---

## 7. Seed prompt for the next conversation
*(Copy the block below as the first message of a new chat.)*

```
Canonical Erdpuls spec: documents/_project/Erdpuls_Module_Spec.md in
github.com/ubeccommon/erdpuls_dashboard (branch main). Read it — and the global
INSTRUCTIONS.md — at session start; update the repo spec file at session close.
Truth hierarchy: git repo > spec > conversation. Verify origin/main HEAD before
proposing changes (it was b31afbe at the end of the last session — confirm it
hasn't moved).

Context from last session (all deployed & verified live):
- OER Library (/library) fully multilingual EN/DE/PL/UK. It live-aggregates the
  separate repo ubeccommon.github.io via GitHub tree API + raw CDN (30-min cache);
  code in app/services/oer_library.py. Learning Pathway Maps now render SAME-ORIGIN
  via /library/pathways/frame (not a cross-origin Pages iframe); pathway langs are
  data-driven from _PATHWAY_URLS in app/routers/web.py — single source of truth for
  tabs + landing-card badges.
- Thread #3 de-Müllrosing DONE: shared network-level pages (/model/*, /offerings,
  offering/contribute titles) and network-wide email identity (smtp_from_name +
  password-reset in app/email.py) now say "Erdpuls". KEPT as flagship/load-bearing:
  index.html (rendered at /muellrose), legal_* pages, send_contribution_confirmation,
  and the db seed row.

Deploy model: author in /home/ubec/ubec_commons/ubec_erdpuls, patches via
git format-patch → git am -3 (patches/ dir, keep untracked) → push; live tree
/srv/ubec/erdpuls is pull-only: `cd /srv/ubec/erdpuls && git pull && sudo
systemctl restart ubec-erdpuls.service`. Your sandbox can't reach the live server
or *.github.io — verify source via raw.githubusercontent.com / the GitHub API and
hand live-check curls to me.

I primarily code in Python.

Let's start with: [PICK ONE]
  (a) #7 cleanup — git rm the dead app/email_password_reset.py and the stale
      templates/index_orig.html (verify unreferenced first).
  (b) #4 initiatives follow-ups — admin edit action in the review queue and/or
      reviewer-email notification on new proposals (read the files first; grep
      suggested they're unbuilt).
  (c) #5 Müllrose flow verification — checklist + curl probes for the /muellrose
      offerings/contribute/login/dashboard flows.
Begin by reading the spec + INSTRUCTIONS.md and confirming origin/main HEAD, then
tell me what you can vs. can't verify from the sandbox.
```
