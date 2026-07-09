# Erdpuls Müllrose Project Status Report

**Date:** 26 January 2026  
**Prepared by:** Claude (AI Assistant), with Michel Garand (Project Lead)  
**Project:** Erdpuls Müllrose – Center for Sustainability Literacy, Citizen Science and Reciprocal Economics  
**Location:** Müllrose, Brandenburg, Germany (Schlaube Valley Nature Park)

---

## Executive Summary

Erdpuls Müllrose is developing a 3,000 square meter Living Laboratory that integrates environmental monitoring technology with sustainability education. The project has made significant progress in establishing its philosophical framework, developing a novel community funding platform (the Collective Threshold Model), and building the technical infrastructure to support reciprocal economics and privacy-protected contributions.

The core platform is operational with a functional FastAPI application deployed at `erdpuls.ubec.network`. Recent development has focused on implementing a nuanced privacy model that balances anonymity ideals with practical operational requirements, along with trilingual support (English, German, Polish) and email confirmation systems.

---

## 1. Project Vision and Philosophy

### 1.1 Core Mission

Erdpuls Müllrose addresses what the project calls the "Values-Action Gap"—the disconnect between environmental awareness (84% of European youth value sustainability) and actual sustainable behavior (only 30% translate this into action). The project cultivates conditions for people to "think like a plant," developing ecological-digital fluency through direct experience and contemplative practice.

### 1.2 Philosophical Foundations

The project rejects what it terms the "Illusion of Choice" between:
- **Technology OR Nature** → Instead: Technology and nature as complementary expressions (symbiosis)
- **Facts OR Wisdom** → Instead: Integrated epistemological approaches
- **Progress OR Preservation** → Instead: Regenerative development

Key philosophical influences include:
- **Ubuntu Philosophy** ("I am because we are") – Community interdependence
- **Anthroposophical Pedagogy** – Contemplative practice and phenomenological observation
- **Permaculture Design** – Practical patterns from living systems
- **Goethean Science** – Qualitative observation methodology

### 1.3 Plant Wisdom Framework

The pedagogical approach draws from seven characteristics of plant intelligence:
1. **Rootedness** – Commitment to place and transforming difficulty
2. **Generosity** – Giving more than taking (economy of abundance)
3. **Transformation** – Participating in energy transformation, not extraction
4. **Distributed Intelligence** – Wisdom without centralization
5. **Network Thinking** – Resource sharing through interconnection
6. **Rhythmic Living** – Alignment with natural cycles
7. **Patient Accumulation** – Steady growth over time

---

## 2. Technical Infrastructure

### 2.1 Platform Architecture

**Production Environment:**
- **Domain:** `erdpuls.ubec.network`
- **Backend:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL (schema: `erdpuls_threshold`)
- **Frontend:** Jinja2 templates + vanilla JavaScript + CSS
- **Server:** Ubuntu Linux, Caddy reverse proxy, systemd service
- **Port:** 8004 (behind Caddy on ports 80/443)

**Server Infrastructure:**
```
Internet → Caddy (80/443)
              │
              ├── living-labs.ubec.network  → localhost:8000
              ├── bioregional.ubec.network  → localhost:8001
              ├── api.ubec.network          → localhost:8002
              ├── iot.ubec.network          → localhost:8003
              ├── erdpuls.ubec.network      → localhost:8004 ✓
              └── mapservice.ubec.network   → localhost:8080
```

### 2.2 Database Schema

The `erdpuls_threshold` schema implements the Collective Threshold Model with the following core tables:

| Table | Purpose |
|-------|---------|
| `users` | User accounts with role-based access (user, admin) |
| `offerings` | Workshops, courses, events with threshold amounts and multilingual content |
| `registrations` | Intention to participate (separate from contributions) |
| `contributions` | Anonymous contributions (Euro, tokens, hours) – no identifying information |
| `contribution_contacts` | **Separated** contact information for operational purposes only |
| `regeneration_fund` | Community reserve from surplus contributions |
| `token_rates` | UBECrc to EUR exchange rates (default: 70 UBECrc = €1.00) |
| `hours_rates` | Hourly rates by contribution category |

**Hours Rate Categories (with EUR/hour values):**
- Garden Labor: €11.00
- Administrative: €12.50
- Skilled Labor: €20.00
- Translation: €22.50
- Knowledge Sharing: €27.50
- Technical Support: €30.00

