
<h1 align="center">Inventory SaaS</h1>

<p align="center">
  A mobile-first inventory and sales management platform for small retail businesses and online shops.
</p>

<p align="center">
  <strong>🚧 Currently building the MVP</strong>
</p>

---

## Overview

Inventory SaaS is a multi-tenant platform designed to help small businesses manage their inventory, sales, customers, and product demand from one place.

The project focuses on replacing fragmented workflows such as paper notes, spreadsheets, messaging apps, and memory-based stock management with structured and actionable data.

> Turn business knowledge into structured and actionable data.

---

## The Problem

Many small retail businesses still rely on manual or disconnected methods to manage their daily operations.

As the business grows, this can lead to:

* Incorrect stock information
* Lost sales
* Dependency on the owner's memory
* Difficult onboarding of new employees
* Limited visibility into sales performance
* No record of products customers wanted but could not buy
* Poor understanding of actual customer demand

---

## The Solution

Inventory SaaS centralizes the most important operational data into a single platform.

The MVP is being built around four core areas:

| Module       | Purpose                                              | Status         |
| ------------ | ---------------------------------------------------- | -------------- |
| 📦 Inventory | Products, variants, stock and inventory movements    | 🟣 In Progress |
| 🛒 Sales     | Sales registration, customers and payment data       | 🟣 In Progress |
| 📋 Requests  | Track products customers requested but could not buy | 🟣 In Progress |
| 📊 Dashboard | Sales, revenue, stock and demand insights            | 🟣 In Progress |

---

## Core Features

### 📦 Inventory Management

Manage products and keep track of stock changes.

* Product management
* Product categories
* Product variants such as sizes
* Real-time stock visibility
* Inventory adjustments
* Inventory movement history
* Low-stock visibility

### 🛒 Sales Tracking

Record sales while keeping inventory and customer information connected.

* Sales registration
* Sale items
* Customer tracking
* Payment methods
* Sales channels
* Automatic stock updates after sales

### 📋 Demand Tracking

One of the main ideas behind the project is tracking **lost demand**.

When a customer asks for a product that is unavailable, the request can be recorded instead of being forgotten.

This makes it possible to understand:

* Frequently requested unavailable products
* Missed sales opportunities
* Demand for specific products or variants
* Potential restocking priorities

### 📊 Dashboard

The dashboard is intended to turn operational data into simple business insights.

Planned metrics include:

* Daily sales
* Revenue
* Low-stock products
* Most requested products
* Recent inventory activity
* Sales trends

---

## Architecture

The platform follows a **multi-tenant SaaS architecture**.

Each account owns a single store, and all business data belongs to that store.

```text
Store
 ├── Users
 ├── Categories
 ├── Products
 │    └── Product Variants
 ├── Customers
 ├── Sales
 │    └── Sale Items
 ├── Inventory Movements
 └── Requests
```

The goal is to keep tenant data isolated while maintaining a simple structure suitable for small businesses.

---

## Domain Model

Core entities currently include:

```text
Store
User
Category
Product
ProductVariant
Customer
Sale
SaleItem
InventoryMovement
Request
```

Some of the main relationships:

```text
Store
 ├── has many Products
 ├── has many Customers
 ├── has many Sales
 └── has many Requests

Product
 └── has many ProductVariants

Sale
 └── has many SaleItems

ProductVariant
 └── has many InventoryMovements
```

---

## Tech Stack

### Backend

* Python
* Django
* Django REST Framework
* PostgreSQL

### Frontend

