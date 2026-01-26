# 🌱 Erdpuls Collective Threshold Model

A community-held approach to reciprocal economics, built with FastAPI.

> "The community holds each offering into being."

## Overview

The Collective Threshold Model transforms how we fund community offerings:

1. **Transparent Need** — Each offering publishes exactly what resources it needs
2. **Register Intention** — People express desire to participate (separate from payment)
3. **Anonymous Contribution** — Everyone contributes to a collective pot anonymously
4. **Threshold Met** — When the threshold is reached, the offering happens
5. **No One Knows** — No one knows who contributed what, dissolving stigma

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL (schema: `erdpuls_threshold`)
- **Frontend:** Jinja2 templates + vanilla JS
- **Languages:** English, German, Polish

## Project Structure

```
erdpuls-threshold/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Pydantic settings
│   ├── database.py       # SQLAlchemy setup
│   ├── models.py         # Database models
│   ├── schemas.py        # Pydantic schemas
│   └── routers/
│       ├── api.py        # JSON API endpoints
│       └── web.py        # HTML page routes
├── templates/            # Jinja2 templates
├── static/               # CSS, JS
├── deploy/               # Deployment files
├── schema.sql            # Database schema
├── requirements.txt
└── run.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/offerings` | GET | List all open offerings |
| `/api/offerings/{id}` | GET | Get offering details |
| `/api/offerings/{id}/progress` | GET | Get funding progress (aggregate only) |
| `/api/offerings/{id}/register` | POST | Register intention |
| `/api/offerings/{id}/contribute/euro` | POST | Anonymous euro contribution |
| `/api/offerings/{id}/contribute/token` | POST | Anonymous token contribution |
| `/api/offerings/{id}/contribute/hours` | POST | Anonymous hours contribution |
| `/api/fund/balance` | GET | Regeneration Fund balance |
| `/api/rates/tokens` | GET | Current token exchange rate |
| `/api/rates/hours` | GET | Hours contribution rates |
| `/api/docs` | GET | Interactive API documentation |

## Quick Start (Development)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/ubec_erdpuls"
export SECRET_KEY="dev-secret-key"

# Run the schema (first time only)
psql -d ubec_erdpuls -f schema.sql

# Run development server
python run.py
```

Visit http://localhost:8004

API docs at http://localhost:8004/api/docs

## Deployment

See `deploy/DEPLOY.md` for production deployment instructions.

## Anonymity Architecture

**Critical Design Decision:** The `contributions` table stores NO contributor identification:

```sql
CREATE TABLE contributions (
    id UUID PRIMARY KEY,
    offering_id UUID NOT NULL,
    amount_eur DECIMAL(10,2) NOT NULL,
    contribution_type VARCHAR(50),
    contributed_at TIMESTAMP
    -- NO contributor_id, NO email, NO IP address
);
```

Only aggregate totals are ever displayed. Even administrators cannot see who contributed what.

## Three Contribution Types

1. **Euro (€)** — Direct monetary contribution
2. **UBECrc Tokens** — Earned through environmental stewardship (70 tokens = €1)
3. **Hours** — Pre-arranged work valued by category

## License

© Farmer | CC BY-NC-SA 4.0

This material is available as an Open Educational Resource (OER).
https://creativecommons.org/licenses/by-nc-sa/4.0/