### 2.3 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/offerings` | GET | List all open offerings |
| `/api/offerings/{id}` | GET | Get offering details |
| `/api/offerings/{id}/progress` | GET | Funding progress (aggregates only) |
| `/api/offerings/{id}/register` | POST | Register intention to participate |
| `/api/offerings/{id}/contribute/euro` | POST | Anonymous Euro contribution |
| `/api/offerings/{id}/contribute/token` | POST | Anonymous token contribution |
| `/api/offerings/{id}/contribute/hours` | POST | Anonymous hours contribution |
| `/api/fund/balance` | GET | Regeneration Fund balance |
| `/api/rates/tokens` | GET | Current token exchange rate |
| `/api/rates/hours` | GET | Hours contribution rates |
| `/api/docs` | GET | Interactive API documentation (Swagger) |

### 2.4 Key Code Components

```
erdpuls-threshold/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Pydantic settings (including SMTP)
│   ├── database.py       # SQLAlchemy setup with schema search_path
│   ├── models.py         # Database models (User, Offering, Contribution, etc.)
│   ├── schemas.py        # Pydantic schemas for API validation
│   ├── auth.py           # Authentication utilities
│   ├── email.py          # Trilingual email confirmation system
│   └── routers/
│       ├── api.py        # JSON API endpoints
│       ├── web.py        # HTML page routes
│       └── auth.py       # Auth routes (login, register, dashboard)
├── templates/            # Jinja2 templates with EN/DE/PL support
├── static/css/           # Stylesheet
├── db/scripts/           # SQL migrations
├── deploy/               # Deployment configuration
└── run.py                # Development server runner
```

---

## 3. Collective Threshold Model

### 3.1 Core Mechanism

The Collective Threshold Model transforms community funding through five steps:

1. **Transparent Need** – Each offering publishes exactly what resources it needs
2. **Register Intention** – People express desire to participate (separate from payment)
3. **Anonymous Contribution** – Everyone contributes to a collective pot
4. **Threshold Met** – When the threshold is reached, the offering happens
5. **No One Knows** – Individual contribution amounts remain private

### 3.2 Privacy Model: "Community-Anonymous, Operationally-Known"

A key development was transitioning from "fully anonymous" to a nuanced privacy model:

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

### 3.3 Contribution Types

| Type | How It Works | Exchange Rate |
|------|--------------|---------------|
| **Euro** | Direct financial contribution | 1:1 |
| **UBECrc Tokens** | Environmental stewardship tokens | 70 tokens = €1.00 |
| **Hours** | Skill/labor contribution | €10-40/hour (by category) |

### 3.4 Regeneration Fund

Surplus contributions flow into a community Regeneration Fund that can:
- Cover shortfalls for offerings that almost reach threshold
- Seed new offerings
- Support community resilience

Transaction types tracked: `surplus_in`, `shortfall_cover`, `seed_offering`, `adjustment`

---

## 4. Reciprocal Economics Business Model

### 4.1 Four Pathways of Participation

| Pathway | How It Works | Philosophical Basis |
|---------|--------------|---------------------|
| **Full Rate** | Pay listed price (supports operations + others) | Plant generosity: giving more than taking |
| **Supported Rate** | Pay 50-80% (self-selected, no justification needed) | Ubuntu: individual wellbeing depends on community |
| **Contribution** | Offset costs through labor, skills, or service | Reciprocity: value flows in multiple directions |
| **Token Exchange** | Use earned UBECrc tokens | Environmental stewardship recognized as value |

### 4.2 Target Financial Sustainability

- **40%** Full rate participants
- **40%** Supported rate participants
- **20%** Contribution/token participants
- Full rates set to cover operational costs + 25% community subsidy pool

### 4.3 Communication Language Guidelines

The project deliberately avoids charity framing:

| Avoid | Use Instead |
|-------|-------------|
| "Scholarship" | "Supported rate" |
| "Discounted" | "Different pathways to participation" |
| "Charity" | "Reciprocal exchange" |
| "Those who can afford it" | "Those choosing to support others" |
| "Pay what you can" | "Choose the pathway that fits your situation" |

---

## 5. Strategic Narrative Documents

### 5.1 Multilingual Documentation

The project maintains strategic narratives in three languages:
- **English:** `Erdpuls_Strategic_Narrative.odt`
- **German:** `Erdpuls_Strategische_Erzaehlung_DE.docx`
- **Polish:** `Erdpuls_Narracja_Strategiczna_PL.docx`

**Key Branding Decision:** The English subtitle "Center for Sustainability Literacy, Citizen Science and Reciprocal Economics" is maintained across all language versions for unified international branding.

### 5.2 Supporting Documents

