# 🌱 UBEC Erdpuls — An Open Living Lab Protocol

**Erdpuls by UBEC · `erdpuls.ubec.network`** — the Erdpuls network application.
Part of the UBEC Commons (Ubuntu Bioregional Economic Commons) network.

Erdpuls is an **open living lab protocol** — a replicable pattern for a Living Laboratory and
Makerspace Garden that any community can adopt on its own ground. Being a protocol rather than
a place, it can take root anywhere. This repository is the network **application** (built with
FastAPI): its root is a directory of initiatives, and **Erdpuls Müllrose** is the flagship
reference implementation that new initiatives are modelled on.

> "The community holds each offering into being."

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Docs: CC BY-SA 4.0](https://img.shields.io/badge/Docs-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

**Live Platform:** https://erdpuls.ubec.network
**API Documentation:** https://erdpuls.ubec.network/api/docs

---

## Table of Contents

- [Overview](#overview)
- [Network & Flagship](#network--flagship)
- [The Collective Threshold Model](#the-collective-threshold-model)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Role System](#role-system)
- [Contribution Types](#contribution-types)
- [Quick Start](#quick-start-development)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Database Documentation](#database-documentation)
- [Licensing](#licensing)
- [Contact](#contact)

---

## Overview

Erdpuls is an **open living lab protocol**: a Living Laboratory and Makerspace Garden where
technology and nature collaborate to understand living systems, and where making, growing,
observing, and repairing converge. It addresses the "Values–Action Gap" between environmental
awareness and action, is anchored in Ubuntu philosophy ("I am because we are"), and uses a
four-element token economy on the Stellar network. Because it is a protocol rather than a
place, any bioregion, farm, school, or community can adopt it on its own ground. The digital
commons and token economy are already live; the full *physical* campus is the pattern
communities are now invited to build. The canonical, location-agnostic protocol documents
(whitepaper, models) live in [`documents/protocol/`](documents/protocol/).

This repository is the Erdpuls **network application**. It implements the **Collective
Threshold Model** — a community funding mechanism combining anonymous contributions with
transparent needs — and serves the network directory at `/`. **Erdpuls Müllrose** (a 3,000 m²
living laboratory in Naturpark Schlaubetal, Brandenburg) is *one initiative* within the
protocol: the flagship reference implementation, served at `/muellrose`. Erdpuls is one module
of the wider UBEC Commons ecosystem and shares its design system, fonts, and legal framework.

---

## Network & Flagship

Erdpuls is structured as a network tier plus a preserved flagship:

| Route | Renders | Purpose |
|-------|---------|---------|
| `/` | `templates/network.html` | **UBEC Erdpuls** network landing — intro + directory of location-based initiatives |
| `/muellrose` | `templates/index.html` | **Erdpuls Müllrose** — flagship / reference implementation (live offerings, regeneration fund) |

`/muellrose` carries the original single-site behaviour verbatim. New place-based initiatives
are modelled on Müllrose; the root belongs to the network as a whole, not to any single place.
The initiatives directory is currently a hardcoded card in `network.html` and is planned to
become data-driven before a second initiative is added.

---

## The Collective Threshold Model

The Collective Threshold Model transforms how community offerings are funded:

1. **Transparent Need** — Each offering publishes exactly what resources it needs
2. **Register Intention** — People express desire to participate (separate from payment)
3. **Anonymous Contribution** — Everyone contributes to a collective pot anonymously
4. **Threshold Met** — When the threshold is reached, the offering happens
5. **No One Knows** — No one knows who contributed what, dissolving stigma

### Engagement Pathways

| Pathway | Description | Registration | Contribution |
|---------|-------------|--------------|--------------|
| **Participate Only** | Express intention without financial commitment | ✅ | ❌ |
| **Support Only** | Contribute without participating | ❌ | ✅ |
| **Support & Participate** | Both contribute and participate | ✅ | ✅ |

### Privacy Model

> **Community-Anonymous, Operationally-Known**

- **Public visibility:** Aggregates only (total amount, contributor count)
- **Organizer visibility:** Individual contributions + linked contact info
- **No individual amounts displayed publicly**

---

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | FastAPI + SQLAlchemy | Python web framework |
| Database | PostgreSQL 16 | Database `ubec_erdpuls`, schema `erdpuls_threshold` |
| Frontend | Jinja2 templates + vanilla JS | Server-side rendering |
| Design | Shared UBEC design system (CDN) + Bunny Fonts | `design.ubec.network/v1/`; DM Serif Display / DM Sans / JetBrains Mono |
| Languages | EN / DE / PL / UK | DE/PL cover the whole app; UK covers the network landing + shell (rest fall back to EN) |
| Web server | nginx 1.24 | Reverse proxy → uvicorn on `127.0.0.1:8004` |
| Runtime | systemd (`ubec-erdpuls.service`) | `User=ubec`, `uvicorn app.main:app --port 8004 --workers 2` |
| Host | Ubuntu (Hetzner, EU) | EU-hosted only; no Cloudflare, no Google Fonts (GDPR) |

---

## Project Structure

```
erdpuls_dashboard/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entry point (docs at /api/docs, /api/redoc; /health)
│   ├── config.py                   # Pydantic settings (DB, SMTP, BASE_URL)
│   ├── database.py                 # SQLAlchemy setup; sets erdpuls_threshold search_path
│   ├── models.py                   # ORM models (User, Offering, Contribution, token_rates, …)
│   ├── schemas.py                  # Pydantic API schemas
│   ├── auth.py                     # Sessions / auth utilities
│   ├── auth_routes_password_reset.py
│   ├── email.py / email_password_reset.py   # Multilingual email
│   ├── roles.py                    # Role hierarchy & permissions
│   ├── routers/
│   │   ├── api.py                  # JSON API (prefix /api)
│   │   ├── web.py                  # HTML routes (/, /muellrose, /set-lang, …)
│   │   ├── auth.py                 # Login, register, password reset
│   │   └── admin.py                # Admin panel
│   └── services/                   # e.g. oer_library.py (renders markdown OER)
├── templates/                      # Jinja2, EN/DE/PL/UK inline
│   ├── base.html                   # Consolidated UBEC shell (design system, Bunny fonts)
│   ├── network.html                # Network landing (/)
│   ├── index.html                  # Müllrose flagship (/muellrose)
│   ├── about.html · offerings.html · contribute*.html · model_*.html
│   ├── legal_imprint.html · legal_privacy.html · legal_terms.html
│   ├── auth/ · admin/ · library/
├── static/
│   ├── css/                        # style.css, auth-additions.css, …
│   └── js/
├── db/
│   ├── schema_complete.sql         # ★ canonical fresh-install schema
│   ├── scripts/                    # historical SQL migrations
│   └── *_schema_documentation_generator.py
├── deploy/
│   ├── deploy.sh · DEPLOY.md
│   ├── erdpuls-threshold.service   # legacy (see Deployment note)
│   └── caddy-site.conf             # legacy (see Deployment note)
├── documents/
│   ├── _project/                   # status reports, schema docs, service README
│   ├── protocol/                   # OER whitepaper / model / business model (EN/DE/PL/UK)
│   └── initiatives/                # per-initiative material (_TEMPLATE/, muellrose/)
├── create_admin.py                 # bootstrap an admin user
├── run.py                          # dev server runner
├── requirements.txt
└── env_example                     # copy to .env
```

---

## Features

### Implemented ✅

- **Network directory + flagship** — `/` lists initiatives; `/muellrose` is the reference implementation
- **Consolidated UBEC design system** — shared CDN CSS + nav, Bunny Fonts, self-rendered footer
- **Multilingual UI** — EN/DE/PL fully; UK on the network landing + shell (rest fall back to EN)
- **User Authentication** — Login, registration, secure sessions
- **Password Reset** — Secure tokens with 1-hour expiry
- **Session Timeout** — 30-minute inactivity timeout with warnings
- **Five-Tier Role System** — Member, Creator, Facilitator, Moderator, Admin
- **Offerings Management** — CRUD with multilingual support
- **Delivery Language** — Specify workshop languages
- **Character Validation** — Defense-in-depth across all layers
- **Registration Flow** — Intention separate from contribution
- **Contribution Flow** — Euro, tokens, hours with confirmation
- **Privacy Model** — Separate contacts table
- **Admin Dashboard** — User and offering management
- **Progress Tracking** — Threshold visualization
- **Regeneration Fund** — Balance + transaction tracking for surplus/shortfall
- **OER Library** — Markdown-rendered open educational resources (`/library`)
- **Legal Pages** — Impressum, Privacy Policy, Terms of Service
- **Database Documentation Generator** — Schema documentation tool

### Planned 📋

- Extend DE/PL/UK translation coverage to every template
- Data-driven initiatives directory (replace hardcoded card)
- "Start an initiative" onboarding flow
- Threshold notification system
- Hub SSO (unify nav "Sign in" — Phase 2)
- UBECrc token blockchain integration (Stellar — Phase 2)

---

## API Endpoints

All API routes are served under the `/api` prefix.

### Offerings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/offerings` | GET | List all open offerings |
| `/api/offerings/{id}` | GET | Get offering details |
| `/api/offerings/{id}/progress` | GET | Funding progress (aggregates only) |
| `/api/offerings` | POST | Create an offering (role-gated) |
| `/api/offerings/{id}/register` | POST | Register intention to participate |
| `/api/offerings/{id}/contribute/euro` | POST | Euro contribution |
| `/api/offerings/{id}/contribute/token` | POST | Token contribution |
| `/api/offerings/{id}/contribute/hours` | POST | Hours contribution |

### Fund & Rates

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fund/balance` | GET | Regeneration Fund balance |
| `/api/fund/transactions` | GET | Regeneration Fund transactions |
| `/api/rates/tokens` | GET | Current token exchange rate |
| `/api/rates/hours` | GET | Hours contribution rates |

### System & Admin

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/session/refresh` | POST | Refresh session cookie |
| `/api/admin/offerings/{id}/confirm` | POST | Confirm an offering (admin) |
| `/api/docs` | GET | Interactive API documentation (Swagger) |
| `/api/redoc` | GET | ReDoc API documentation |
| `/health` | GET | Health check endpoint |

> Endpoints above were verified against `app/routers/api.py` and `app/main.py`. Always
> confirm against `https://erdpuls.ubec.network/api/docs` (or `/openapi.json`) before relying
> on a specific shape.

---

## Role System

### Five-Tier Hierarchy

| Role | Level | Description | Capabilities |
|------|-------|-------------|--------------|
| `member` | 10 | Default for new registrations | Participate, contribute |
| `creator` | 20 | Content creators | Create offerings (requires approval) |
| `facilitator` | 30 | Trusted creators | Direct publishing without approval |
| `moderator` | 50 | Community managers | Approve offerings, access admin panel |
| `admin` | 100 | Full access | Complete system access |

New registrations default to `member` (enforced in `app/models.py` and the
`users_role_check` constraint).

### Permission Matrix

| Permission | member | creator | facilitator | moderator | admin |
|------------|--------|---------|-------------|-----------|-------|
| View Offerings | ✅ | ✅ | ✅ | ✅ | ✅ |
| Participate | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contribute | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create Offering | ❌ | ✅ | ✅ | ✅ | ✅ |
| Publish Direct | ❌ | ❌ | ✅ | ✅ | ✅ |
| Approve Offerings | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage Users | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Contribution Types

### Euro
Direct monetary contribution in EUR.

### Token
UBECrc tokens earned through environmental stewardship. Default exchange rate: **70 tokens =
€1** (`token_rates.tokens_per_eur`, seeded at 70.0).

### Hours
Pre-arranged work valued by category. Rates below reflect the seed data in
`db/schema_complete.sql`:

| Category | EUR/Hour | Description |
|----------|----------|-------------|
| `garden_labor` | €11.00 | Weeding, planting, harvesting, composting, watering |
| `administrative` | €12.50 | Communication, scheduling, outreach, event support |
| `skilled_labor` | €20.00 | Carpentry, electrical, sensor installation, equipment repair |
| `translation` | €22.50 | DE/EN/PL translation, documentation, content creation |
| `knowledge_sharing` | €27.50 | Leading a session, mentoring, traditional knowledge transmission |
| `technical_support` | €30.00 | Data processing, sensor calibration, web development |

---

## Quick Start (Development)

### Prerequisites

- Python 3.10+
- PostgreSQL 16 (14+ likely works; production is 16)
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/ubeccommon/erdpuls_dashboard
cd erdpuls_dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp env_example .env
# Edit .env with your database credentials (see Environment Variables)

# Create the database and load the canonical schema (first time only)
createdb ubec_erdpuls
psql -d ubec_erdpuls -f db/schema_complete.sql

# Bootstrap an admin user
python create_admin.py

# Run development server
python run.py
```

Visit http://localhost:8004 — API docs at http://localhost:8004/api/docs

---

## Environment Variables

Create a `.env` file in the project root (copy from `env_example`):

```env
# Database
# Use 127.0.0.1 rather than localhost (localhost can resolve to ::1 and hit an auth quirk).
# Use an alphanumeric password: '%' breaks URL parsing and '$' breaks shell/heredoc handling.
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/ubec_erdpuls

# Security
SECRET_KEY=<generated-secret-key>
DEBUG=false

# Application
# Must be set explicitly — config.py defaults to a .eu value that is wrong for this deployment.
BASE_URL=https://erdpuls.ubec.network

# SMTP Configuration (port 465 / SSL)
SMTP_HOST=mail.ubec.network
SMTP_PORT=465
SMTP_USER=erdpuls@ubec.network
SMTP_PASSWORD=<password>
SMTP_USE_TLS=false
SMTP_FROM_EMAIL=erdpuls@ubec.network
SMTP_FROM_NAME=Erdpuls Müllrose
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deployment

Production runs on Hetzner (`ubec-common`) behind **nginx 1.24**, using a **deploy-by-pull**
model. The live systemd unit is **`ubec-erdpuls.service`**.

> **Note on `deploy/`:** the bundled `deploy/caddy-site.conf` and
> `deploy/erdpuls-threshold.service` describe an earlier **Caddy**-based setup and are
> **legacy**. The live deployment uses nginx and the `ubec-erdpuls.service` unit described
> here.

### Deploy-by-pull

```bash
# On the server, in the live tree:
cd /srv/ubec/erdpuls
git pull
sudo systemctl restart ubec-erdpuls
```

`.env` and `venv/` are gitignored, so `git pull` never touches secrets or the virtualenv.

### Systemd (live unit)

```
[Service]
User=ubec
WorkingDirectory=/srv/ubec/erdpuls
EnvironmentFile=/srv/ubec/erdpuls/.env
ExecStart=<venv>/bin/uvicorn app.main:app --port 8004 --workers 2
```

### Useful Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl status ubec-erdpuls` | Check app status |
| `sudo systemctl restart ubec-erdpuls` | Restart app |
| `sudo journalctl -u ubec-erdpuls -f` | View live logs |
| `sudo journalctl -u ubec-erdpuls -n 100` | View last 100 log lines |

### Architecture

```
Internet → nginx (80/443)
              │
              └── erdpuls.ubec.network → 127.0.0.1:8004 (uvicorn, 2 workers)
```

See `deploy/DEPLOY.md` for the detailed deployment guide.

---

## Database Documentation

Canonical fresh-install schema: **`db/schema_complete.sql`** (schema `erdpuls_threshold`).

Generate schema documentation:

```bash
cd db/
python erdpuls_schema_documentation_generator.py \
  --host 127.0.0.1 \
  --database ubec_erdpuls \
  --user <username> \
  --password <password> \
  --format markdown
```

Output formats: `markdown`, `json`, `html`

### Current Schema Statistics

| Metric | Count |
|--------|-------|
| Tables | 9 |
| Columns | 93 |
| Relationships (FKs) | 6 |
| Indexes | 22 |

> The schema file contains 10 explicit `CREATE INDEX` statements; the "22 indexes" figure is
> the live catalogue count, which additionally includes indexes Postgres creates for primary
> keys and UNIQUE constraints.

---

## Licensing

### Code
**GNU Affero General Public License v3.0 (AGPL-3.0)**

### Documentation
**Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**

> The material and content are available as Open Educational Resources (OER) and are licensed
> under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0). To view a
> copy of this license, visit https://creativecommons.org/licenses/by-sa/4.0/

---

## Contact

- **Email:** erdpuls@ubec.network
- **Location:** Müllrose, Brandenburg, Germany (Naturpark Schlaubetal)
- **Founder:** Michel Garand

---

## Acknowledgments

This project is being developed with assistance from Claude (Anthropic PBC). All strategic
decisions, philosophical positions, and project commitments are those of the author.

---

© 2024–2026 Michel Garand · CC BY-SA 4.0 · GNU AGPL v3.0
