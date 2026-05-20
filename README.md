# Retail Management System (FIMS)

Implementation-accurate documentation for the current codebase on the `main` branch.

## What This System Does

This is a role-based fertilizer logistics and inventory system built with Flask. It manages the complete operational chain:

1. Admin creates and manages rakes, masters, summaries, and logistics billing.
2. Rake Point creates loading slips and builties for dispatch from rake source.
3. Warehouse handles stock-in/stock-out, dispatch documentation, and balance tracking.
4. Accountant generates e-bills and manages bill/eway bill files.

The same codebase supports two runtime modes:

1. Local mode: SQLite (`fims.db`).
2. Cloud mode: Turso/LibSQL when `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are set.

## Current Architecture

### Application Layer

1. `app.py`
2. Flask app, all routes, login/session handling, role checks, API endpoints, print/download endpoints.

### Data Layer

1. `database.py`
2. `Database` class for schema init, CRUD, analytics queries, stock movement logic, billing persistence.
3. Optional Turso connection reuse with stale-connection reset.
4. In-memory TTL cache (`SimpleCache`, 300s) for frequently reused query results.

### Deployment Entrypoints

1. `api/index.py`: Vercel serverless entrypoint importing app from `app.py`.
2. `vercel.json`: routes all dynamic traffic to `api/index.py`.
3. `Procfile`: Gunicorn process (`web: gunicorn app:app --worker-class gevent --timeout 120 --workers 1`).

### Presentation Layer

1. Jinja templates under `templates/`.
2. Role-specific template folders: `templates/admin/`, `templates/rakepoint/`, `templates/warehouse/`, `templates/accountant/`.

### File Storage

1. `uploads/bills/`: bill PDFs.
2. `uploads/eway_bills/`: e-way bill PDFs.

## Technology Stack

1. Python 3
2. Flask 3.0.0
3. Flask-Login 0.6.3
4. Werkzeug 3.0.1 (password hashing/checking)
5. openpyxl 3.1.2 (Excel exports)
6. reportlab 4.0.7
7. libsql-experimental 0.0.47 (Turso)

## Authentication and Roles

Authentication is session-based using Flask-Login and password hashes.

Default users created during local DB initialization:

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| RakePoint | rakepoint | rake123 |
| Warehouse | warehouse | warehouse123 |
| Accountant | accountant | account123 |

Root route (`/`) redirects authenticated users to role-specific dashboards.

## Major Features Implemented

### Admin

1. Dashboard stats (optimized queries).
2. Add rake with multi-product support.
3. Close/reopen rake with shortage tracking.
4. Summary views (rake/account/cgmf/warehouse).
5. Excel export endpoints for summaries and details.
6. Manage accounts, products, companies, employees, CGMF, warehouses.
7. View/edit/delete all loading slips and builties.
8. Warehouse transactions and warehouse summary analytics.
9. Logistic bill module (rake/warehouse level) with exports.
10. Save/get rake bill payments.
11. Download database backup (`fims.db`) from admin route.

### Rake Point

1. Dashboard with operational stats.
2. Create builty.
3. Create loading slip.
4. List loading slips and builties.
5. Print loading slip and builty.
6. View and download bills/e-way bills.

### Warehouse

1. Dashboard with warehouse-focused metrics.
2. Stock in (warehouse stock ledger entries).
3. Stock out with dispatch/builty generation.
4. Create loading slip and create builty.
5. Balance pages (all warehouses and per warehouse).
6. DO creation flow.
7. Print/loading-slip and print-builty endpoints.
8. View and download bills/e-way bills.

### Accountant

1. Dashboard.
2. Create e-bill from builty data.
3. List all e-bills.
4. Download bill and e-way bill files.

### Shared APIs

1. Rake balance/product data.
2. Next serial/LR/warehouse sequence APIs.
3. Builty detail lookup.
4. Dispatch summaries by account/CGMF.
5. Warehouse account stock endpoint.

## End-to-End Business Flow (Current)

1. Admin creates rake (`/admin/add-rake`) including company, product data, RR quantity.
2. RakePoint creates loading slips and/or builties tied to rake and destination.
3. Warehouse records stock-in from movement documents and stock-out for onward dispatch.
4. System maintains running balances via `warehouse_stock` and rake-based dispatch totals.
5. Accountant generates e-bills for builties and attaches bill/eway bill files.
6. Admin reviews summaries/logistic billing and can close rake with shortage computation.

## Route Surface (High-Level)

The route map in `app.py` currently includes:

1. Authentication routes (`/`, `/login`, `/logout`).
2. Admin module routes under `/admin/*` including dashboards, summaries, masters, logistics billing, exports.
3. RakePoint module routes under `/rakepoint/*`.
4. Warehouse module routes under `/warehouse/*`.
5. Accountant module routes under `/accountant/*`.
6. Utility API routes under `/api/*`.

## Database Schema (Current)

Tables currently created/maintained by `database.py`:

1. `users`
2. `rakes`
3. `rake_products`
4. `accounts`
5. `products`
6. `companies`
7. `employees`
8. `cgmf`
9. `warehouses`
10. `trucks`
11. `builty`
12. `loading_slips`
13. `warehouse_stock`
14. `ebills`
15. `rake_bill_payments`

### Core Data Relationships

1. `loading_slips` links to destination entities (`accounts`/`warehouses`/`cgmf`) and optional `builty`.
2. `builty` links to rake, truck, and destination entity.
3. `warehouse_stock` records stock transactions with references to warehouse, product, account/cgmf, builty/truck.
4. `ebills` link directly to `builty`.
5. `rake_bill_payments` aggregate payment tracking by `rake_code`.

## Project Structure (Current)

```text
Retail-Management-system/
|-- app.py
|-- database.py
|-- reports.py
|-- api/
|   `-- index.py
|-- templates/
|   |-- base.html
|   |-- login.html
|   |-- admin/
|   |   |-- dashboard.html
|   |   |-- add_rake.html
|   |   |-- summary.html
|   |   |-- manage_accounts.html
|   |   |-- all_loading_slips.html
|   |   |-- all_builties.html
|   |   |-- all_ebills.html
|   |   |-- logistic_bill.html
|   |   |-- warehouse_transactions.html
|   |   |-- warehouse_summary.html
|   |   |-- manage_warehouses.html
|   |   |-- edit_warehouse_stock.html
|   |   `-- rake_details.html
|   |-- rakepoint/
|   |   |-- dashboard.html
|   |   |-- create_builty.html
|   |   |-- create_loading_slip.html
|   |   |-- loading_slips.html
|   |   |-- all_builties.html
|   |   `-- view_ebills.html
|   |-- warehouse/
|   |   |-- dashboard.html
|   |   |-- stock_in.html
|   |   |-- stock_out.html
|   |   |-- create_builty.html
|   |   |-- create_loading_slip.html
|   |   |-- loading_slips.html
|   |   |-- balance.html
|   |   |-- do_creation.html
|   |   |-- all_builties.html
|   |   `-- view_ebills.html
|   `-- accountant/
|       |-- dashboard.html
|       |-- create_ebill.html
|       `-- all_ebills.html
|-- uploads/
|   |-- bills/
|   `-- eway_bills/
|-- requirements.txt
|-- Procfile
|-- vercel.json
|-- test_pipeline.py
`-- test_system.py
```

## Setup and Run

### Local Development (SQLite)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run app:

```bash
python app.py
```

3. Open:

```text
http://localhost:5001
```

### Cloud DB Mode (Turso)

Set environment variables before start:

```bash
export TURSO_DATABASE_URL="libsql://..."
export TURSO_AUTH_TOKEN="..."
export SECRET_KEY="replace-in-production"
python app.py
```

Notes:

1. In cloud mode, schema initialization is skipped by design (assumes schema already provisioned).
2. A reusable cloud connection is kept with a 300s staleness reset.

## Deployment

### Vercel

1. Entrypoint: `api/index.py`
2. Build target: `@vercel/python`
3. All dynamic routes forwarded to serverless function.

### Gunicorn/Process Hosts

Use `Procfile` command:

```bash
gunicorn app:app --worker-class gevent --timeout 120 --workers 1
```

## Testing

Current test files in repo:

1. `test_pipeline.py` (comprehensive auth/database/route/performance/security tests)
2. `test_system.py`

Run tests:

```bash
python -m pytest test_pipeline.py -v
python -m pytest test_system.py -v
```

## Operational Notes

1. App currently runs on port `5001` in local `__main__` block.
2. Upload/download routes sanitize filenames with `os.path.basename`.
3. Passwords are stored as hashes, not plaintext.
4. There is role-based authorization per route, with redirect on unauthorized access.

## Repository Sync Status

Verified against remote:

1. Remote: `https://github.com/srijanmishra08/Retail-Management-system.git`
2. Branch: `main`
3. Pull status: already up to date at the time of this documentation update.
