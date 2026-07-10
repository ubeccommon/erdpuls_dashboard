# Erdpuls Müllrose Project: Comprehensive Status Report

**Report Date:** 28 January 2026  
**Project:** Erdpuls Müllrose – Center for Sustainability Literacy, Citizen Science and Reciprocal Economics  
**Location:** Müllrose, Brandenburg, Germany (Schlaube Valley Nature Park)  
**Prepared by:** Claude (AI Assistant), in collaboration with Michel Garand

---

## Executive Summary

Erdpuls Müllrose is developing a 3,000 square meter Living Laboratory that integrates environmental monitoring technology with sustainability education. This comprehensive status report is based on examination of the GitHub erdpuls_dashboard repository (authoritative code source), project knowledge documents, database schema documentation, and conversation history through January 2026.

The project has achieved significant milestones in establishing a novel community funding platform (the Collective Threshold Model), developing a coherent philosophical framework, and building functional technical infrastructure. The core platform is operational at `https://erdpuls.ubec.network` with a FastAPI backend, PostgreSQL database, and full trilingual support (English, German, Polish).

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

| Document | Purpose |
|----------|---------|
| `ERDPULS_MULLROSE_COMPREHENSIVE_VISION_INTEGRATED.odt` | Full project vision (51KB) |
| `Erdpuls_Reciprocal_Economics_Business_Model.docx` | Economic framework (16KB) |
| `Erdpuls_Collective_Threshold_Model.docx` | Funding mechanism (13KB) |
| `Erdpuls_Collective_Threshold_Business_Model_Canvas.docx` | Canvas visualization (17KB) |

### 2.3 Key Terminology Decisions (from Conversations)

Recent refinements established important philosophical distinctions:

- **"Symbiosis"** (not "synthesis") — Technology and nature maintaining distinct identities while reciprocally supporting each other
- **"Facts OR Wisdom"** (not "Data OR Wisdom") — Deeper epistemological contrast
- **"The Illusion of Choice"** (not "The False Choice") — More impactful framing
- **"Anthroposophical pedagogy"** (not "Steiner pedagogy") — Greater precision

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
│   ├── auth.py            # Authentication utilities (sessions, password reset)
│   ├── email.py           # Trilingual email system
│   └── routers/
│       ├── __init__.py    # Router exports
│       ├── api.py         # JSON API endpoints
│       ├── web.py         # HTML page routes
│       └── auth.py        # Auth routes (login, register, password reset)
├── templates/             # Jinja2 templates with EN/DE/PL support
├── static/css/            # Stylesheets
├── db/
│   └── scripts/           # SQL migrations (including 006_role_system.sql)
├── deploy/
│   ├── deploy.sh          # Deployment script
│   └── erdpuls-threshold.service  # Systemd service file
├── schema.sql             # Initial database schema
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
├── run.py                 # Development server runner
└── .env                   # Environment configuration (not in repo)
```

### 3.3 API Endpoints (from README.md)

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

### 3.4 Platform URLs

- **Production:** https://erdpuls.ubec.network
- **API Documentation:** https://erdpuls.ubec.network/api/docs
- **Development Path:** `/home/kelpit/UBEC_ERDPULS/`
- **Production Path:** `/var/www/erdpuls-threshold/`

---

## 4. Database Schema

### 4.1 Schema Metadata (from erdpuls_schema_documentation_20260127_174355.md)

| Property | Value |
|----------|-------|
| Generated | 2026-01-27T17:43:55 |
| Schema Name | `erdpuls_threshold` |
| Database Size | 9,297 kB |
| PostgreSQL Version | 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1) |
| UUID Extension | ✅ Enabled |

### 4.2 Schema Summary

| Metric | Count |
|--------|-------|
| Tables | 9 |
| Columns | 92 |
| Relationships | 6 |
| Indexes | 22 |
| Triggers | 1 |
| Functions | 12 |
| Core Erdpuls Tables | 8 |
| Privacy-Sensitive Tables | 2 |

### 4.3 Core Tables

| Table | Purpose | Current Rows |
|-------|---------|--------------|
| `users` | User accounts with authentication credentials | 2 |
| `roles` | Role definitions for permission hierarchy | 5 |
| `offerings` | Workshops, courses, events with threshold-based funding | 1 |
| `registrations` | Participation intentions (separate from contributions) | 0 |
| `contributions` | Contributions—NO contributor identification stored | 0 |
| `contribution_contacts` | Separated contact info for operational purposes | 0 |
| `regeneration_fund` | Community reserve from surplus contributions | 0 |
| `token_rates` | Exchange rates for UBECrc tokens to EUR | 2 |
| `hours_rates` | Valuation rates for different contribution hours | 6 |

### 4.4 Privacy Model

> **Community-Anonymous, Operationally-Known**

- **Public visibility:** Aggregates only (total amount, contributor count)
- **Organizer visibility:** Individual contributions + linked contact info
- **No individual amounts displayed publicly**

### 4.5 Contribution Types

| Type | Description |
|------|-------------|
| `euro` | Direct monetary contribution in EUR |
| `token` | UBECrc tokens earned through environmental stewardship (~70 tokens = €1) |
| `hours` | Pre-arranged work valued by category (garden labor, technical, etc.) |

### 4.6 Hours Rate Categories

| Category | EUR/Hour | Description |
|----------|----------|-------------|
| `garden_labor` | €10 | Weeding, planting, harvesting, composting |
| `administrative` | €12 | Communication, scheduling, outreach |
| `skilled_labor` | €20 | Carpentry, electrical, sensor installation |
| `translation` | €20 | DE/EN/PL translation, documentation |
| `knowledge_sharing` | €25 | Leading sessions, mentoring, traditional knowledge |
| `technical_support` | €30 | Data processing, sensor calibration, web development |

### 4.7 Database Relationships Diagram

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

---

## 5. Role System

### 5.1 Five-Tier Role Hierarchy (from 006_role_system.sql)

| Role | Level | Description | Capabilities |
|------|-------|-------------|--------------|
| `member` | 10 | Default for new registrations | Participate, contribute |
| `creator` | 20 | Content creators | Create offerings (requires approval) |
| `facilitator` | 30 | Trusted creators | Direct publishing without approval |
| `moderator` | 50 | Community managers | Approve offerings, access admin panel |
| `admin` | 100 | Full access | Complete system access |

### 5.2 Role-Based Permissions

| Permission | member | creator | facilitator | moderator | admin |
|------------|--------|---------|-------------|-----------|-------|
| Create Offering | ❌ | ✅ | ✅ | ✅ | ✅ |
| Publish Direct | ❌ | ❌ | ✅ | ✅ | ✅ |
| Approve Offerings | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage Users | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 6. Collective Threshold Model

### 6.1 Core Mechanism

The Collective Threshold Model transforms community funding through five steps:

1. **Transparent Need** – Each offering publishes exactly what resources it needs
2. **Register Intention** – People express desire to participate (separate from payment)
3. **Anonymous Contribution** – Everyone contributes to a collective pot
4. **Threshold Met** – When the threshold is reached, the offering happens
5. **No One Knows** – No one knows who contributed what, dissolving stigma

### 6.2 Offering Financial Breakdown

Offerings can specify costs across categories:

- Facilitator cost
- Materials cost
- Meals cost
- Space cost
- Sustainability contribution

### 6.3 Surplus Handling

When contributions exceed the threshold, surplus flows to the Regeneration Fund, which supports future community offerings.

---

## 7. Reciprocal Economics Business Model

### 7.1 Four Pathways of Participation

| Pathway | How It Works | Philosophical Basis |
|---------|--------------|---------------------|
| **Sustaining Contribution** (Full Rate) | Pay listed price (supports operations + others) | Plant generosity: giving more than taking |
| **Community-Held Participation** (Supported Rate) | Pay 50-80% (self-selected, no justification needed) | Ubuntu: individual wellbeing depends on community |
| **Skills-Based Exchange** (Contribution) | Offset costs through labor, skills, or service | Reciprocity: value flows in multiple directions |
| **Token Exchange** | Use earned UBECrc tokens | Environmental stewardship recognized as value |

### 7.2 Target Financial Sustainability

- **40%** Full rate participants
- **40%** Supported rate participants
- **20%** Contribution/token participants
- Full rates set to cover operational costs + 25% community subsidy pool

### 7.3 Communication Language Guidelines

The project deliberately avoids charity framing:

| Avoid | Use Instead |
|-------|-------------|
| "Scholarship" or "Financial aid" | "Supported rate" |
| "Discounted" or "Reduced" | "Different pathways to participation" |
| "Charity" or "Donation" | "Reciprocal exchange" |
| "Those who can afford it" | "Those choosing to support others" |
| "Pay what you can" | "Choose the pathway that fits your situation" |

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
| Role-based permissions | ✅ Complete | Five-tier hierarchy implemented |
| Registration flow | ✅ Complete | Intention separate from contribution |
| Contribution flow | ✅ Complete | Euro, tokens, hours with confirmation |
| Privacy model | ✅ Complete | Separate contacts table implemented |
| Trilingual UI | ✅ Complete | EN/DE/PL language switching |
| Organizer dashboard | ✅ Complete | Manage offerings, view contributions |
| Progress tracking | ✅ Complete | Threshold visualization |
| Regeneration Fund | ✅ Complete | Balance tracking, surplus processing |
| Legal pages | ✅ Complete | Impressum, Privacy Policy, Terms of Service |
| Database documentation generator | ✅ Complete | Adapted from UBEC IOT project |
| Email contribution confirmation | ⚠️ Partial | Code complete, SMTP intermittently blocked |
| Email password reset | ⚠️ Partial | Code complete, SMTP intermittently blocked |

### 8.2 Authentication System Details

The authentication system implements:

- **Session tokens** using itsdangerous with configurable expiry
- **Password reset tokens** with 1-hour expiry
- **Email enumeration protection** (always shows success on forgot-password)
- **Clean URL paths** (`/r/{token}` instead of `/reset-password?token=`) to avoid spam filter triggers
- **Session refresh** on user activity to extend inactivity timeout

### 8.3 Email System Status

The email system is fully implemented with:

- Trilingual email templates (EN/DE/PL)
- HTML + plain text versions
- Contribution confirmation emails
- Password reset emails

**Current Issue:** MailChannels (spam filtering service used by hosting provider) has intermittently blocked outbound emails. DNS records (SPF, DKIM, DMARC, PTR) are documented as valid. The user has trained spam filters by clicking "Not Spam" in MailChannels console.

**Documented Reference:** `auid=instrampxe0y3a`

**Workarounds Attempted:**
- Simplified email templates
- Subject line modifications to avoid trigger words
- Matching HTML structure of working emails
- Using `/r/` URL path instead of `/reset-password?token=`

---

## 9. Outstanding Items and Recommendations

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

---

## 11. Achievements Summary

Based on documented evidence, the project has established:

- ✅ A novel community funding model combining threshold-based funding with privacy protection
- ✅ A reciprocal economics framework recognizing multiple forms of value contribution
- ✅ Technical infrastructure for the Collective Threshold Model platform
- ✅ Coherent philosophical framework bridging technology and traditional ecological wisdom
- ✅ Trilingual platform supporting cross-border European collaboration (DE/EN/PL)
- ✅ Comprehensive strategic narrative documentation in three languages
- ✅ Database schema with 9 tables, 92 columns, and full privacy model implementation
- ✅ Working web platform deployed at erdpuls.ubec.network
- ✅ Five-tier role-based permission system
- ✅ Complete authentication system with password reset and session management

---

## 12. Project Resources

### 12.1 Live Platform
- **Production:** https://erdpuls.ubec.network
- **API Documentation:** https://erdpuls.ubec.network/api/docs

### 12.2 Repository
- Source code in GitHub erdpuls_dashboard repository (authoritative code state)

### 12.3 External Integrations
- **Liberapay:** Donation platform for project support
- **UBECrc Token:** Environmental stewardship blockchain tokens

### 12.4 Environment Configuration

Key environment variables (`.env` file):

```
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

## 13. Licensing

### Code
**GNU Affero General Public License v3.0 (AGPL-3.0)**

### Documentation
**Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**

> The material and content are available as Open Educational Resources (OER) and are licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0). To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/4.0/deed.de

---

*This report was generated based on project knowledge, GitHub repository code, strategic documents, database schema documentation (erdpuls_schema_documentation_20260127_174355.md), and conversation history. The GitHub erdpuls_dashboard repository serves as the authoritative source for current code state.*

---

© Michel Garand | Lizenz: CC BY-SA 4.0 | https://creativecommons.org/licenses/by-sa/4.0/deed.de

*This project uses the services of Claude and Anthropic PBC.*