The mobile-first React frontend is maintained separately at
[`mohrezvelayati/inventory-saas-frontend`](https://github.com/mohrezvelayati/inventory-saas-frontend).
It currently covers authentication, store onboarding, dashboard, catalog,
inventory, customers, sales checkout, wanted products, and member management.

### Architecture

* REST API
* Multi-tenant data model
* Relational database
* Mobile-first product direction

---

## Example Workflow

A typical sale flow is intended to look like this:

```text
Customer selects product
        ↓
Seller selects product variant
        ↓
Sale is registered
        ↓
Stock is updated
        ↓
Inventory movement is recorded
        ↓
Dashboard data is updated
```

If the requested product is unavailable:

```text
Customer requests product
        ↓
Product is unavailable
        ↓
Seller records the request
        ↓
Demand data is stored
        ↓
Business can use it for future restocking decisions
```

---

## Target Audience

The platform is being designed primarily for:

* Sneaker stores
* Small fashion retailers
* Online shops
* Instagram-based sellers
* Small retail businesses
* Businesses with approximately 1–10 employees

---

## Project Status

> 🚧 This project is actively under development.

The current focus is building the MVP and validating the core domain model and workflows.

```text
Inventory     → Active development
Sales         → Building
Requests      → Planned / partially implemented
Dashboard     → In progress
```

Features, APIs, database models, and architecture may change while the MVP evolves.

---

Implemented:

- JWT authentication and user registration
- One-store-per-user tenant model
- Manager-controlled capability permissions
- Category, product, and size-variant management
- Inventory balances, stock movements, and movement history
- Customer management
- Draft sales, line items, checkout, and cancellation
- Wanted-product demand tracking
- Store dashboard metrics
- Pagination, filtering, OpenAPI, and Swagger
- A PostgreSQL-backed automated test suite

Not production-ready yet:

- Secrets and database configuration are still stored in development settings.
- Environment-specific settings have not been split.
- Password reset/change, JWT logout/blacklisting, and rate limiting are missing.
- CI, production logging, monitoring, backups, and deployment are missing.
- The frontend still needs production hardening, complete CRUD detail views,
  automated UI tests, and deployment configuration.

Do not deploy the current settings with real customer data.

## Product Goal

Small stores often manage inventory through memory, paper, spreadsheets, or
messaging apps. This creates incorrect stock counts, missed sales, difficult
employee onboarding, and little visibility into customer demand.

The MVP supports this workflow:

1. A Manager creates an account and a Store.
2. The Manager creates categories, products, and size variants.
3. Stock enters through purchase or adjustment movements.
4. Employees create draft sales and add variants.
5. Checkout validates and deducts stock atomically.
6. Customer requests for unavailable products are recorded as Wanted data.
7. Dashboard metrics summarize sales, stock, and demand.

## Technology Stack

- Python 3.9 in the current development environment
- Django 4.2
- Django REST Framework
- PostgreSQL
- SimpleJWT
- drf-spectacular / OpenAPI / Swagger UI

Dependencies are pinned in [`requirements.txt`](requirements.txt).

## Application Structure

```text
config/       Django settings and root URLs
users/        Custom User model, registration, and current-user API
stores/       Store, membership, roles, capabilities, and employee management
catalog/      Categories, products, variants, search, and stock filters
inventory/    Stock movements, cached balances, and movement history
sales/        Draft sales, sale items, checkout, and cancellation
customers/    Tenant-scoped customer CRUD
wanted/       Unavailable-product demand aggregation and request history
dashboard/    Sales, inventory, top-product, and wanted metrics
tests/        Shared factories and backend integration/concurrency tests
```

The usual write path is:

```text
API View -> Serializer validation -> Service -> Model / PostgreSQL
```

Views handle HTTP and tenant-scoped object lookup. Serializers validate API
input. Services contain business rules, transactions, and row locking.

## Domain Model

```text
User --1:1 for MVP--> StoreMembership --> Store
                                      |--> Category
                                      |--> Product --> ProductVariant
                                      |--> Customer
                                      |--> Sale --> SaleItem
                                      |--> WantedProduct --> WantedCustomerRequest

ProductVariant --> InventoryMovement
StoreMembership --> MembershipPermission --> Permission
```

Important constraints:

- A User can have only one StoreMembership in the MVP.
- Category names are unique per Store.
- Customer phone numbers are unique per Store.
- Variant sizes are unique per Product.
- WantedProduct is unique by `(store, product_name, size)`.
- Membership permissions are unique by `(membership, permission)`.

## Tenant Isolation

Every business object belongs to a Store, directly or through a parent object.
The central resolver is:

```python
get_current_membership(user)
```

It deliberately uses `.get()`, not `.first()`. Selecting an arbitrary Store is
not allowed. The database also enforces one membership per User.

Tenant isolation is applied at two levels:

1. Views and serializer relation querysets only expose objects from the current
   Store.
2. Mutating services repeat ownership checks as defense in depth.

Inaccessible tenant objects normally return `404` so the API does not reveal
that another Store's object exists.

When adding an endpoint that accepts an object ID, add a cross-store denial
test.

## Roles and Capabilities

Roles:

```text
manager
seller
admin
```

A Manager has implicit full access. Seller and Admin access is controlled by
MembershipPermission rows.

Supported capability codes:

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

Membership, role, and capability management is restricted to Managers.
Services prevent self-promotion, self-removal, and removal or demotion of the
last Manager.

## Inventory Rules

`ProductVariant.current_stock` is the cached current balance.
`InventoryMovement` is the audit trail. All stock changes must go through
`create_inventory_movement()`.

Movement rules:

| Type | Quantity | Created by |
| --- | --- | --- |
| `purchase` | positive | Inventory API |
| `adjustment` | positive or negative, never zero | Inventory API or cancellation |
| `sale` | negative | Sale checkout only |

The generic Inventory API does not accept manual `sale` movements. A movement
that would make stock negative is rejected.

Stock updates lock the ProductVariant row with `select_for_update()`.

## Sale Lifecycle

### Draft creation

A Sale starts as `draft`. Channel and payment method are required. Customer is
optional but must belong to the same Store.

### Adding items

Only a draft Sale can be modified. The service:

- Locks the Sale row.
- Verifies that the Variant belongs to the Sale's Store.
- Requires a positive quantity.
- Uses the current variant sale price as the line price snapshot.
- Rejects negative discounts.
- Rejects discounts greater than the line subtotal.
- Recalculates `Sale.total_amount`.

Draft SaleItems can be updated or removed. Quantity and discount changes are
validated by the Sales service and always recalculate the Sale total. An
abandoned draft Sale can also be deleted; this does not change stock because
inventory is only deducted during checkout.

### Checkout

Checkout runs in one database transaction:

1. Lock the draft Sale.
2. Reject an empty or non-draft Sale.
3. Aggregate duplicate SaleItem quantities by Variant.
4. Lock affected Variants in deterministic ID order.
5. Validate stock using the locked rows.
6. Create negative `sale` movements.
7. Mark the Sale as `completed`.

This prevents double completion and overselling during concurrent requests.

### Cancellation

The current product behavior allows cancellation of a completed Sale. It
creates positive `adjustment` movements to restore stock and changes the Sale
status to `cancelled`. A second cancellation is rejected.

Do not change this behavior without an explicit product decision; older design
documents may describe draft cancellation instead.

## Wanted-Product Flow

Wanted captures demand for products that customers requested but could not
buy.

- Product and Customer relations are tenant-scoped.
- `brand` and `created_by` are preserved.
- Repeated requests increment `wanted_count` atomically.
- Every request creates a separate WantedCustomerRequest audit row.
- Concurrent increments are covered by a PostgreSQL test.

## Dashboard

The Dashboard accepts optional ISO dates:

```text
?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
```

Defaults are based on `timezone.localdate()`. Reversed dates and ranges longer
than `DASHBOARD_MAX_DATE_RANGE_DAYS` are rejected.

The response contains:

```text
sales
inventory
low_stock
products
wanted
```

Sales totals and SaleItem discounts are intentionally aggregated separately so
multi-item sales do not duplicate revenue through SQL joins.

## API Overview

All endpoints use the `/api/v1/` prefix.

### Authentication

```text
POST /api/v1/users/register/
GET  /api/v1/users/me/
POST /api/v1/auth/login/
POST /api/v1/auth/token/refresh/
```

Use access tokens as:

```http
Authorization: Bearer <access-token>
```

### Stores and employees

```text
POST   /api/v1/stores/
GET    /api/v1/stores/members/
POST   /api/v1/stores/members/
GET    /api/v1/stores/members/{membership_id}/
PATCH  /api/v1/stores/members/{membership_id}/
DELETE /api/v1/stores/members/{membership_id}/
GET    /api/v1/stores/permissions/
GET    /api/v1/stores/members/{membership_id}/permissions/
POST   /api/v1/stores/members/{membership_id}/permissions/
DELETE /api/v1/stores/members/{membership_id}/permissions/{assignment_id}/
```

### Catalog

```text
GET/POST               /api/v1/catalog/categories/
GET/PUT/PATCH/DELETE   /api/v1/catalog/categories/{category_id}/
GET/POST               /api/v1/catalog/products/
GET/PUT/PATCH/DELETE   /api/v1/catalog/products/{product_id}/
GET                    /api/v1/catalog/variants/
POST                   /api/v1/catalog/product/{product_id}/variants/
GET/PUT/PATCH/DELETE   /api/v1/catalog/variants/{variant_id}/
```

Product filters:

```text
?search=name
?category_id=1
?stock_status=in_stock|low_stock|out_of_stock
```

### Inventory

```text
GET  /api/v1/inventory/
POST /api/v1/inventory/movements/create/
GET  /api/v1/inventory/movements/history/
```

History filters:

```text
?product_id=1
?variant_id=1
?created_by_id=1
?type=purchase|sale|adjustment
?date_from=YYYY-MM-DD
?date_to=YYYY-MM-DD
```

### Sales

```text
GET  /api/v1/sales/
POST /api/v1/sales/create/
GET/DELETE /api/v1/sales/{sale_id}/
POST /api/v1/sales/{sale_id}/items/
PATCH/DELETE /api/v1/sales/{sale_id}/items/{item_id}/
POST /api/v1/sales/{sale_id}/complete/
POST /api/v1/sales/{sale_id}/cancel/
```

Sale filters:

```text
?status=draft|completed|cancelled
?channel=store|instagram|website|referral|other
?date_from=YYYY-MM-DD
?date_to=YYYY-MM-DD
```

### Customers, Wanted, and Dashboard

```text
GET/POST               /api/v1/customers/
GET/PUT/PATCH/DELETE   /api/v1/customers/{customer_id}/
GET/POST               /api/v1/wanted/
GET/PUT/PATCH/DELETE   /api/v1/wanted/{wanted_id}/
GET                    /api/v1/dashboard/
```

List endpoints use page-number pagination with a default page size of 20:

```json
{
  "count": 42,
  "next": "...",
  "previous": null,
  "results": []
}
```

## Local Setup

Prerequisites:

- Python 3.9+
- PostgreSQL
- A PostgreSQL user that can create the development and test databases

Create the virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a PostgreSQL database named `inventory_saas`, then configure the local
database credentials in `config/settings.py`. Environment-variable support is
planned but not implemented yet.

Apply migrations:

```bash
python manage.py migrate
```

Run the server:

```bash
python manage.py runserver
```

Useful URLs:

```text
Swagger: http://127.0.0.1:8000/api/v1/docs/
Schema:  http://127.0.0.1:8000/api/v1/schema/
Admin:   http://127.0.0.1:8000/admin/
```

## Verification and Tests

Run Django checks:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

Validate OpenAPI:

```bash
python manage.py spectacular --file /tmp/inventory-openapi.yaml --validate
```

Run the complete test suite:

```bash
python manage.py test
```

The current suite contains 69 tests and uses PostgreSQL. It covers:

- Authentication and JWT login
- Membership uniqueness and role restrictions
- Capability permissions
- Tenant isolation
- Catalog filters and read-only stock
- Customer and Wanted workflows
- Inventory invariants and history filters
- Sale checkout, rollback, cancellation, and duplicate variants
- Concurrent checkout for the final stock unit
- Concurrent Wanted increments
- Dashboard correctness and date validation
- Core OpenAPI paths

The Django test runner creates a temporary `test_inventory_saas` database. The
configured PostgreSQL user needs permission to create and destroy it.

## Development Rules

When changing the project:

1. Keep every business queryset tenant-scoped.
2. Never use `.memberships.first()` to select a Store.
3. Never update `current_stock` outside the Inventory service.
4. Do not expose manual `sale` inventory movements.
5. Keep cross-store relation querysets empty or Store-scoped.
6. Put transactional business rules in services, not serializers or views.
7. Use DRF ValidationError for expected API validation failures.
8. Add a regression test for every bug fix.
9. Run checks, OpenAPI validation, and the complete PostgreSQL suite before
   committing.
10. Stage explicit files; avoid `git add .` when local artifacts exist.

## Documentation and Planning

- [`TECHNICAL_HANDOVER_AND_REFACTOR_PLAN.md`](TECHNICAL_HANDOVER_AND_REFACTOR_PLAN.md): original technical audit

Treat the current code and passing tests as the behavioral source of truth.
Planning documents may contain older decisions, especially around Sale
cancellation and tasks that were marked complete before regression tests were
added.

## Remaining Roadmap

The recommended next phases are:

1. Finish backend regression and coverage review.
2. Move secrets and database configuration to environment variables.
3. Split development, test, and production settings.
4. Add password validation, logout/blacklisting, reset flows, and throttling.
5. Add formatting, linting, and PostgreSQL CI.
6. Add production logging, security settings, health checks, and indexes based
   on measured query plans.
7. Finish frontend detail views, UI tests, and production authentication.
8. Deploy staging with monitoring, backups, restore, and rollback procedures.

## AI / Developer Handoff

Before editing code, an AI or new developer should read:

1. This README
2. The relevant models, serializers, views, services, and tests

Then run:

```bash
git status --short
python manage.py check
python manage.py test
```

Do not assume that a green task marker proves the implementation is correct.
Confirm the behavior through the source code and tests. Preserve unrelated
worktree changes and keep each commit focused on one logical change.

## License

MIT
