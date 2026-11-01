# NWR Business Intelligence Portal - Phase 1 Framework

**Leonora Nashipeta · University of Namibia**
NWR Hackathon · Presentation 16 July 2026, 10:15–10:30

This is the working Phase 1 codebase behind the hackathon presentation. It
implements every deliverable from the hackathon brief and the
accompanying study guide: a secure login system with RBAC, Flask routes
that sync data from CiMSO Innkeeper, a PostgreSQL-ready schema (staging →
fact → dimension), a live KPI dashboard with Chart.js, and a CSV/Excel
upload pipeline with pandas validation and an audit log.

## Quick Start (2 minutes)

```bash
cd nwr_bi_portal
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env          # then edit SECRET_KEY if you like
python3 seed_data.py          # creates the DB, roles, demo users, and 30 days of mock CiMSO data
python3 run.py                # starts the server on http://localhost:5000
```

These are demo accounts with mock data only.
Log in with any of:

| Username        | Password    | Role    | Scope                |
|-----------------|-------------|---------|----------------------|
| admin@nwr       | admin123    | Admin   | All resorts           |
| manager@nwr     | manager123  | Manager | Etosha Safari Lodge only |
| exco@nwr        | exco123     | EXCO    | All resorts, summary only |

## What's actually implemented (Phase 1 checklist)

- [x] Secure login system with role-based access (Admin / Manager / EXCO)
- [x] Flask routes that connect to and pull data from CiMSO Innkeeper
      (mock generator today — see "About the CiMSO mock" below)
- [x] PostgreSQL-ready database schema — staging tables, fact tables,
      dimension tables (works today on SQLite; one env var switches it to
      real Postgres, see below)
- [x] Dashboard home screen with live KPI cards and a Chart.js revenue chart
- [x] CSV/Excel upload pipeline with pandas validation and an audit log
- [x] Production-ready project structure (app factory, blueprints, config
      via environment variables, `.gitignore`, requirements.txt)

This is an honest Phase 1 framework, not a finished product — see Slide 6
of the presentation guide for how to talk about that with the panel.

## Project structure

```
nwr_bi_portal/
├── app/
│   ├── __init__.py          # application factory
│   ├── extensions.py        # db, login_manager, scheduler singletons
│   ├── models/               # user.py, dimension.py, staging.py, fact.py
│   ├── auth/                 # login/logout + role_required decorator
│   ├── dashboard/             # KPI home + Finance/Reservations/Ops + CSV export
│   ├── api/                   # mock CiMSO client + APScheduler sync job
│   ├── upload/                 # CSV/Excel upload + shared ETL validators
│   ├── templates/              # Jinja2 templates (NWR-branded)
│   └── static/css, static/js
├── config.py                  # all settings, read from environment variables
├── run.py                      # entry point
├── seed_data.py                 # one-time DB bootstrap + demo data
├── requirements.txt
├── .env.example
└── .gitignore
```

## How the 5-layer data flow maps to the code

This is exactly the diagram from Slide 3 / Figure 2 of the study guide —
useful if you're building the draw.io version too:

| Layer | Study guide label | Code |
|---|---|---|
| 1 | Data Sources: CiMSO Innkeeper (API) + Manual CSV/Excel | `app/api/cimso_client.py`, file upload form in `upload.html` |
| 2 | API/ETL Layer: Flask REST API + APScheduler | `app/api/routes.py`, `app/api/scheduler.py` |
| 3 | Database: PostgreSQL, Staging → Fact → Dimension | `app/models/staging.py`, `fact.py`, `dimension.py` |
| 4 | Backend Logic: Flask + RBAC | `app/dashboard/routes.py` (`_resort_filter`), `app/auth/decorators.py` |
| 5 | Frontend/UI: HTML5 + CSS3 + Chart.js | `app/templates/*.html`, `app/static/css/style.css` |

## About the CiMSO mock

NWR hasn't issued live CiMSO credentials for the hackathon, so
`CIMSO_USE_MOCK=true` (the default) makes `app/api/cimso_client.py`
generate realistic booking records locally — including a small
percentage of deliberately messy rows (blank revenue, blank dates) so the
staging/validation pipeline has real failures to catch, just like it would
with real-world CiMSO exports.

**For Phase 2**, implement `_fetch_from_real_api()` in that same file to
call the real CiMSO REST endpoint with the API key from your `.env`, keep
the same return shape, and flip `CIMSO_USE_MOCK=false`. Nothing else in
the pipeline (staging, validation, fact tables, dashboard) needs to change
— that's the point of the adapter pattern here.

## Switching to PostgreSQL for Phase 2

The entire app is written against SQLAlchemy, so switching databases is a
one-line config change, not a code change:

```bash
# 1. Install Postgres and the driver
pip install psycopg2-binary

# 2. Create a database and user
sudo -u postgres createuser nwr_user --pwprompt
sudo -u postgres createdb nwr_bi -O nwr_user

# 3. Point the app at it in .env
DATABASE_URL=postgresql://nwr_user:your_password@localhost:5432/nwr_bi

# 4. Re-run the seed script against the new database
python3 seed_data.py
```

## Security layers implemented (Slide 5)

- **L1 Authentication** - Flask-Login sessions, Werkzeug password hashing
  (pbkdf2:sha256 — a salted one-way hash, same category of protection as
  bcrypt), every login attempt (success or failure) logged with IP address
  in `login_attempts`.
- **L2 Authorisation/RBAC** - `@role_required(...)` decorator on every
  sensitive route, and - the important part — `_resort_filter()` in
  `app/dashboard/routes.py` filters the SQL query itself, so a Manager's
  query never fetches another resort's rows from the database at all.
- **L3 Data in transit** — the app reads `SECRET_KEY`, database
  credentials, and the CiMSO API key from environment variables, never
  hard-coded, and `.env` is git-ignored. Deploy behind HTTPS/TLS in
  production and set `FORCE_SECURE_COOKIES=true`.
- **L4 Data at rest** - in a real deployment, PostgreSQL should be bound
  to localhost/private network only (not exposed publicly), with
  automated backups - this is an infrastructure/deployment step, not
  something the application code can enforce by itself.

## Known Phase 1 limitations (be upfront about these if asked)

- CiMSO integration is a realistic mock, not a live connection (no
  credentials yet).
- PDF export isn't implemented yet - CSV export is (Slide 5 UX section
  mentions CSV/PDF; CSV is the Phase 1 deliverable here).
- No automated test suite yet - recommended next step for Phase 2 is
  `pytest` coverage of `app/upload/validators.py`, since that's where a
  bug would most silently corrupt real numbers.
- Dev server (`python3 run.py`) is for demo/dev use only; a real
  deployment should run behind `gunicorn` + a reverse proxy.

## Publishing this to GitHub

```bash
cd nwr_bi_portal
git init                       # already done for you in this delivered copy
git add .
git commit -m "Phase 1: NWR BI Portal framework"
git remote add origin https://github.com/<your-username>/nwr-bi-portal.git
git branch -M main
git push -u origin main
```
