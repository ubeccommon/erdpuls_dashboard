# 🌱 Erdpuls Collective Threshold Model - Database Schema Documentation

> **Single Source of Truth** for the Erdpuls Platform database structure

---

## Metadata

| Property | Value |
|----------|-------|
| Generated | 2026-01-28T18:23:31.572955 |
| Schema | `erdpuls_threshold` |
| Database Size | 9321 kB |
| PostgreSQL | PostgreSQL 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1) o... |
| UUID Extension | ✅ Enabled |
| Author | Farmer |
| License | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de) |

## Table of Contents

1. [Summary](#summary)
2. [Contribution Model](#contribution-model)
3. [Tables](#tables)
4. [Relationships](#relationships)
5. [Indexes](#indexes)
6. [Functions](#functions)

## Summary

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

## Contribution Model

### Privacy Model

> **Community-Anonymous, Operationally-Known**

- **Public visibility:** Aggregates only (total amount, contributor count)
- **Organizer visibility:** Individual contributions + linked contact info
- **No individual amounts displayed publicly**

### Contribution Types

| Type | Description |
|------|-------------|
| `euro` | Direct monetary contribution in EUR |
| `token` | UBECrc tokens earned through environmental stewardship (~70 tokens = €1) |
| `hours` | Pre-arranged work valued by category (garden labor, technical, etc.) |

### Hours Contribution Rates

| Category | €/Hour | Description |
|----------|--------|-------------|
| `administrative` | €12.5 | Communication, scheduling, outreach, event support |
| `garden_labor` | €11.0 | Weeding, planting, harvesting, composting, watering |
| `knowledge_sharing` | €27.5 | Leading a session, mentoring, traditional knowledge transmission |
| `skilled_labor` | €20.0 | Carpentry, electrical, sensor installation, equipment repair |
| `technical_support` | €30.0 | Data processing, sensor calibration, web development |
| `translation` | €22.5 | DE/EN/PL translation, documentation, content creation |

### Token Exchange Rates

- **Current rate:** 70.0 UBECrc = €1
- Approximately 70 UBECrc = €1

### Regeneration Fund

- **Current Balance:** €150.00
- **Purpose:** Community reserve from surplus contributions

## Tables

### contribution_contacts 🏛️ 🔒

> Separated contact info for operational purposes only

**Rows:** 20 | **Size:** 64 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | gen_random_uuid() |
| `contribution_id` | uuid | ✗ | - |
| `name` | varchar(255) | ✓ | - |
| `email` | varchar(255) | ✓ | - |
| `phone` | varchar(50) | ✓ | - |
| `notes` | text | ✓ | - |
| `created_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |

**Constraints:**

- `contribution_contacts_contribution_id_fkey` (FOREIGN KEY)
- `contribution_contacts_pkey` (PRIMARY KEY)

---

### contributions 🏛️ 🔒

> ANONYMOUS contributions - no contributor identification stored!

**Rows:** 27 | **Size:** 64 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | erdpuls_threshold.uuid_generat |
| `offering_id` | uuid | ✗ | - |
| `amount_eur` | numeric(10,2) | ✗ | - |
| `contribution_type` | varchar(50) | ✓ | 'euro'::character varying |
| `token_amount` | numeric(15,2) | ✓ | - |
| `hours_description` | text | ✓ | - |
| `hours_equivalent_eur` | numeric(10,2) | ✓ | - |
| `contributed_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |
| `hours_category` | varchar(100) | ✓ | - |
| `hours_amount` | numeric(5,2) | ✓ | - |
| `status` | varchar(50) | ✓ | 'pending'::character varying |
| `wants_to_participate` | boolean | ✓ | false |
| `engagement_type` | varchar(50) | ✓ | 'support_only'::character vary |

**Constraints:**

- `contributions_contribution_type_check` (CHECK)
- `contributions_engagement_type_check` (CHECK)
- `contributions_offering_id_fkey` (FOREIGN KEY)
- `contributions_pkey` (PRIMARY KEY)
- `contributions_status_check` (CHECK)

---

### hours_rates 🏛️

> Valuation rates for different types of contribution hours

**Rows:** 6 | **Size:** 48 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | erdpuls_threshold.uuid_generat |
| `category` | varchar(100) | ✗ | - |
| `eur_per_hour` | numeric(10,2) | ✗ | - |
| `description` | text | ✓ | - |
| `created_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |
| `description_de` | text | ✓ | - |
| `description_pl` | text | ✓ | - |

**Constraints:**

- `hours_rates_category_key` (UNIQUE)
- `hours_rates_pkey` (PRIMARY KEY)

---

### offerings 🏛️

> Workshops, courses, events with threshold-based funding model

**Rows:** 3 | **Size:** 64 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | erdpuls_threshold.uuid_generat |
| `title` | varchar(255) | ✗ | - |
| `title_de` | varchar(255) | ✓ | - |
| `title_pl` | varchar(255) | ✓ | - |
| `description` | text | ✗ | - |
| `description_de` | text | ✓ | - |
| `description_pl` | text | ✓ | - |
| `threshold_amount` | numeric(10,2) | ✗ | - |
| `facilitator_cost` | numeric(10,2) | ✓ | 0 |
| `materials_cost` | numeric(10,2) | ✓ | 0 |
| `meals_cost` | numeric(10,2) | ✓ | 0 |
| `space_cost` | numeric(10,2) | ✓ | 0 |
| `sustainability_contribution` | numeric(10,2) | ✓ | 0 |
| `event_date` | timestamp without time zone | ✓ | - |
| `registration_deadline` | timestamp without time zone | ✗ | - |
| `contribution_deadline` | timestamp without time zone | ✗ | - |
| `status` | varchar(50) | ✓ | 'open'::character varying |
| `min_participants` | integer | ✓ | 1 |
| `max_participants` | integer | ✓ | - |
| `created_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |
| `updated_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |
| `created_by` | varchar(255) | ✓ | - |
| `creator_id` | uuid | ✓ | - |
| `organizer_name` | varchar(255) | ✓ | - |
| `organizer_email` | varchar(255) | ✓ | - |
| `organizer_phone` | varchar(50) | ✓ | - |
| `delivery_language` | array | ✓ | ARRAY['de'::character varying( |

**Constraints:**

- `offerings_creator_id_fkey` (FOREIGN KEY)
- `offerings_delivery_language_check` (CHECK)
- `offerings_pkey` (PRIMARY KEY)
- `offerings_status_check` (CHECK)

---

### regeneration_fund 🏛️

> Community reserve from surplus contributions

**Rows:** 1 | **Size:** 32 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | erdpuls_threshold.uuid_generat |
| `amount` | numeric(10,2) | ✗ | - |
| `transaction_type` | varchar(50) | ✗ | - |
| `offering_id` | uuid | ✓ | - |
| `description` | text | ✓ | - |
| `created_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |

**Constraints:**

- `regeneration_fund_offering_id_fkey` (FOREIGN KEY)
- `regeneration_fund_pkey` (PRIMARY KEY)
- `regeneration_fund_transaction_type_check` (CHECK)

---

### registrations 🏛️

> Participation intentions (separate from contributions for privacy)

**Rows:** 5 | **Size:** 80 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | erdpuls_threshold.uuid_generat |
| `offering_id` | uuid | ✗ | - |
| `email` | varchar(255) | ✗ | - |
| `name` | varchar(255) | ✓ | - |
| `referral_source` | varchar(255) | ✓ | - |
| `status` | varchar(50) | ✓ | 'registered'::character varyin |
| `registered_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |
| `linked_contribution_id` | uuid | ✓ | - |
| `registration_type` | varchar(50) | ✓ | 'participate_only'::character  |

**Constraints:**

- `registrations_linked_contribution_id_fkey` (FOREIGN KEY)
- `registrations_offering_id_email_key` (UNIQUE)
- `registrations_offering_id_fkey` (FOREIGN KEY)
- `registrations_pkey` (PRIMARY KEY)
- `registrations_registration_type_check` (CHECK)
- `registrations_status_check` (CHECK)

---

### roles

**Rows:** 5 | **Size:** 32 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `name` | varchar(50) | ✗ | - |
| `level` | integer | ✗ | - |
| `description` | text | ✓ | - |
| `description_de` | text | ✓ | - |
| `description_pl` | text | ✓ | - |
| `can_create_offering` | boolean | ✓ | false |
| `can_publish_direct` | boolean | ✓ | false |
| `can_approve_offerings` | boolean | ✓ | false |
| `can_manage_users` | boolean | ✓ | false |
| `created_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |

**Constraints:**

- `roles_pkey` (PRIMARY KEY)

---

### token_rates 🏛️

> Exchange rates for UBECrc tokens to EUR

**Rows:** 2 | **Size:** 24 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | erdpuls_threshold.uuid_generat |
| `tokens_per_eur` | numeric(15,4) | ✗ | 70.0 |
| `effective_from` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |
| `effective_until` | timestamp without time zone | ✓ | - |
| `created_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |

**Constraints:**

- `token_rates_pkey` (PRIMARY KEY)

---

### users 🏛️

> User accounts with authentication credentials (admin/user roles)

**Rows:** 2 | **Size:** 80 kB

| Column | Type | Nullable | Default |
|--------|------|----------|--------|
| `id` | uuid | ✗ | erdpuls_threshold.uuid_generat |
| `email` | varchar(255) | ✗ | - |
| `password_hash` | varchar(255) | ✗ | - |
| `name` | varchar(255) | ✓ | - |
| `role` | varchar(50) | ✓ | 'user'::character varying |
| `is_active` | boolean | ✓ | true |
| `email_verified` | boolean | ✓ | false |
| `created_at` | timestamp without time zone | ✓ | CURRENT_TIMESTAMP |
| `last_login` | timestamp without time zone | ✓ | - |

**Constraints:**

- `users_email_key` (UNIQUE)
- `users_pkey` (PRIMARY KEY)
- `users_role_check` (CHECK)

---

## Relationships

| From Table | Column | To Table | Column | On Delete |
|------------|--------|----------|--------|----------|
| `contribution_contacts` | contribution_id | `contributions` | id | CASCADE |
| `contributions` | offering_id | `offerings` | id | CASCADE |
| `offerings` | creator_id | `users` | id | SET NULL |
| `regeneration_fund` | offering_id | `offerings` | id | SET NULL |
| `registrations` | linked_contribution_id | `contributions` | id | SET NULL |
| `registrations` | offering_id | `offerings` | id | CASCADE |

## Indexes

### contribution_contacts

- 🔑 `contribution_contacts_pkey` on (id)
- 📇 `idx_contribution_contacts_contribution_id` on (contribution_id)
- 📇 `idx_contribution_contacts_email` on (email)

### contributions

- 🔑 `contributions_pkey` on (id)
- 📇 `idx_contributions_date` on (contributed_at)
- 📇 `idx_contributions_offering` on (offering_id)

### hours_rates

- 🔒 `hours_rates_category_key` on (category)
- 🔑 `hours_rates_pkey` on (id)

### offerings

- 📇 `idx_offerings_dates` on (registration_deadline, contribution_deadline)
- 📇 `idx_offerings_status` on (status)
- 🔑 `offerings_pkey` on (id)

### regeneration_fund

- 🔑 `regeneration_fund_pkey` on (id)

### registrations

- 📇 `idx_registrations_linked_contribution` on (linked_contribution_id)
- 📇 `idx_registrations_offering` on (offering_id)
- 🔒 `registrations_offering_id_email_key` on (offering_id, email)
- 🔑 `registrations_pkey` on (id)

### roles

- 🔑 `roles_pkey` on (name)

### token_rates

- 🔑 `token_rates_pkey` on (id)

### users

- 📇 `idx_users_email` on (email)
- 📇 `idx_users_role` on (role)
- 🔒 `users_email_key` on (email)
- 🔑 `users_pkey` on (id)

## Functions

### check_offering_threshold

- **Returns:** trigger
- **Arguments:** none
- **Language:** plpgsql

### process_offering_surplus

- **Returns:** numeric
- **Arguments:** offering_uuid uuid
- **Language:** plpgsql

### uuid_generate_v1

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

### uuid_generate_v1mc

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

### uuid_generate_v3

- **Returns:** uuid
- **Arguments:** namespace uuid, name text
- **Language:** c

### uuid_generate_v4

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

### uuid_generate_v5

- **Returns:** uuid
- **Arguments:** namespace uuid, name text
- **Language:** c

### uuid_nil

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

### uuid_ns_dns

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

### uuid_ns_oid

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

### uuid_ns_url

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

### uuid_ns_x500

- **Returns:** uuid
- **Arguments:** none
- **Language:** c

---

*This project uses the services of Claude and Anthropic PBC to inform our decisions and recommendations.*

*Generated by Erdpuls Collective Threshold Model Schema Documenter v1.0.0*

---

© Farmer | License: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
