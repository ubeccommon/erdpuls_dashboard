# Erdpuls Müllrose Project: Comprehensive Status Report

**Report Date:** 27 January 2026  
**Prepared by:** Claude (AI Assistant), in collaboration with Michel Garand  
**Project:** Erdpuls Müllrose – Center for Sustainability Literacy, Citizen Science and Reciprocal Economics  
**Location:** Müllrose, Brandenburg, Germany (Schlaube Valley Nature Park)

---

## Executive Summary

Erdpuls Müllrose is developing a 3,000 square meter Living Laboratory that integrates environmental monitoring technology with sustainability education. This report provides a comprehensive review of all documented work to date, based on examination of the GitHub erdpuls_dashboard repository (authoritative code source), project knowledge documents, database schema documentation, and conversation history.

The project has achieved significant milestones in establishing a novel community funding platform (the Collective Threshold Model), developing a coherent philosophical framework, and building functional technical infrastructure. The core platform is operational at `https://erdpuls.ubec.network` with a FastAPI backend, PostgreSQL database, and trilingual support.

---

## 1. Project Vision and Philosophy

### 1.1 Core Mission

The project addresses what it terms the "Values-Action Gap"—the documented disconnect between environmental awareness (84% of European youth value sustainability) and sustainable behavior (only 30% translate this into action).

**Guiding Question:** *"What if technology and nature are not opposites but complementary expressions of the same creative forces that shape our world?"*

### 1.2 Philosophical Foundations

The project explicitly rejects what it calls the "Illusion of Choice" between binary oppositions:

| False Binary | Erdpuls Response |
|--------------|------------------|
| Technology OR Nature | Technology and nature in **symbiosis**—distinct identities creating reciprocal support |
| Facts OR Wisdom | Integrated epistemological approaches |
| Progress OR Preservation | Regenerative development |

**Key Terminology Decision:** The term "symbiosis" (not "synthesis") was deliberately chosen to emphasize that technology and nature maintain distinct identities while reciprocally supporting each other.

### 1.3 Plant Wisdom Framework

The pedagogical approach draws from seven characteristics of plant intelligence:

1. **Rootedness** — Commitment to place; transforming difficulty rather than fleeing
2. **Generosity** — Giving more than taking (economy of abundance)
3. **Transformation** — Participating in energy transformation, not extraction
4. **Distributed Intelligence** — Wisdom without centralization
5. **Network Thinking** — Resource sharing through interconnection
6. **Rhythmic Living** — Alignment with natural cycles
7. **Patient Accumulation** — Steady growth over time

### 1.4 Intellectual Influences

The project documents the following philosophical influences:

- **Ubuntu Philosophy** ("I am because we are") — Community interdependence
- **Anthroposophical Pedagogy** — Contemplative practice and phenomenological observation
- **Permaculture Design** — Practical patterns from living systems
- **Goethean Science** — Qualitative observation methodology
- **EU GreenComp Standards** — European sustainability competence framework

---

## 2. Strategic Narrative Documents

### 2.1 Multilingual Documentation (Verified in Project Files)

| Document | Language | File |
|----------|----------|------|
| Strategic Narrative | English | `Erdpuls_Strategic_Narrative.odt` |
| Strategische Erzählung | German | `Erdpuls_Strategische_Erzaehlung_DE.docx` |
| Narracja Strategiczna | Polish | `Erdpuls_Narracja_Strategiczna_PL.docx` |

**Branding Decision:** The English subtitle "Center for Sustainability Literacy, Citizen Science and Reciprocal Economics" is maintained across all language versions for unified international branding.

### 2.2 Supporting Documents (Verified in Project Files)

| Document | Purpose | Size |
|----------|---------|------|
| `ERDPULS_MULLROSE_COMPREHENSIVE_VISION_INTEGRATED.odt` | Full project vision | 51KB |
| `Erdpuls_Reciprocal_Economics_Business_Model.docx` | Economic framework | 16KB |
| `Erdpuls_Collective_Threshold_Model.docx` | Funding mechanism | 13KB |
| `Erdpuls_Collective_Threshold_Business_Model_Canvas.docx` | Canvas visualization | 17KB |

---

## 3. Technical Platform

