# Brightloop Subscription Management System (SMS)

A complete, production-grade subscription billing platform built directly from scratch according to the specification outlined in `SMS_Implementation_Plan.docx` and Brightloop business requirements.

## Architecture Highlights
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.x, Alembic, Celery, Redis, ReportLab PDF generator.
- **Frontend**: React 18, TypeScript, TailwindCSS, Zustand (JWT state), Recharts, React Router v6.
- **Billing Engine**:
  - `InvoicingService`: Idempotent generation preventing double billing in the same cycle.
  - `TaxCalculator`: Product-specific rule precedence with fallback to global tax rules.
  - `DiscountEngine`: Evaluation of fixed/percentage discounts with usage cap tracking and auto-expiry.
  - `SubscriptionService`: Strict state machine (`draft -> quotation -> confirmed -> active -> paused / closed -> renew`).
  - `PaymentService`: Multi-method recording with automated invoice status reconciliation.
  - `ReportService`: Database-level aggregations (`DATE_TRUNC`, `SUM`) with Redis 60s caching.

## Directory Structure
```
subscription-mgmt/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── seed.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tasks/
│   │   └── utils/
│   └── tests/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── api/
        ├── components/
        ├── pages/
        │   ├── admin/
        │   ├── staff/
        │   └── portal/
        └── store/
```

## Running the Application

### 1. With Docker Compose
```bash
cd subscription-mgmt
cp .env.example .env
docker compose up --build
```
- Frontend UI: `http://localhost` (or `http://localhost:5173` if running dev server)
- Backend API Docs: `http://localhost:8000/docs`

### 2. Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Demo Accounts
- **Admin**: `admin@brightloop.test` / `Admin@123`
- **Staff**: `staff@brightloop.test` / `Staff@123`
- **Customer**: `alice@acme.test` / `Alice@123`
- **Customer**: `bob@globex.test` / `Bob@1234`

