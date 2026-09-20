# Inventory SaaS

[![Backend CI](https://github.com/mohrezvelayati/inventory-SaaS/actions/workflows/ci.yml/badge.svg)](https://github.com/mohrezvelayati/inventory-SaaS/actions/workflows/ci.yml)
[![CodeQL](https://github.com/mohrezvelayati/inventory-SaaS/actions/workflows/codeql.yml/badge.svg)](https://github.com/mohrezvelayati/inventory-SaaS/actions/workflows/codeql.yml)

A multi-tenant inventory, sales, customer, and demand-management platform for
small retail businesses and online shops.

The backend is a Django REST API. The mobile-first Persian/RTL React client is
maintained separately in
[`mohrezvelayati/inventory-saas-frontend`](https://github.com/mohrezvelayati/inventory-saas-frontend).

> Current maturity: live portfolio MVP running on Render with demo data only.
> Upgrade PostgreSQL and complete the restore drill before storing real customer
> data.

## Live Demo

- Frontend: <https://inventory-saas-frontend-evln.onrender.com>
- Backend API: <https://inventory-saas-api-k6wp.onrender.com>
- Swagger UI: <https://inventory-saas-api-k6wp.onrender.com/api/v1/docs/>
- Readiness: <https://inventory-saas-api-k6wp.onrender.com/api/v1/health/ready/>

Use **ورود به نسخهٔ نمایشی** on the login page to enter the shared, writable
portfolio store without registering or entering credentials. The synthetic
tenant is rebuilt on backend deploy/startup, and no real customer data belongs
in this environment.

## What the MVP Does

- JWT registration, login, refresh, logout, and current-user context
- Password change, token revocation, and optional SMS OTP password recovery
- One-store-per-user tenant isolation
- Manager, seller, and admin roles with capability permissions
- Secure phone-bound employee invitations
- Store, profile, member, role, and capability management
- Catalog APIs for categories, products, size variants, individual pricing,
  bulk sale-price updates, search, filtering, and ordering
- Cached stock balances backed by an inventory movement audit trail
- Atomic batch purchase entry across existing and new product sizes
- Draft sales, editable line items, atomic checkout, and cancellation
- Tenant-scoped customer management and search/filter by gender and age
- Wanted-product demand aggregation and request auditing
- Dashboard metrics and financial/inventory reports
- Pagination and OpenAPI/Swagger documentation
- PostgreSQL-backed integration, tenant, permission, concurrency, schema, and
  end-to-end smoke tests

The core business workflow is:

```text
Register owner
-> create store
-> create catalog and variants
-> enter stock
-> create customer
-> build draft sale
-> checkout atomically
-> inspect inventory/dashboard/reports
-> record unavailable demand
-> invite employees
```

## Technology

- Python 3.12
- Django 5.2 LTS
- Django REST Framework 3.16.1
- PostgreSQL
- SimpleJWT
- drf-spectacular / OpenAPI / Swagger UI
- Docker / Docker Compose
- GitHub Actions and Render, with optional Sentry integration
- Redis-backed dashboard caching
- Celery 5.6 with Redis as the message broker

Dependencies are pinned in [`requirements.txt`](requirements.txt).

## Backend Structure

```text
config/       Settings and root URL configuration
users/        Custom User, registration, profile/current-user context
stores/       Store, memberships, capabilities, invitations
catalog/      Categories, products, variants, pricing and filters
inventory/    Stock mutation, balances and movement history
sales/        Drafts, line items, checkout and cancellation
customers/    Tenant-scoped customer CRUD, search and gender/age filters
wanted/       Unavailable-product demand aggregation
dashboard/    Dashboard metrics and analytical reports
tests/        Cross-app integration, concurrency and smoke tests
```

The preferred write path is:

```text
API View -> Serializer validation -> Service -> Model / PostgreSQL
```

- Views handle HTTP, permissions, and tenant-scoped lookup.
- Serializers validate input and describe response contracts.
- Services own business rules, transactions, locks, and state transitions.
- Models and migrations enforce persistence constraints.

## Non-Negotiable Domain Rules

### Tenant isolation

- One user has at most one `StoreMembership` in the MVP.
- Resolve the store with `get_current_membership(user)`; never use
  `.memberships.first()`.
- Every business queryset and relation input must be scoped to the current
  store.
- Cross-store objects normally return `404` to avoid leaking their existence.

### Inventory

- `ProductVariant.current_stock` is a cached balance.
- `InventoryMovement` is the audit trail.
- All stock changes go through `create_inventory_movement()`.
- Purchase quantities are positive.
- Adjustments are non-zero and may be positive or negative.
- Sale movements are negative and can only be created by checkout.
- Batch purchase entry creates missing sizes when prices are supplied and
  records every size quantity through the normal movement audit trail.
- A batch is atomic: if any item is invalid, no size, stock, or movement from
  that request is persisted.
- The resulting stock may never become negative.

### Sales

- A Sale begins as `draft`; only drafts and their items can be edited/deleted.
- SaleItem price and cost are snapshots taken when the item is added.
- Discounts cannot be negative or exceed the line subtotal.
- Checkout locks the Sale and Variants, aggregates duplicate Variant demand,
  validates stock, creates movements, and completes the Sale atomically.
- Cancelling a completed Sale keeps the record and restores stock with positive
  adjustment movements.

### Membership and invitations

- Managers have implicit full access and exclusively manage members,
  capabilities, invitations, and store settings.
- Employees join through a phone-bound invitation as `seller` or `admin`.
- Invitation tokens are single-use, revocable, valid for seven days, and stored
  only as SHA-256 hashes.
- Automatic SMS/email delivery is outside the MVP; the manager manually shares
  the returned link.

## Roles and Capability Codes

```text
manage_catalog
view_inventory
manage_inventory
create_sale
view_sales
manage_customers
manage_wanted
view_dashboard
manage_members
```

Default assignments:

| Role | Defaults |
| --- | --- |
| `manager` | All capabilities; access is also implicit in backend checks |
| `seller` | Create/view sales, view inventory, view dashboard |
| `admin` | Seller defaults plus manage wanted demand |

Frontend permission gates improve UX; backend permission classes remain the
security boundary.

## API

All business routes are under `/api/v1/`.

Main route groups:

```text
/api/v1/users/
/api/v1/auth/
/api/v1/stores/
/api/v1/catalog/
/api/v1/inventory/
/api/v1/sales/
/api/v1/customers/
/api/v1/wanted/
/api/v1/dashboard/
/api/v1/health/
```

Interactive documentation:

```text
Swagger UI: http://127.0.0.1:8000/api/v1/docs/
OpenAPI:    http://127.0.0.1:8000/api/v1/schema/
Admin:      http://127.0.0.1:8000/admin/
```

Use the generated OpenAPI schema and Swagger UI as the authoritative public API
reference.

## Local Backend Setup

Prerequisites:

- Python 3.12
- PostgreSQL
- A PostgreSQL user allowed to create the test database

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

To create or rebuild the complete shared demo tenant locally:

```bash
DEMO_MODE_ENABLED=true python manage.py seed_demo --reset
```

The command uses the existing catalog, inventory, sales, membership,
invitation, and wanted services so cached stock and audit history remain
consistent. It refuses to run unless demo mode is explicitly enabled.

Alternatively, start PostgreSQL, Redis, Django, and the Celery worker together:

```bash
docker compose up -d --build db redis backend worker
```

Redis database `0` is the Celery broker and database `1` stores dashboard
cache entries. The worker consumes background jobs independently from the web
process. Celery Beat and business notification tasks are not implemented yet.

Confirm the worker is reachable with:

```bash
docker compose exec worker celery -A config inspect ping
```

Configuration is environment-based. Copy `.env.example` to `.env` for local
overrides and never commit real secrets.

## Verification

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
.venv/bin/python manage.py spectacular \
  --file /tmp/inventory-openapi.yaml --validate
```

Verified on 2026-09-20 with Python 3.12 and Django 5.2:

- 140 Django tests passed against PostgreSQL
- No pending model/migration changes
- Django system check passed
- OpenAPI validation reported zero errors

The test suite covers authentication and password recovery, profile/store
settings, invitations, roles/capabilities, tenant isolation, catalog filters
and bulk pricing, customer/Wanted flows, inventory invariants, concurrent batch
purchases and checkout, concurrent demand increments, sales lifecycle,
dashboard/report correctness, schema paths, and the complete
owner-registration-to-employee-invitation smoke workflow.

## Deployment and Operations

- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md): Render deployment
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md): monitoring, backup, restore,
  rollback, secret rotation, and incident response
- [`docs/DEMO_CHECKLIST.md`](docs/DEMO_CHECKLIST.md): repeatable manual portfolio demo

The backend and PostgreSQL are configured by [`render.yaml`](render.yaml).
Production deploys wait for GitHub Actions checks. The Vite frontend is a Render
Static Site deployed from its separate repository and uses `VITE_API_BASE_URL`
to reach this API.

Known non-blocking gaps include no dedicated Wanted customer-request history
endpoint, manual invitation delivery, and inconsistent legacy formatting/error
language.

## Production Guardrail

Free Render PostgreSQL expires after 30 days and has no managed backups. Use it
only for the first deployment exercise. Upgrade the database, enable Sentry and
uptime monitoring, configure the SMS provider, and complete a restore drill
before storing real customer data.

## License

MIT — see [`LICENSE`](LICENSE).
