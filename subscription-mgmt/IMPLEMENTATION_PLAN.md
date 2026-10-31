# Brightloop Subscription Management System (SMS)
## Hackathon Architecture & Implementation Blueprint

---

### Executive Summary
Brightloop Software requires a unified, full-lifecycle subscription management and recurring billing platform. This document outlines the clean, ground-up architecture and implementation plan designed to eliminate spreadsheet reliance, automate invoice generation and recurring billing cycles, provide real-time payment reconciliation, and deliver role-tailored user interfaces for administrators, staff, and customers.

---

### 1. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Frontend (React 18 + TS)                        │
│   ├── Admin Portal: Subscriptions, Invoices, Plans, Taxes, Reports     │
│   ├── Staff Portal: Daily ops, state transitions, payment collection   │
│   └── Customer Portal: Self-service subscriptions, PDF invoices        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST + JWT
┌───────────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Backend Engine                           │
│  /auth        /users       /products    /plans       /subscriptions    │
│  /tax-rules   /discounts   /invoices    /payments    /portal  /reports │
└─────────────┬─────────────────────────────┬────────────────────────────┘
              │                             │
              ▼ SQLAlchemy                  ▼ Celery Tasks
┌──────────────────────────────┐  ┌──────────────────────────────────────┐
│     PostgreSQL 16 Database   │  │        Redis Broker & Cache          │
│ 10 Normalized Relational     │  │  - Billing cycle queue (midnight)    │
│ Tables with Indexed Queries  │  │  - 60s reporting cache TTL           │
└──────────────────────────────┘  └──────────────────┬───────────────────┘
                                                     ▼
                                  ┌──────────────────────────────────────┐
                                  │      Celery Worker & Beat Engine     │
                                  │  - Daily billing cycle invoicing     │
                                  │  - Auto-close expired plans & subs   │
                                  │  - Auto-expire promotional discounts │
                                  │  - Overdue payment reminders (9 AM)  │
                                  │  - Renewal warnings (7 days ahead)   │
                                  └──────────────────────────────────────┘
```

---

### 2. Core Service Engines (Business Logic)

1. **`SubscriptionService` (State Machine Engine)**
   - Strict lifecycle transitions:
     $$\text{Draft} \longrightarrow \text{Quotation} \longrightarrow \text{Confirmed} \longrightarrow \text{Active} \longleftrightarrow \text{Paused}$$
     $$\text{Active} \longrightarrow \text{Closed} \longrightarrow \text{Renewed (Active)}$$
   - Prevents invalid operations (e.g., activating a draft subscription directly without confirmation).
   - Validates plan permissions (`can_pause`, `can_close_early`, `can_renew`).

2. **`TaxCalculator` (Tax Determination Engine)**
   - Priority matching: Product-specific rule override $\to$ Global rule fallback $\to$ 0.00% tax.
   - Precision rounding to 2 decimal places using standard financial half-up rounding.

3. **`DiscountEngine` (Promotions & Concessions Engine)**
   - Supports fixed amount deductions and percentage reductions.
   - Evaluates eligibility: active status, validity time window, minimum purchase amount, minimum item quantity, and scope (product vs. whole subscription).
   - Atomic usage counter incrementation with auto-deactivation once `max_uses` is met.

4. **`InvoicingService` (Idempotent Billing Engine)**
   - Generates sequential invoice identifiers: `INV-YYYYMM-XXXXX`.
   - Prevents duplicate invoice issuance for the same subscription in a single period.
   - Automatically computes subtotal, line-item tax amounts, discounts, and grand totals.
   - Automatically advances `next_billing_date` based on the plan's billing interval (Daily, Weekly, Monthly, Yearly).

5. **`PaymentService` (Reconciliation Engine)**
   - Records payments against specific invoices across Cash, Bank Transfer, Credit/Debit Card, and UPI.
   - Computes total cumulative payments; automatically updates invoice status from `confirmed` to `paid` once the grand total is covered.

6. **`ReportService` (Executive Intelligence)**
   - Executes database-level aggregations (`SUM`, `DATE_TRUNC`) instead of application-level loops.
   - Sub-second query times over thousands of records with Redis 60-second caching.

---

### 3. Database Schema Blueprint

| Table Name | Primary Keys & Foreign Keys | Key Attributes & Enums | Purpose |
| :--- | :--- | :--- | :--- |
| **`users`** | `id` (UUID) | `email` (unique), `password_hash`, `role` (`admin`, `staff`, `customer`), `is_active` | Auth & role-based access control |
| **`products`** | `id` (UUID) | `name`, `type`, `sales_price`, `cost_price`, `is_active` | Products catalog |
| **`product_variants`** | `id` (UUID), `product_id` (FK) | `label`, `price_delta` | Add-on options (e.g. Odoo brand +560) |
| **`plans`** | `id` (UUID), `product_id` (FK) | `billing_interval` (`daily`, `weekly`, `monthly`, `yearly`), `price`, `auto_close`, `can_pause` | Pricing and billing frequencies |
| **`quotation_templates`** | `id` (UUID), `plan_id` (FK) | `name`, `validity_days`, `notes` | Standardized quotes for sales teams |
| **`subscriptions`** | `id` (UUID), `customer_id` (FK), `plan_id` (FK) | `subscription_number`, `status`, `start_date`, `expiry_date`, `next_billing_date`, `payment_terms` | Core subscription contracts |
| **`subscription_lines`** | `id` (UUID), `subscription_id` (FK) | `product_id`, `quantity`, `unit_price`, `line_total` | Line item contents of a subscription |
| **`tax_rules`** | `id` (UUID), `product_id` (FK, nullable) | `name`, `rate` (e.g. 0.1800), `applies_to` (`all`, `product`, `plan`) | Configurable taxation rules |
| **`discounts`** | `id` (UUID), `product_id` (FK, nullable) | `type` (`fixed`, `percentage`), `value`, `max_uses`, `used_count`, `scope` | Promotional discount logic |
| **`invoices`** | `id` (UUID), `subscription_id` (FK) | `invoice_number`, `status` (`draft`, `confirmed`, `paid`, `cancelled`), `due_date`, `grand_total` | Generated bills |
| **`invoice_lines`** | `id` (UUID), `invoice_id` (FK) | `description`, `quantity`, `unit_price`, `tax_amount`, `discount`, `line_total` | Line breakdown per invoice |
| **`payments`** | `id` (UUID), `invoice_id` (FK) | `amount`, `method` (`cash`, `bank_transfer`, `card`, `upi`), `payment_date`, `reference` | Payment transactions |

---

### 4. Implementation Deliverables

1. **Backend Layer**:
   - Python 3.12 with FastAPI.
   - Pydantic v2 schemas for request validation, response serialization, and password policy verification.
   - JWT authentication with separate short-lived access tokens and refresh tokens.
   - Automated Celery cron tasks configured for midnight billing and 9 AM reminders.
   - Professional PDF invoice generation via ReportLab.

2. **Frontend Layer**:
   - Single-Page Application (SPA) in React 18, TypeScript, and TailwindCSS.
   - Role-based route protection (`ProtectedRoute`) strictly isolating Admin, Staff, and Customer views.
   - Axios interceptor with automated token refresh handling.
   - Dashboard visualizations using Recharts.

3. **Production Deployment Configuration**:
   - Multi-container `docker-compose.yml` deploying DB, Redis, API, Worker, Beat, and Nginx.
   - Cross-database compatible GUID handling (PostgreSQL native UUID in production, SQLite in unit tests).

