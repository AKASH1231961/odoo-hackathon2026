# Brightloop Subscription Management System (SMS)

One platform for plans, subscriptions, recurring billing, payments and revenue reporting,
built for the scenario in [docs/problem-statement.txt](docs/problem-statement.txt).

## Project layout

```
backend/        API, background jobs, database migrations, tests
ui/             Web app: pages in templates/, scripts in static/js/
docs/           Problem statement and planning documents
requirements.txt          Every Python dependency, for the backend, UI and tests
docker-compose.yml        Runs everything
docker-compose.prod.yml   Production overrides
.env.example              Copy to .env
```

## Architecture
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.x, Alembic, Celery, Redis, ReportLab.
- **UI**: `ui/`, FastAPI serving HTML, CSS and plain JavaScript. Its `/api` route forwards to the backend, so the browser needs no CORS.
- **Billing engine**:
  - `InvoicingService`: one invoice per billing period, enforced by a row lock and a unique index.
  - `TaxCalculator`: product rule, then plan rule, then global rule, on the discounted amount.
  - `DiscountEngine`: product discounts per line, subscription discounts once per invoice, with usage limits, optional customer targeting and uses returned on cancellation.
  - `SubscriptionService`: `draft -> quotation -> confirmed -> active -> paused / closed -> renew`, with plan rules enforced.
  - `PaymentService`: payments up to the balance due; the invoice status follows its payments.
  - `ReportService`: database aggregations. Revenue is money received, by payment date.

## Running with Docker

```bash
cp .env.example .env
docker compose up -d --build
```

| What | Where |
|---|---|
| App | http://localhost:8081 |
| API docs | http://localhost:8000/docs |
| Caught emails (Mailpit) | http://localhost:8025 |
| PostgreSQL from your machine | `localhost:5433` |

The `migrate` service runs first: it applies migrations, loads demo data when
`SEED_DEMO_DATA=true`, and creates an admin from `ADMIN_EMAIL` / `ADMIN_PASSWORD` if none exists.

To bill right away instead of waiting for the midnight run, press **Run billing now** on the Invoices page as admin.

### Sending real email through Gmail

By default Mailpit catches all email. To deliver it for real:

1. Turn on 2-Step Verification on the Google account, then create an app password at https://myaccount.google.com/apppasswords.
2. In `.env`, set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER` and `SMTP_FROM` to the Gmail address, and `SMTP_PASSWORD` to the app password with no spaces.
3. Apply it and send a test:

```bash
docker compose up -d --force-recreate api worker beat
docker compose exec api python scripts/send_test_email.py you@example.com
```

A free Gmail account sends about 500 messages a day, so use a business mail service for real volumes.

### Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Set real values in `.env` first: `ENVIRONMENT=production`, `SECRET_KEY`, `POSTGRES_PASSWORD`,
`SMTP_*`, `FRONTEND_URL`, `ADMIN_*`, and `SEED_DEMO_DATA=false`. The API refuses to start
outside development with a default `SECRET_KEY`.

### Demo accounts
- **Admin**: `admin@brightloop.test` / `Admin@123`
- **Staff**: `staff@brightloop.test` / `Staff@123`
- **Customer**: `alice@acme.test` / `Alice@123`
- **Customer**: `bob@globex.test` / `Bob@12345`

## Local development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
docker compose up -d db redis mailpit

cd backend
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/subscription_db
export REDIS_URL=redis://localhost:6379/0
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd ui
uvicorn main:app --reload --port 8002
```

## Changing a screen

Each page is a file in `ui/templates/` with its script in `ui/static/js/pages/`. Every API call goes
through `BL` in `ui/static/js/api.js`. The API itself is documented at http://localhost:8000/docs.
In Docker, HTML, CSS and JavaScript changes appear when you refresh the page.

## Database changes

Change the models, then:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Alembic does not detect CHECK constraints or server defaults, so add those to the migration by hand.

## Tests

```bash
cd backend
pytest                                           # SQLite, quick
TEST_DATABASE_URL=postgresql://... pytest        # a throwaway Postgres database; use before merging
```

SQLite hides some problems Postgres shows, such as timezone-aware dates and foreign keys.

## Scheduled jobs (UTC)

| Time | Job |
|---|---|
| 00:00 | Bill everything due, confirm and email invoices |
| 00:05 | Close plans past their end date with `auto_close` |
| 00:10 | Close subscriptions that have ended on `auto_close` plans |
| 00:15 | Deactivate expired discounts |
| 09:00 | Overdue invoice reminders |
| 09:05 | Renewal reminders, 7 days before expiry |

