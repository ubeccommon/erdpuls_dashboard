# 🌱 Erdpuls Collective Threshold Model

**Erdpuls Müllrose – Center for Sustainability Literacy, Citizen Science and Reciprocal Economics**

A community-held approach to reciprocal economics, built with FastAPI.

> "The community holds each offering into being."

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Docs: CC BY-NC-SA 4.0](https://img.shields.io/badge/Docs-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

**Live Platform:** https://erdpuls.ubec.network  
**API Documentation:** https://erdpuls.ubec.network/api/docs

---

## Table of Contents

- [Overview](#overview)
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

Erdpuls Müllrose is developing a 3,000 square meter Living Laboratory in Naturpark Schlaubetal, Brandenburg, Germany. The project integrates environmental monitoring technology with sustainability education, addressing the "Values-Action Gap" between environmental awareness and sustainable behavior.

The platform implements the **Collective Threshold Model**, a novel community funding mechanism that combines anonymous contributions with transparent needs.

---

## The Collective Threshold Model

The Collective Threshold Model transforms how we fund community offerings:

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
| Database | PostgreSQL 14+ | Schema: `erdpuls_threshold` |
| Frontend | Jinja2 templates + vanilla JS | Server-side rendering |
| Languages | English, German, Polish | Full trilingual support |
| Server | Ubuntu 22.04 | Systemd service management |

---

## Project Structure

```
erdpuls-threshold/
├── app/
│   ├── __init__.py           # Package init
│   ├── main.py               # FastAPI application entry point
│   ├── config.py             # Pydantic settings (including SMTP)
│   ├── database.py           # SQLAlchemy setup with schema search_path
│   ├── models.py             # Database models (User, Offering, Contribution, etc.)
│   ├── schemas.py            # Pydantic schemas for API validation
│   ├── auth.py               # Authentication utilities (sessions, password reset)
│   ├── roles.py              # Role definitions and permissions
│   ├── email.py              # Trilingual email system
│   └── routers/
│       ├── __init__.py       # Router exports
│       ├── api.py            # JSON API endpoints
│       ├── web.py            # HTML page routes
│       ├── auth.py           # Auth routes (login, register, password reset)
│       └── admin.py          # Admin panel routes
├── templates/                # Jinja2 templates with EN/DE/PL support
│   ├── auth/                 # Login, register, password reset
│   ├── admin/                # Admin panel templates
│   └── *.html                # Public pages
├── static/
│   └── css/                  # Stylesheets
├── db/
│   ├── scripts/              # SQL migrations
│   │   ├── 006_role_system.sql
│   │   ├── 006_fix_roles.sql
│   │   └── delivery_language_migration.sql
│   └── erdpuls_schema_documentation_generator.py
├── deploy/
│   ├── deploy.sh             # Deployment script
│   ├── DEPLOY.md             # Deployment guide
│   └── erdpuls-threshold.service  # Systemd service file
├── schema.sql                # Initial database schema
├── requirements.txt          # Python dependencies
├── run.py                    # Development server runner
└── .env                      # Environment configuration (not in repo)
```

---

## Features

### Implemented ✅

- **User Authentication** — Login, registration, secure sessions
- **Password Reset** — Secure tokens with 1-hour expiry
- **Session Timeout** — 30-minute inactivity timeout with warnings
- **Five-Tier Role System** — Member, Creator, Facilitator, Moderator, Admin
- **Offerings Management** — CRUD with multilingual support
- **Delivery Language** — Specify workshop languages (EN/DE/PL)
- **Character Validation** — Defense-in-depth across all layers
- **Registration Flow** — Intention separate from contribution
- **Contribution Flow** — Euro, tokens, hours with confirmation
- **Privacy Model** — Separate contacts table
- **Trilingual UI** — EN/DE/PL language switching
- **Admin Dashboard** — User and offering management
- **Progress Tracking** — Threshold visualization
- **Regeneration Fund** — Balance tracking for surplus/shortfall
- **Legal Pages** — Impressum, Privacy Policy, Terms of Service
- **Database Documentation Generator** — Schema documentation tool

### Planned 📋

- Threshold notification system
- Contribution status workflow automation
- Hours scheduling interface
- UBECrc token blockchain integration

---

## API Endpoints

### Offerings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/offerings` | GET | List all open offerings |
| `/api/offerings/{id}` | GET | Get offering details |
| `/api/offerings/{id}/progress` | GET | Funding progress (aggregates only) |
| `/api/offerings/{id}/register` | POST | Register intention to participate |
| `/api/offerings/{id}/contribute/euro` | POST | Euro contribution |
| `/api/offerings/{id}/contribute/token` | POST | Token contribution |
| `/api/offerings/{id}/contribute/hours` | POST | Hours contribution |

### Fund & Rates

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fund/balance` | GET | Regeneration Fund balance |
| `/api/rates/tokens` | GET | Current token exchange rate |
| `/api/rates/hours` | GET | Hours contribution rates |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/docs` | GET | Interactive API documentation (Swagger) |
| `/api/redoc` | GET | ReDoc API documentation |
| `/api/session/refresh` | POST | Refresh session cookie |
| `/health` | GET | Health check endpoint |

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
UBECrc tokens earned through environmental stewardship (~70 tokens = €1).

### Hours
Pre-arranged work valued by category:

| Category | EUR/Hour | Description |
|----------|----------|-------------|
| `garden_labor` | €10 | Weeding, planting, harvesting, composting |
| `administrative` | €12 | Communication, scheduling, outreach |
| `skilled_labor` | €20 | Carpentry, electrical, sensor installation |
| `translation` | €20 | DE/EN/PL translation, documentation |
| `knowledge_sharing` | €25 | Leading sessions, mentoring, traditional knowledge |
| `technical_support` | €30 | Data processing, sensor calibration, web development |

---

## Quick Start (Development)

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd erdpuls-threshold

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your database credentials

# Run the schema (first time only)
psql -d ubec_erdpuls -f schema.sql

# Run development server
python run.py
```

Visit http://localhost:8004

API docs at http://localhost:8004/api/docs

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ubec_erdpuls

# Security
SECRET_KEY=<generated-secret-key>
DEBUG=false

# Application
BASE_URL=https://erdpuls.ubec.network

# SMTP Configuration
SMTP_HOST=mail.ubec.network
SMTP_PORT=465
SMTP_USER=erdpuls@ubec.network
SMTP_PASSWORD=<password>
SMTP_USE_TLS=false
SMTP_FROM_EMAIL=noreply@ubec.network
SMTP_FROM_NAME=Erdpuls Müllrose
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deployment

### Systemd Service

```bash
# Copy service file
sudo cp deploy/erdpuls-threshold.service /etc/systemd/system/erdpuls_ubec.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable erdpuls_ubec
sudo systemctl start erdpuls_ubec

# Check status
sudo systemctl status erdpuls_ubec
```

### Useful Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl status erdpuls_ubec` | Check app status |
| `sudo systemctl restart erdpuls_ubec` | Restart app |
| `sudo journalctl -u erdpuls_ubec -f` | View live logs |
| `sudo journalctl -u erdpuls_ubec -n 100` | View last 100 log lines |

### Architecture

```
Internet → Caddy (80/443)
              │
              └── erdpuls.ubec.network → localhost:8004
```

See `deploy/DEPLOY.md` for detailed production deployment instructions.

---

## Database Documentation

Generate schema documentation:

```bash
cd db/
python erdpuls_schema_documentation_generator.py \
  --host localhost \
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
| Relationships | 6 |
| Indexes | 22 |

---

## Licensing

### Code
**GNU Affero General Public License v3.0 (AGPL-3.0)**

### Documentation
**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**

> The material and content are available as Open Educational Resources (OER) and are licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0). To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de

---

## Contact

- **Email:** erdpuls@ubec.network
- **Location:** Müllrose, Brandenburg, Germany (Naturpark Schlaubetal)
- **Founder:** Michel Garand

---

## Acknowledgments

This project uses the services of Claude and Anthropic PBC.

---

© Michel Garand | Lizenz: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
