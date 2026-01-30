# Erdpuls Müllrose Project: Comprehensive Status Report and README

**Report Date:** 30 January 2026  
**Project:** Erdpuls Müllrose – Center for Sustainability Literacy, Citizen Science and Reciprocal Economics  
**Location:** Müllrose, Brandenburg, Germany (Naturpark Schlaubetal)  
**Founder:** Michel Garand  
**Platform:** https://erdpuls.ubec.network

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Vision and Philosophy](#2-project-vision-and-philosophy)
3. [Strategic Documentation](#3-strategic-documentation)
4. [Technical Platform](#4-technical-platform)
5. [Database Architecture](#5-database-architecture)
6. [Role-Based Permission System](#6-role-based-permission-system)
7. [Collective Threshold Model](#7-collective-threshold-model)
8. [Current Implementation Status](#8-current-implementation-status)
9. [Outstanding Items](#9-outstanding-items)
10. [Strategic Development Timeline](#10-strategic-development-timeline)
11. [Licensing](#11-licensing)
12. [Getting Started (README)](#12-getting-started-readme)

---

## 1. Executive Summary

Erdpuls Müllrose is developing a 3,000 square meter Living Laboratory that integrates environmental monitoring technology with sustainability education. This report documents the project state as of 30 January 2026, based on examination of:

- GitHub erdpuls_dashboard repository (authoritative code source)
- Project knowledge documents
- Database schema documentation (erdpuls_schema_documentation_20260129_054507.md)
- Conversation history through January 2026

**Key Achievements:**
- Functional web platform deployed at erdpuls.ubec.network
- Novel Collective Threshold Model funding mechanism
- Trilingual support (English, German, Polish)
- Five-tier role-based permission system
- Privacy-protected contribution system
- Comprehensive authentication with password reset

**Upcoming Milestone:** Application to Incubator Village Beeskow, Kohorte 2 (July 2026)

---

## 2. Project Vision and Philosophy

### 2.1 Core Mission

The project addresses the "Values-Action Gap"—the documented disconnect between environmental awareness (84% of European youth value sustainability) and sustainable behavior (only 30% translate this into action).

**Guiding Question:** *"What if technology and nature are not opposites but complementary expressions of the same creative forces that shape our world?"*

### 2.2 Philosophical Foundations

The project rejects the "Illusion of Choice" between binary oppositions:

| False Binary | Erdpuls Response |
|--------------|------------------|
| Technology OR Nature | Technology and nature in **symbiosis**—distinct identities creating reciprocal support |
| Facts OR Wisdom | Integrated epistemological approaches |
| Progress OR Preservation | Regenerative development |

**Key Terminology:** The term "symbiosis" (not "synthesis") was deliberately chosen to emphasize that technology and nature maintain distinct identities while reciprocally supporting each other.

### 2.3 Plant Wisdom Framework

The pedagogical approach draws from seven characteristics of plant intelligence:

1. **Rootedness** — Commitment to place; transforming difficulty rather than fleeing
2. **Generosity** — Giving more than taking (economy of abundance)
3. **Transformation** — Participating in energy transformation, not extraction
4. **Distributed Intelligence** — Wisdom without centralization
5. **Network Thinking** — Resource sharing through interconnection
6. **Rhythmic Living** — Alignment with natural cycles
7. **Patient Accumulation** — Steady growth over time

### 2.4 Intellectual Influences

- **Ubuntu Philosophy** ("I am because we are") — Community interdependence
- **Anthroposophical Pedagogy** — Contemplative practice and phenomenological observation
- **Permaculture Design** — Practical patterns from living systems
- **Goethean Science** — Qualitative observation methodology
- **EU GreenComp Standards** — European sustainability competence framework

---

## 3. Strategic Documentation

### 3.1 Multilingual Strategic Narratives (Verified in Project Files)

| Document | Language | File |
|----------|----------|------|
| Strategic Narrative | English | `Erdpuls_Strategic_Narrative.odt` |
| Strategische Erzählung | German | `Erdpuls_Strategische_Erzaehlung_DE.docx` |
| Narracja Strategiczna | Polish | `Erdpuls_Narracja_Strategiczna_PL.docx` |

**Branding Decision:** The English subtitle "Center for Sustainability Literacy, Citizen Science and Reciprocal Economics" is maintained across all language versions for unified international branding.

### 3.2 Supporting Documents (Verified in Project Files)

| Document | Purpose | Size |
|----------|---------|------|
| `ERDPULS_MULLROSE_COMPREHENSIVE_VISION_INTEGRATED.odt` | Full project vision | 51KB |
| `Erdpuls_Reciprocal_Economics_Business_Model.docx` | Economic framework | 16KB |
| `Erdpuls_Collective_Threshold_Model.docx` | Funding mechanism | 13KB |
| `Erdpuls_Collective_Threshold_Business_Model_Canvas.docx` | Canvas visualization | 17KB |

---

## 4. Technical Platform

### 4.1 Architecture Overview

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | FastAPI + SQLAlchemy | Python web framework |
| Database | PostgreSQL 14.20 | Schema: `erdpuls_threshold` |
| Frontend | Jinja2 templates + vanilla JS | Server-side rendering |
| Languages | English, German, Polish | Full trilingual support |
| Server | Ubuntu 22.04 | Systemd service management |
| Domain | erdpuls.ubec.network | HTTPS enabled |

### 4.2 Repository Structure (from GitHub erdpuls_dashboard)

```
erdpuls-threshold/
├── app/
│   ├── __init__.py        # Package init
│   ├── main.py            # FastAPI application entry point
│   ├── config.py          # Pydantic settings (including SMTP)
│   ├── database.py        # SQLAlchemy setup with schema search_path
│   ├── models.py          # Database models (User, Offering, Contribution, etc.)
│   ├── schemas.py         # Pydantic schemas for API validation
│   ├── auth.py            # Authentication utilities (sessions, password reset)
│   ├── roles.py           # Role definitions and permissions
│   ├── email.py           # Trilingual email system
│   └── routers/
│       ├── __init__.py    # Router exports
│       ├── api.py         # JSON API endpoints
│       ├── web.py         # HTML page routes
│       ├── auth.py        # Auth routes (login, register, password reset)
│       └── admin.py       # Admin panel routes
├── templates/             # Jinja2 templates with EN/DE/PL support
├── static/css/            # Stylesheets
├── db/
│   └── scripts/           # SQL migrations
│       ├── 006_role_system.sql
│       ├── 006_fix_roles.sql
│       └── delivery_language_migration.sql
├── deploy/
│   ├── deploy.sh          # Deployment script
│   └── erdpuls-threshold.service  # Systemd service file
├── schema.sql             # Initial database schema
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
├── run.py                 # Development server runner
└── .env                   # Environment configuration (not in repo)
```

### 4.3 API Endpoints (from README.md)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/offerings` | GET | List all open offerings |
| `/api/offerings/{id}` | GET | Get offering details |
| `/api/offerings/{id}/progress` | GET | Funding progress (aggregates only) |
| `/api/offerings/{id}/register` | POST | Register intention to participate |
| `/api/offerings/{id}/contribute/euro` | POST | Euro contribution |
| `/api/offerings/{id}/contribute/token` | POST | Token contribution |
| `/api/offerings/{id}/contribute/hours` | POST | Hours contribution |
| `/api/fund/balance` | GET | Regeneration Fund balance |
| `/api/rates/tokens` | GET | Current token exchange rate |
| `/api/rates/hours` | GET | Hours contribution rates |
| `/api/docs` | GET | Interactive API documentation (Swagger) |
| `/health` | GET | Health check endpoint |
| `/api/session/refresh` | POST | Refresh session cookie |

### 4.4 Platform URLs

- **Production:** https://erdpuls.ubec.network
- **API Documentation:** https://erdpuls.ubec.network/api/docs
- **Development Path:** `/home/kelpit/UBEC_ERDPULS/`

---

## 5. Database Architecture

### 5.1 Schema Metadata (from erdpuls_schema_documentation_20260129_054507.md)

| Property | Value |
|----------|-------|
| Generated | 2026-01-29T05:45:07 |
| Schema Name | `erdpuls_threshold` |
| Database Size | 9,329 kB |
| PostgreSQL Version | 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1) |
| UUID Extension | ✅ Enabled |

### 5.2 Schema Summary

| Metric | Count |
|--------|-------|
| Tables | 9 |
| Columns | 93 |
| Relationships | 6 |
| Indexes | 22 |
| Triggers | 1 |
| Functions | 12 |
| Erdpuls Core Tables | 8 |
| Privacy-Sensitive Tables | 2 |

### 5.3 Core Tables

| Table | Purpose | Current Rows |
|-------|---------|--------------|
| `users` | User accounts with authentication credentials | 2 |
| `roles` | Role definitions for permission hierarchy | 5 |
| `offerings` | Workshops, courses, events with threshold-based funding | 1 |
| `registrations` | Participation intentions (separate from contributions) | Variable |
| `contributions` | Contributions—NO contributor identification stored | 0 |
| `contribution_contacts` | Separated contact info for operational purposes | 0 |
| `regeneration_fund` | Community reserve from surplus contributions | 0 |
| `token_rates` | Exchange rates for UBECrc tokens to EUR | 2 |
| `hours_rates` | Valuation rates for different contribution hours | 6 |

### 5.4 Privacy Model

> **Community-Anonymous, Operationally-Known**

- **Public visibility:** Aggregates only (total amount, contributor count)
- **Organizer visibility:** Individual contributions + linked contact info
- **No individual amounts displayed publicly**

### 5.5 Contribution Types

| Type | Description |
|------|-------------|
| `euro` | Direct monetary contribution in EUR |
| `token` | UBECrc tokens earned through environmental stewardship (~70 tokens = €1) |
| `hours` | Pre-arranged work valued by category |

### 5.6 Hours Rate Categories

| Category | EUR/Hour | Description |
|----------|----------|-------------|
| `garden_labor` | €10 | Weeding, planting, harvesting, composting |
| `administrative` | €12 | Communication, scheduling, outreach |
| `skilled_labor` | €20 | Carpentry, electrical, sensor installation |
| `translation` | €20 | DE/EN/PL translation, documentation |
| `knowledge_sharing` | €25 | Leading sessions, mentoring, traditional knowledge |
| `technical_support` | €30 | Data processing, sensor calibration, web development |

### 5.7 Database Relationships Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│     users       │     │    offerings     │     │   registrations     │
├─────────────────┤     ├──────────────────┤     ├─────────────────────┤
│ id (UUID)       │──┐  │ id (UUID)        │◄────│ offering_id (FK)    │
│ email           │  │  │ title (EN/DE/PL) │     │ email               │
│ password_hash   │  │  │ description      │     │ name                │
│ name            │  │  │ threshold_amount │     │ status              │
│ role            │  └──│ creator_id (FK)  │     │ linked_contribution │
│ is_active       │     │ event_date       │     │ registered_at       │
│ created_at      │     │ status           │     └─────────────────────┘
│ last_login      │     │ delivery_language│
└─────────────────┘     └────────┬─────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  contributions  │     │regeneration_fund │     │    token_rates      │
├─────────────────┤     ├──────────────────┤     ├─────────────────────┤
│ id (UUID)       │     │ id (UUID)        │     │ id (UUID)           │
│ offering_id(FK) │     │ amount           │     │ tokens_per_eur      │
│ amount_eur      │     │ transaction_type │     │ effective_from      │
│ contribution_   │     │ offering_id (FK) │     │ effective_until     │
│   type          │     │ description      │     └─────────────────────┘
│ token_amount    │     │ created_at       │
│ hours_amount    │     └──────────────────┘     ┌─────────────────────┐
│ hours_category  │                              │    hours_rates      │
│ engagement_type │                              ├─────────────────────┤
│ status          │                              │ id (UUID)           │
│ contributed_at  │                              │ category            │
└────────┬────────┘                              │ eur_per_hour        │
         │                                       │ description         │
         │ (1:1 operational link)                └─────────────────────┘
         ▼
┌────────────────────┐
│contribution_contacts│
├────────────────────┤
│ id (UUID)          │
│ contribution_id(FK)│
│ name               │
│ email              │
│ phone              │
│ notes              │
└────────────────────┘
```

---

## 6. Role-Based Permission System

### 6.1 Five-Tier Role Hierarchy

| Role | Level | Description | Capabilities |
|------|-------|-------------|--------------|
| `member` | 10 | Default for new registrations | Participate, contribute |
| `creator` | 20 | Content creators | Create offerings (requires approval) |
| `facilitator` | 30 | Trusted creators | Direct publishing without approval |
| `moderator` | 50 | Community managers | Approve offerings, access admin panel |
| `admin` | 100 | Full access | Complete system access |

### 6.2 Permission Matrix

| Permission | member | creator | facilitator | moderator | admin |
|------------|--------|---------|-------------|-----------|-------|
| View Offerings | ✅ | ✅ | ✅ | ✅ | ✅ |
| Participate | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contribute | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create Offering | ❌ | ✅ | ✅ | ✅ | ✅ |
| Publish Direct | ❌ | ❌ | ✅ | ✅ | ✅ |
| Approve Offerings | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage Users | ❌ | ❌ | ❌ | ❌ | ✅ |

### 6.3 Trilingual Role Names

| Role | English | German | Polish |
|------|---------|--------|--------|
| member | Member | Mitglied | Członek |
| creator | Creator | Ersteller | Twórca |
| facilitator | Facilitator | Moderator | Facilitator |
| moderator | Moderator | Moderator | Moderator |
| admin | Administrator | Administrator | Administrator |

---

## 7. Collective Threshold Model

### 7.1 Core Mechanism

The Collective Threshold Model transforms community funding through five steps:

1. **Transparent Need** — Each offering publishes exactly what resources it needs
2. **Register Intention** — People express desire to participate (separate from payment)
3. **Anonymous Contribution** — Everyone contributes to a collective pot
4. **Threshold Met** — When the threshold is reached, the offering happens
5. **No One Knows** — No one knows who contributed what, dissolving stigma

### 7.2 Engagement Pathways

| Pathway | Description | Registration | Contribution |
|---------|-------------|--------------|--------------|
| Participate Only | Express intention without financial commitment | ✅ | ❌ |
| Support Only | Contribute without participating | ❌ | ✅ |
| Support & Participate | Both contribute and participate | ✅ | ✅ |

### 7.3 Regeneration Fund

- **Purpose:** Community reserve from surplus contributions
- **Surplus:** When offerings exceed threshold, excess goes to fund
- **Shortfall:** When offerings don't reach threshold, fund can cover gap

---

## 8. Current Implementation Status

### 8.1 Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| Core platform deployment | ✅ Complete | Running at erdpuls.ubec.network |
| User authentication | ✅ Complete | Login, registration, sessions |
| Password reset functionality | ✅ Complete | Secure tokens using itsdangerous |
| Session timeout | ✅ Complete | 30-minute inactivity timeout with warnings |
| Offerings management | ✅ Complete | CRUD with multilingual support |
| Delivery language field | ✅ Complete | Offerings specify EN/DE/PL |
| Character limit validation | ✅ Complete | Defense-in-depth across all layers |
| Role-based permissions | ✅ Complete | Five-tier hierarchy implemented |
| Registration flow | ✅ Complete | Intention separate from contribution |
| Contribution flow | ✅ Complete | Euro, tokens, hours with confirmation |
| Privacy model | ✅ Complete | Separate contacts table implemented |
| Trilingual UI | ✅ Complete | EN/DE/PL language switching |
| Admin dashboard | ✅ Complete | User/offering management |
| Progress tracking | ✅ Complete | Threshold visualization |
| Regeneration Fund | ✅ Complete | Balance tracking |
| Legal pages | ✅ Complete | Impressum, Privacy Policy, Terms of Service |
| Database documentation generator | ✅ Complete | Adapted from UBEC IOT project |
| Systemd service | ✅ Complete | Fixed bcrypt/passlib compatibility |
| Incubator pitch deck | ✅ Complete | For Beeskow Kohorte 2 application |

### 8.2 Authentication System Details

- **Session tokens** using itsdangerous with configurable expiry
- **Password reset tokens** with 1-hour expiry
- **Email enumeration protection** (always shows success on forgot-password)
- **Clean URL paths** (`/r/{token}` instead of `/reset-password?token=`) to avoid spam filter triggers
- **Session refresh** on user activity to extend inactivity timeout
- **Direct bcrypt usage** (fixed passlib compatibility issue with bcrypt 5.0.0)

### 8.3 Email System Status

The email system is fully implemented with:
- Trilingual email templates (EN/DE/PL)
- HTML + plain text versions
- Contribution confirmation emails
- Password reset emails

**Current Issue:** MailChannels (spam filtering service used by hosting provider) has intermittently blocked outbound emails. DNS records (SPF, DKIM, DMARC, PTR) are documented as valid.

**Workarounds Applied:**
- Simplified email templates
- Plain text versions preferred
- Clean `/r/` URL paths instead of query parameters
- Spam filter training in MailChannels console

---

## 9. Outstanding Items

### 9.1 Immediate Technical Tasks

1. **Monitor Email Delivery**
   - Continue monitoring MailChannels status
   - Alternative: Configure external SMTP service (e.g., Brevo/Sendinblue) if issues persist

2. **Seed Test Data**
   - Create initial offerings for platform testing
   - Document user workflows

### 9.2 Platform Enhancements (Not Yet Implemented)

1. Threshold notification system (when offerings reach goal)
2. Contribution status workflow automation (pending → confirmed → completed)
3. Hours scheduling interface for organizers
4. Token integration with blockchain infrastructure (UBECrc)

### 9.3 Content Development

1. Develop curriculum materials (EU GreenComp aligned)
2. Create user onboarding documentation
3. Expand multilingual content

---

## 10. Strategic Development Timeline

The project documents a seven-year development cycle:

| Phase | Years | Focus |
|-------|-------|-------|
| **Germination** | 1-2 (Current) | System proof, community gathering |
| **Growth** | 3-4 | Ten schools join, bioregion awakens |
| **Flowering** | 5-6 | Research publication, policy influence |
| **Fruiting** | 7 | Model replication, paradigm establishment |

**Next Milestone:** Incubator Village Beeskow, Kohorte 2 (July 2026)

---

## 11. Licensing

### 11.1 Code

**GNU Affero General Public License v3.0 (AGPL-3.0)**

### 11.2 Documentation

**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**

> The material and content are available as Open Educational Resources (OER) and are licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0). To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de

---

## 12. Getting Started (README)

### 12.1 Overview

The Collective Threshold Model is a community-held approach to reciprocal economics built with FastAPI.

> "The community holds each offering into being."

### 12.2 Prerequisites

- Python 3.10+
- PostgreSQL 14+
- pip

### 12.3 Quick Start (Development)

```bash
# Clone the repository
git clone <repository-url>
cd erdpuls-threshold

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run the schema (first time only)
psql -d ubec_erdpuls -f schema.sql

# Run development server
python run.py
```

Visit http://localhost:8004

API docs at http://localhost:8004/api/docs

### 12.4 Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/ubec_erdpuls
SECRET_KEY=<generated-secret>
DEBUG=false
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

### 12.5 Deployment with Systemd

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

### 12.6 Database Documentation

Generate database schema documentation:

```bash
cd db/
python erdpuls_schema_documentation_generator.py \
  --host localhost \
  --database ubec_erdpuls \
  --user <username> \
  --password <password> \
  --format markdown
```

### 12.7 Project Resources

| Resource | URL |
|----------|-----|
| Live Platform | https://erdpuls.ubec.network |
| API Documentation | https://erdpuls.ubec.network/api/docs |
| GitHub Repository | erdpuls_dashboard (authoritative code source) |
| Liberapay | Donation support |

### 12.8 Contact

- **Email:** erdpuls@ubec.network
- **Location:** Müllrose, Brandenburg, Germany

---

## Appendix: Recent Development History

| Date | Topic |
|------|-------|
| 29 Jan 2026 | Pitch deck for Incubator Village Beeskow |
| 29 Jan 2026 | Delivery language feature, character limit validation |
| 28 Jan 2026 | Comprehensive status report, systemd service fixes |
| 28 Jan 2026 | Password reset email deliverability |
| 27 Jan 2026 | Role system implementation, offerings page |
| 26 Jan 2026 | Database documentation generator adaptation |
| 26 Jan 2026 | Email SMTP debugging, MailChannels issue identified |
| 25 Jan 2026 | Strategic narrative translation refinements |

---

*This report was generated based on project knowledge, GitHub repository code, strategic documents, database schema documentation (erdpuls_schema_documentation_20260129_054507.md), and conversation history. The GitHub erdpuls_dashboard repository serves as the authoritative source for current code state.*

---

© Michel Garand | Lizenz: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de

*This project uses the services of Claude and Anthropic PBC.*