- `ERDPULS_MULLROSE_COMPREHENSIVE_VISION_INTEGRATED.odt` – Full project vision (~51KB)
- `Erdpuls_Reciprocal_Economics_Business_Model.docx` – Economic framework
- `Erdpuls_Collective_Threshold_Model.docx` – Funding mechanism
- `Erdpuls_Collective_Threshold_Business_Model_Canvas.docx` – Canvas visualization

### 5.3 Key Terminology Decisions

Recent refinements established important philosophical distinctions:
- **"Symbiosis"** (not "synthesis") – Technology and nature maintaining distinct identities while reciprocally supporting each other
- **"Facts OR Wisdom"** (not "Data OR Wisdom") – Deeper epistemological contrast
- **"The Illusion of Choice"** (not "The False Choice") – More impactful framing
- **"Anthroposophical pedagogy"** (not "Steiner pedagogy") – Greater precision

---

## 6. Current Implementation Status

### 6.1 Completed Features

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
| Email confirmation | ⚠️ Partial | Code complete, SMTP blocked |

### 6.2 Email System Status

The email confirmation system is fully implemented with:
- Trilingual email templates (EN/DE/PL)
- HTML + plain text versions
- Contribution summary display
- Privacy reminders
- Next steps guidance

**Current Issue:** MailChannels (spam filtering service) has blocked the `erdpuls@ubec.network` account at the hosting provider level. DNS records (SPF, DKIM, DMARC, PTR) are all valid.

**Recommended Actions:**
1. Contact hostingww.com to resolve MailChannels block (Reference: `auid=instrampxe0y3a`)
2. Alternative: Configure external SMTP service (e.g., Brevo/Sendinblue)

### 6.3 Database Migration Status

| Migration | Status |
|-----------|--------|
| Initial schema | ✅ Applied |
| Users table | ✅ Applied |
| 003_contribution_contacts.sql | ✅ Applied |

---

## 7. Outstanding Items and Next Steps

### 7.1 Immediate Technical Tasks

1. **Resolve Email Delivery**
   - Contact hosting provider about MailChannels block
   - Or configure alternative SMTP provider

2. **Database Documentation Generator**
   - Recently adapted from UBEC IOT project
   - Generates comprehensive schema documentation
   - License: CC BY-NC-SA 4.0

### 7.2 Platform Enhancements

1. Threshold notification system (when offerings reach goal)
2. Contribution status workflow (pending → confirmed → completed)
3. Hours scheduling interface for organizers
4. Token integration with blockchain infrastructure

### 7.3 Content Development

1. Seed initial offerings for platform testing
2. Develop curriculum materials (EU GreenComp aligned)
3. Create user onboarding documentation

### 7.4 Strategic Development

The project follows a seven-year development cycle:
- **Years 1-2 (Current):** Germination – System proof, community gathering
- **Years 3-4:** Growth – Ten schools join, bioregion awakens
- **Years 5-6:** Flowering – Research publication, policy influence
- **Year 7:** Fruiting – Model replication, paradigm establishment

---

## 8. Achievements and Milestones

The project has established:
- 🌍 A novel community funding model combining threshold-based funding with privacy protection
- 🌍 A reciprocal economics framework recognizing multiple forms of value contribution
- 🌍 Technical infrastructure integrating IoT environmental monitoring with Web3 tokens
- 🌍 Coherent philosophical framework bridging technology and traditional ecological wisdom
- 🌍 Trilingual platform supporting cross-border European collaboration

---

## 9. Licensing

All project materials follow these licensing requirements:

**Code:** GNU Affero General Public License v3.0 (AGPL-3.0)

**Documentation:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)

> The material and content are available as Open Educational Resources (OER) and are licensed under Creative Commons Attribution – ShareAlike 4.0 International (CC BY-NC-SA 4.0). To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en

---

## 10. Project Resources

### 10.1 Live Platform
- **Production:** https://erdpuls.ubec.network
- **API Documentation:** https://erdpuls.ubec.network/api/docs

### 10.2 Repository
- Source code in GitHub erdpuls_dashboard repository (authoritative code state)
- Deployment path: `/var/www/erdpuls-threshold/` (production) or `/home/kelpit/UBEC_ERDPULS/` (development)

### 10.3 External Integrations
- **Liberapay:** Donation platform for project support
- **UBECrc Token:** Environmental stewardship blockchain tokens

---

## Appendix A: Environment Configuration

Key environment variables (`.env` file):

```
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

---

## Appendix B: Database Schema Diagram

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

*This report was generated based on project knowledge, code repositories, strategic documents, and conversation history. The GitHub erdpuls_dashboard repository serves as the authoritative source for current code state.*

---

© Michel Garand | License: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en