### 3.1 Architecture Overview

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | FastAPI + SQLAlchemy | Python web framework |
| Database | PostgreSQL 14.20 | Schema: `erdpuls_threshold` |
| Frontend | Jinja2 templates + vanilla JS | Server-side rendering |
| Languages | English, German, Polish | Full trilingual support |
| Deployment | Ubuntu 22.04 server | Production at erdpuls.ubec.network |

### 3.2 Verified Code Structure (from GitHub Repository)

```
erdpuls-threshold/
├── app/
│   ├── __init__.py        # Package init
│   ├── main.py            # FastAPI application entry point
│   ├── config.py          # Pydantic settings (including SMTP)
│   ├── database.py        # SQLAlchemy setup with schema search_path
│   ├── models.py          # Database models (User, Offering, Contribution, etc.)
│   ├── schemas.py         # Pydantic schemas for API validation
│   ├── auth.py            # Authentication utilities
│   ├── email.py           # Trilingual email confirmation system
│   └── routers/
│       ├── __init__.py    # Router exports
│       ├── api.py         # JSON API endpoints
│       ├── web.py         # HTML page routes
│       └── auth.py        # Auth routes (login, register, dashboard)
├── templates/             # Jinja2 templates with EN/DE/PL support
├── static/css/            # Stylesheets
├── db/
│   └── scripts/           # SQL migrations
├── deploy/
│   ├── deploy.sh          # Deployment script
│   └── erdpuls-threshold.service  # Systemd service file
├── schema.sql             # Initial database schema
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
├── run.py                 # Development server runner
└── .env                   # Environment configuration (not in repo)
```

### 3.3 API Endpoints (Documented in README.md)

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

### 3.4 Environment Configuration (from .env template)

```env
DATABASE_URL=postgresql://ubecpuls:<password>@localhost:5432/ubec_erdpuls
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

---

## 4. Database Schema

### 4.1 Schema Metadata (from erdpuls_schema_documentation_20260127_070340.md)

| Property | Value |
|----------|-------|
| Generated | 2026-01-27T07:03:40 |
| Schema Name | `erdpuls_threshold` |
| Database Size | 9,185 kB |
| PostgreSQL Version | 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1) |
| UUID Extension | ✅ Enabled |

### 4.2 Schema Summary

| Metric | Count |
|--------|-------|
| Tables | 8 |
| Columns | 76 |
| Relationships | 5 |
| Indexes | 19 |
| Triggers | 1 |
| Functions | 12 |
| Core Erdpuls Tables | 8 |
| Privacy-Sensitive Tables | 2 |

### 4.3 Core Tables

| Table | Purpose | Current Rows |
|-------|---------|--------------|
| `users` | User accounts with authentication credentials | 1 |
| `offerings` | Workshops, courses, events with threshold-based funding | 1 |
| `registrations` | Participation intentions (separate from contributions) | 0 |
| `contributions` | Contributions—NO contributor identification stored | 0 |
| `contribution_contacts` | Separated contact info for operational purposes | 0 |
| `regeneration_fund` | Community reserve from surplus contributions | 0 |
| `token_rates` | Exchange rates for UBECrc tokens to EUR | 2 |
| `hours_rates` | Valuation rates for different contribution hours | 6 |

### 4.4 Database Relationships

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│     users       │     │    offerings     │     │   registrations     │
├─────────────────┤     ├──────────────────┤     ├─────────────────────┤
│ id (UUID)       │──┐  │ id (UUID)        │◄────│ offering_id (FK)    │
│ email           │  │  │ title (EN/DE/PL) │     │ email               │
│ password_hash   │  │  │ description      │     │ name                │
│ name            │  │  │ threshold_amount │     │ status              │
│ role            │  └──│ creator_id (FK)  │     │ registered_at       │
│ is_active       │     │ event_date       │     └─────────────────────┘
│ created_at      │     │ status           │
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
│ status          │                              ├─────────────────────┤
│ contributed_at  │                              │ id (UUID)           │
└────────┬────────┘                              │ category            │
         │                                       │ eur_per_hour        │
         │ (1:1 operational link)                │ description         │
         ▼                                       └─────────────────────┘
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

### 4.5 Migration Status

| Migration | Status |
|-----------|--------|
| Initial schema (`schema.sql`) | ✅ Applied |
| Users table | ✅ Applied |
| `003_contribution_contacts.sql` | ✅ Applied |

---

## 5. Collective Threshold Model

### 5.1 Core Mechanism

The Collective Threshold Model transforms community funding through five steps:

1. **Transparent Need** — Each offering publishes exactly what resources it needs
2. **Register Intention** — People express desire to participate (separate from payment)
3. **Anonymous Contribution** — Everyone contributes to a collective pot
4. **Threshold Met** — When the threshold is reached, the offering happens
5. **No One Knows** — Individual contribution amounts remain private

### 5.2 Privacy Model: "Community-Anonymous, Operationally-Known"

A key development documented in conversation history was transitioning from "fully anonymous" to a nuanced privacy model:

**Public Visibility:**
- Only aggregate totals displayed
- Contributor count shown
- Individual amounts never revealed

**Organizer Visibility (Operational Only):**
- Contributor contact information (optional, for coordination)
- Individual contributions linked to contacts for:
  - Hours contribution scheduling
  - Payment confirmation
  - Tax receipts if needed
  - Follow-up communications

**Technical Implementation:**
- `contributions` table contains NO identifying information
- `contribution_contacts` table stores identity SEPARATELY
- Two tables linked only for organizer operational views
- Clear messaging: "Privacy protected" (not "anonymous")

### 5.3 Contribution Types

| Type | Description | Exchange Rate |
|------|-------------|---------------|
| **Euro** | Direct monetary contribution | 1:1 |
| **UBECrc Tokens** | Environmental stewardship tokens | 70 tokens = €1.00 (default) |
| **Hours** | Skill/labor contribution | €10-40/hour (by category) |

### 5.4 Hours Categories (from database)

| Category | EUR/Hour | Description |
|----------|----------|-------------|
| `garden_labor` | €10 | Weeding, planting, harvesting, composting |
| `skilled_labor` | €20 | Carpentry, electrical, sensor installation |
| `knowledge_sharing` | €25 | Leading sessions, mentoring, traditional knowledge |
| `translation` | €20 | DE/EN/PL translation, documentation |
| `technical_support` | €30 | Data processing, sensor calibration, web development |
| `administrative` | €12 | Communication, scheduling, outreach |

### 5.5 Regeneration Fund

Surplus contributions flow into a community Regeneration Fund that can:
- Cover shortfalls for offerings that almost reach threshold
- Seed new offerings
- Support community resilience

Transaction types: `surplus_in`, `shortfall_cover`, `seed_offering`, `adjustment`

---

## 6. Reciprocal Economics Business Model

### 6.1 Four Pathways of Participation

| Pathway | How It Works | Philosophical Basis |
|---------|--------------|---------------------|
| **Full Rate** | Pay listed price (supports operations + others) | Plant generosity: giving more than taking |
| **Supported Rate** | Pay 50-80% (self-selected, no justification needed) | Ubuntu: individual wellbeing depends on community |
| **Contribution** | Offset costs through labor, skills, or service | Reciprocity: value flows in multiple directions |
| **Token Exchange** | Use earned UBECrc tokens | Environmental stewardship recognized as value |

### 6.2 Target Financial Sustainability

- **40%** Full rate participants
- **40%** Supported rate participants
- **20%** Contribution/token participants
- Full rates set to cover operational costs + 25% community subsidy pool

### 6.3 Communication Language Guidelines

The project deliberately avoids charity framing:

| Avoid | Use Instead |
|-------|-------------|
| "Scholarship" or "Financial aid" | "Supported rate" |
| "Discounted" or "Reduced" | "Different pathways to participation" |
| "Charity" or "Donation" | "Reciprocal exchange" |
| "Those who can afford it" | "Those choosing to support others" |
| "Pay what you can" | "Choose the pathway that fits your situation" |

---

## 7. Current Implementation Status

### 7.1 Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| Core platform deployment | ✅ Complete | Running at erdpuls.ubec.network |
| User authentication | ✅ Complete | Login, registration, sessions |
| Offerings management | ✅ Complete | CRUD with multilingual support |
| Registration flow | ✅ Complete | Intention separate from contribution |
| Contribution flow | ✅ Complete | Euro, tokens, hours with confirmation |
| Privacy model | ✅ Complete | Separate contacts table implemented |
| Trilingual UI | ✅ Complete | EN/DE/PL language switching |
| Organizer dashboard | ✅ Complete | Manage offerings, view contributions |
| Progress tracking | ✅ Complete | Threshold visualization |
| Regeneration Fund | ✅ Complete | Balance tracking, surplus processing |
| Database documentation generator | ✅ Complete | Adapted from UBEC IOT project |
| Email confirmation | ⚠️ Partial | Code complete, SMTP blocked |

### 7.2 Email System Status

The email confirmation system is documented as fully implemented with:
- Trilingual email templates (EN/DE/PL)
- HTML + plain text versions
- Contribution summary display
- Privacy reminders
- Next steps guidance
- SMTP configuration for port 465 with SSL

**Current Issue:** MailChannels (spam filtering service) has blocked the `erdpuls@ubec.network` account at the hosting provider level. DNS records (SPF, DKIM, DMARC, PTR) are documented as valid.

**Documented Reference:** `auid=instrampxe0y3a`

### 7.3 Platform URLs

- **Production:** https://erdpuls.ubec.network
- **API Documentation:** https://erdpuls.ubec.network/api/docs
- **Development Path:** `/home/kelpit/UBEC_ERDPULS/`
- **Production Path:** `/var/www/erdpuls-threshold/`

---

## 8. Outstanding Items and Recommendations

### 8.1 Immediate Technical Tasks

1. **Resolve Email Delivery**
   - Contact hostingww.com to resolve MailChannels block
   - Alternative: Configure external SMTP service (e.g., Brevo/Sendinblue)

2. **Seed Test Data**
   - Create initial offerings for platform testing
   - Document user workflows

### 8.2 Platform Enhancements (Not Yet Implemented)

1. Threshold notification system (when offerings reach goal)
2. Contribution status workflow automation (pending → confirmed → completed)
3. Hours scheduling interface for organizers
4. Token integration with blockchain infrastructure (UBECrc)

### 8.3 Content Development

1. Develop curriculum materials (EU GreenComp aligned)
2. Create user onboarding documentation
3. Expand multilingual content

---

## 9. Strategic Development Timeline

The project documents a seven-year development cycle:

| Phase | Years | Focus |
|-------|-------|-------|
| **Germination** | 1-2 (Current) | System proof, community gathering |
| **Growth** | 3-4 | Ten schools join, bioregion awakens |
| **Flowering** | 5-6 | Research publication, policy influence |
| **Fruiting** | 7 | Model replication, paradigm establishment |

---

## 10. Achievements Summary

Based on documented evidence, the project has established:

- ✅ A novel community funding model combining threshold-based funding with privacy protection
- ✅ A reciprocal economics framework recognizing multiple forms of value contribution
- ✅ Technical infrastructure for the Collective Threshold Model platform
- ✅ Coherent philosophical framework bridging technology and traditional ecological wisdom
- ✅ Trilingual platform supporting cross-border European collaboration (DE/EN/PL)
- ✅ Comprehensive strategic narrative documentation in three languages
- ✅ Database schema with 8 tables, 76 columns, and full privacy model implementation
- ✅ Working web platform deployed at erdpuls.ubec.network

---

## 11. Project Resources

### 11.1 Live Platform
- **Production:** https://erdpuls.ubec.network
- **API Documentation:** https://erdpuls.ubec.network/api/docs

### 11.2 Repository
- Source code in GitHub erdpuls_dashboard repository (authoritative code state)

### 11.3 External Integrations
- **Liberapay:** Donation platform for project support
- **UBECrc Token:** Environmental stewardship blockchain tokens

---

## 12. Licensing

### Code
**GNU Affero General Public License v3.0 (AGPL-3.0)**

### Documentation
**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**

> The material and content are available as Open Educational Resources (OER) and are licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0). To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de

---

*This report was generated based on project knowledge, GitHub repository code, strategic documents, database schema documentation, and conversation history. The GitHub erdpuls_dashboard repository serves as the authoritative source for current code state.*

---

© Michel Garand | Lizenz: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de

*This project uses the services of Claude and Anthropic PBC.*
