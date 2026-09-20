# Inventory SaaS — AI Project Handoff

Last verified: 2026-09-20
Backend repository: `mohrezvelayati/inventory-SaaS`
Frontend repository: `mohrezvelayati/inventory-saas-frontend`

## 1. Purpose of this document

This is the primary context document for any AI or developer continuing this
project. Read it before proposing architecture changes or editing either
repository.

The current code and passing tests remain the final source of truth. This file
records the product decisions, architecture, security invariants, implemented
workflows, API contracts, frontend behavior, verification process, and known
technical debt so future work follows the same direction.

If a statement here conflicts with code or a test, inspect the relevant code,
explain the mismatch, and update both the implementation and this document as
part of the same change.

Source-of-truth order:

1. Current models, migrations, services, views, serializers, permissions, and
   passing tests
2. Generated OpenAPI schema
3. This handoff
4. `README.md`
5. `TECHNICAL_HANDOVER_AND_REFACTOR_PLAN.md`, which is a historical audit and
   contains resolved findings and obsolete estimates

### Owner collaboration preferences

The owner is learning through the project and normally communicates in Persian.
Act like a senior mentor, not a code generator:

- Explain the purpose, failure mode, benefit, and trade-off of a change.
- Prefer the simplest complete MVP design and actively avoid overengineering.
- When the owner says they will implement, provide all edits and verification
  steps in one coherent message and do not touch files.
- When the owner explicitly asks the AI to implement, make and verify the
  change directly.
- Announce clean commit boundaries and suggest specific Conventional Commit
  messages.
- Never stage unrelated artifacts or use `git add .`.

## 2. Product and MVP definition

Inventory SaaS is a mobile-first, RTL inventory and sales system for small
retail businesses, especially sneaker, fashion, Instagram, and online stores
with roughly 1–10 employees.

The MVP replaces paper, spreadsheets, messaging apps, and memory-based store
operations with structured data for:

- Products, sizes, prices, and categories
- Current stock and inventory history
- Customers
- Draft sales, checkout, and cancellation
- Unavailable-product demand (`WantedProduct`)
- Dashboard and financial/inventory reports
- Store employees, roles, capabilities, and invitation onboarding

### Product decisions that must not change implicitly

1. One user can belong to only one store in the MVP.
2. Normal registration is the store-owner flow.
3. A normal registrant starts without a membership, then completes onboarding
   by creating a store and becoming its `manager`.
4. Employee onboarding uses a phone-bound invitation link.
5. Invitation registration skips store onboarding and creates a `seller` or
   `admin` membership in the inviting store.
6. Invitations cannot create a `manager`.
7. Invitations are manually copied and shared; automatic SMS/email is outside
   the MVP.
8. An invitation is single-use, revocable, and valid for 7 days.
9. A completed sale deducts stock atomically. Cancelling a completed sale
   restores stock with adjustment movements.
10. Every tenant-owned read and write must be scoped to the current store.

Do not add multi-store switching, automatic invitation delivery, subscription
billing, or production deployment behavior without an explicit product
decision.

## 3. Repository layout and current state

The backend and frontend are intentionally separate repositories.

Typical local paths used during development:

```text
/Users/mohrez/code/inventory-SaaS
/Users/mohrez/code/inventory-saas-frontend
```

### Backend

- Python 3.12
- Django 5.2.17 LTS
- Django REST Framework 3.16.1
- PostgreSQL
- Redis 7.4 for the dashboard response cache
- Celery 5.6.3 with Redis as the message broker
- SimpleJWT
- drf-spectacular / OpenAPI / Swagger
- Current feature branch: `feature/redis-celery-notifications`
- Latest committed backend base before the Celery change: `a3ac572`

### Frontend

- React 19
- TypeScript 6
- Vite 8
- React Router 7
- TanStack Query 5
- React Hook Form + Zod
- Lucide icons
- Vitest + Testing Library
- oxlint
- Latest committed frontend base while writing this file: `0b94aba`
- Invitation UI changes are currently present in the frontend working tree and
  may not yet be committed; always run `git status --short` before editing.
- Frontend suite at last verification: 31 passing tests, clean lint, successful
  production build

Never assume both repositories are clean. Existing modifications belong to the
user unless proven otherwise.

## 4. Architecture

### Backend applications

| App | Responsibility |
| --- | --- |
| `users` | Custom user, normal registration, current-user profile |
| `stores` | Store tenant, membership, roles, capabilities, invitations |
| `catalog` | Categories, products, size variants, prices |
| `inventory` | Stock balance mutation and movement audit trail |
| `customers` | Tenant-scoped customer CRUD |
| `sales` | Draft invoices, items, checkout, cancellation |
| `notifications` | Persistent outbox events and external notification delivery |
| `wanted` | Unavailable-product demand and customer request audit |
| `dashboard` | Dashboard metrics and analytical reports |
| `tests` | Shared factories, integration, tenant, concurrency, schema, and E2E tests |

The preferred backend write path is:

```text
API view -> serializer validation -> service -> model/PostgreSQL
```

- Views own HTTP behavior, permissions, and tenant-scoped object lookup.
- Serializers validate request/response shapes.
- Services own business rules, transactions, row locks, and state transitions.
- Models own persistence constraints.

Keep views thin and do not move transactional business logic into React,
serializers, or model signals.

### Frontend structure

```text
src/App.tsx                 Route definitions and route guards
src/pages/                 Page-level UI and workflows
src/features/<domain>/     API adapters and domain behavior
src/features/auth/         Auth context, gates, user refresh
src/components/            Shared visual components and app shell
src/lib/api.ts              Fetch wrapper, JWT storage/refresh, ApiError
src/lib/pagination.ts       Fetch-all pagination helper
src/lib/navigation.ts       Safe internal redirect validation
src/types/api.ts            Shared API response/input types
src/App.css                 Main application styling
```

TanStack Query owns server-state fetching and invalidation. Page-local form and
modal state uses React state or React Hook Form. API calls must remain in
feature API modules rather than being embedded directly in components.

## 5. Domain model and database invariants

```text
User
  └── StoreMembership ── Store
        └── MembershipPermission ── Permission

Store
  ├── StoreInvitation
  ├── Category
  ├── Product ── ProductVariant ── InventoryMovement
  ├── Customer
  ├── Sale ── SaleItem
  │      └── NotificationEvent
  └── WantedProduct ── WantedCustomerRequest
```

Important constraints:

- `User.username` is globally unique.
- `User.phone_number` is globally unique and currently stored as an 11-character
  string.
- `StoreMembership.user` has a database unique constraint: one membership per
  user.
- Category name is unique within a store.
- Customer phone is unique within a store.
- Variant size is unique within a product.
- Wanted demand is unique by `(store, product_name, size)`.
- Membership capability assignment is unique by `(membership, permission)`.
- Invitation token hashes are globally unique.
- A store can have only one pending invitation for the same phone at a time.
- Invitation role has a database check limiting it to `seller` or `admin`.
- A Sale has at most one NotificationEvent for each event type.
- Store `notification_email` is optional. An empty value disables outbound sale
  email events for that store.

The central tenant resolver is `stores.services.get_current_membership(user)`.
It deliberately uses `.get()`, never `.first()`. No active-store selector exists
in the MVP.

## 6. Authentication, membership, and authorization

### JWT behavior

- Login: `POST /api/v1/auth/login/`
- Refresh: `POST /api/v1/auth/token/refresh/`
- Access lifetime: 15 minutes
- Refresh lifetime: 7 days
- Refresh rotation is enabled
- Refresh-token blacklisting and password-change revocation are enabled
- Frontend stores both tokens in `sessionStorage` under
  `inventory.auth.tokens`
- The portfolio environment exposes guarded `POST /auth/demo/` one-click login
  for the single internally marked demo manager; it is disabled by default.
- `apiRequest()` attaches the bearer token, coalesces simultaneous refreshes,
  retries once after a 401, and dispatches `auth:expired` if refresh fails

Tokens are intentionally session-scoped, not persisted in `localStorage`.

### Normal owner registration

```text
POST /users/register/
  -> User only, no role yet
POST /auth/login/
  -> JWT
/onboarding/store
POST /stores/
  -> Store + manager StoreMembership + manager default capabilities
```

The signup endpoint does not automatically set `manager`. Manager membership
is created only when the user creates a store.

### Roles and capabilities

Roles:

- `manager`: store owner/manager; implicit access to every capability in the
  permission catalog and exclusive member/invitation management authority
- `seller`: employee with sales/inventory/dashboard defaults
- `admin`: broader operational employee, still not allowed to manage members

Capability codes:

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

Default capability assignments:

| Role | Defaults |
| --- | --- |
| manager | all nine capabilities |
| seller | `create_sale`, `view_sales`, `view_inventory`, `view_dashboard` |
| admin | seller defaults plus `manage_wanted` |

`create_store_membership()` assigns defaults. Migration
`stores.0007_store_invitation_and_default_permissions` backfills missing
defaults without deleting custom capabilities. Role changes add missing
defaults but intentionally do not delete custom assignments.

Only a manager may list/edit/delete members, assign/revoke capabilities, create
or revoke invitations, or update store settings. Services prevent changing
one's own role, removing oneself, and removing/demoting the last manager.

Frontend `PermissionGate` improves UX but is not security. Backend permission
classes and tenant-scoped querysets are mandatory.

## 7. Store invitation system

The invitation is a temporary bridge, not a replacement for membership:

```text
StoreInvitation -> registration/login -> StoreMembership
```

### Security design

- Manager enters phone number and `seller`/`admin` role.
- Backend generates `secrets.token_urlsafe(32)`.
- Only SHA-256 of the token is stored.
- Raw token is returned only in the invitation creation response.
- Frontend builds the full link using `window.location.origin`.
- The manager copies and manually shares the link.
- Creating another invitation for the same store/phone revokes the old pending
  invitation.
- Preview exposes store name, role, masked phone, and expiry; it does not expose
  whether an account exists.
- Accept/register locks the invitation with `select_for_update()`.
- Existing-account acceptance locks the user as well, validates exact phone
  match, and rejects existing membership.
- Registration and membership creation are atomic; failure rolls back the new
  user.
- Invitation errors use stable codes: `invalid`, `expired`, `revoked`, `used`,
  `phone_mismatch`, `already_member`, `account_exists`.

### New employee flow

```text
Manager creates invitation
-> employee opens /invite/:token
-> public preview
-> employee enters full name, username, password
-> phone comes from invitation and cannot be edited
-> backend creates User + StoreMembership + default permissions atomically
-> backend returns JWT pair
-> frontend stores tokens, refreshes /users/me/, opens dashboard
```

### Existing employee flow

```text
Employee opens invitation
-> clicks login
-> /login?next=/invite/:token
-> frontend validates next as an internal path
-> login
-> return to invitation page
-> authenticated accept endpoint
-> refresh current user
-> dashboard
```

Do not add account-existence information to preview. Do not store raw tokens.
Do not remove locking or the one-membership check.

## 8. Backend API contract

All routes are prefixed with `/api/v1/`. List endpoints normally use page-number
pagination with page size 20, except pending invitation listing, which returns a
plain array.

### Authentication and profile

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/users/register/` | Normal owner registration; creates User only |
| GET/PATCH | `/users/me/` | Current profile, membership, store, effective capabilities |
| POST | `/auth/login/` | Username/password JWT pair |
| POST | `/auth/demo/` | Public guarded demo JWT pair; portfolio environment only |
| POST | `/auth/token/refresh/` | Rotate/refresh access token |
| POST | `/auth/logout/` | Blacklist a refresh token; idempotent |
| POST | `/auth/password/change/` | Authenticated password change and token revocation |
| POST | `/auth/password-reset/request/` | Public generic OTP request; does not reveal account existence |
| POST | `/auth/password-reset/confirm/` | Public single-use SMS OTP confirmation |
| GET | `/health/live/` | Process liveness; no database query |
| GET | `/health/ready/` | PostgreSQL readiness; returns 503 when unavailable |

### Store, membership, permissions, invitations

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/stores/` | Create store and manager membership |
| GET/PATCH | `/stores/current/` | Manager-only store settings |
| GET/POST | `/stores/members/` | Manager member list; legacy direct existing-user creation remains available |
| GET/PATCH/DELETE | `/stores/members/{membership_id}/` | Manager-only role/detail/removal |
| GET | `/stores/permissions/` | Capability catalog |
| GET/POST | `/stores/members/{membership_id}/permissions/` | Assigned capabilities |
| DELETE | `/stores/members/{membership_id}/permissions/{assignment_id}/` | Revoke capability |
| GET/POST | `/stores/invitations/` | Pending list/create; manager only |
| DELETE | `/stores/invitations/{invitation_id}/` | Soft revoke; manager only |
| GET | `/stores/invitations/preview/{token}/` | Public safe preview |
| POST | `/stores/invitations/{token}/register/` | Public invitation registration, returns JWT |
| POST | `/stores/invitations/{token}/accept/` | Authenticated existing-user acceptance |

Store responses include optional `notification_email`. Only the manager-only
store settings endpoint can update it; an empty string disables sale email
events without affecting checkout.

### Catalog

| Method | Path |
| --- | --- |
| GET/POST | `/catalog/categories/` |
| GET/PUT/PATCH/DELETE | `/catalog/categories/{category_id}/` |
| GET/POST | `/catalog/products/` |
| GET/PUT/PATCH/DELETE | `/catalog/products/{product_id}/` |
| PATCH | `/catalog/products/{product_id}/prices/` |
| GET | `/catalog/variants/` |
| POST | `/catalog/product/{product_id}/variants/` |
| GET/PUT/PATCH/DELETE | `/catalog/variants/{variant_id}/` |

Product list supports `search`, `category_id`,
`stock_status=in_stock|low_stock|out_of_stock`, and
`ordering=created|-created|name|-name`.

Bulk sale-price update requires `manage_catalog`, accepts one non-negative
`sale_price`, and updates every existing variant of the tenant-scoped product
in one database operation. A product without variants returns a field-level
400 error. Purchase prices, historical `SaleItem` price snapshots, and the
existing per-variant update endpoint remain unchanged.

### Inventory

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/inventory/` | Current variant balances |
| POST | `/inventory/movements/create/` | Manual purchase/adjustment only |
| GET | `/inventory/movements/history/` | Audit history |

History supports `product_id`, `variant_id`, `created_by_id`,
`type=purchase|sale|adjustment`, `date_from`, and `date_to`.

### Sales

| Method | Path |
| --- | --- |
| GET | `/sales/` |
| POST | `/sales/create/` |
| GET/DELETE | `/sales/{sale_id}/` |
| POST | `/sales/{sale_id}/items/` |
| PATCH/DELETE | `/sales/{sale_id}/items/{item_id}/` |
| POST | `/sales/{sale_id}/complete/` |
| POST | `/sales/{sale_id}/cancel/` |

Sale list supports `search` by customer/id, `status`, `channel`, `date_from`,
and `date_to`.

Sale responses include `completed_at`. It is `null` for drafts and is set
atomically when checkout succeeds.

Completing a sale also persists a `sale_completed` NotificationEvent in the
same database transaction when the store has configured a notification email.
The recipient and sale summary are captured in the JSON payload. This is an
internal outbox record; no notification API is exposed.

### Customers, wanted demand, dashboard, reports

| Method | Path |
| --- | --- |
| GET/POST | `/customers/` |
| GET/PUT/PATCH/DELETE | `/customers/{customer_id}/` |
| GET/POST | `/wanted/` |
| GET/PUT/PATCH/DELETE | `/wanted/{wanted_id}/` |
| GET | `/dashboard/` |
| GET | `/dashboard/reports/` |

Customer records carry `full_name`, `phone_number` (required), `gender`
(required, `male`|`female`, with `آقا`/`خانم` labels), an optional `age`
(`PositiveIntegerField`, null allowed), and `total_items_purchased` — an
aggregated read-only count of the total item quantity across that customer's
COMPLETED sales (DRAFT/CANCELLED sales are excluded; customers with none get
`0`). The customer list supports `search` by name or phone, an exact `gender`
query filter, and an inclusive `age` range via `age_min`/`age_max` (either
bound is optional). Invalid values (`gender` outside `male`/`female`,
non-integer age bounds, or `age_min` greater than `age_max`) return 400.

Dashboard/report dates use `YYYY-MM-DD`. Report range is limited by
`DASHBOARD_MAX_DATE_RANGE_DAYS` (currently 90).

Only the summary endpoint at `GET /dashboard/` is cached. The analytical
`GET /dashboard/reports/` endpoint is intentionally uncached because it accepts
larger arbitrary ranges and is used less frequently.

OpenAPI and admin endpoints:

```text
/api/v1/schema/
/api/v1/docs/
/admin/
```

## 9. Critical business workflows and invariants

### Tenant isolation

Every business object belongs to a store directly or through a parent. For any
endpoint accepting an object ID:

1. Resolve the current membership.
2. Filter the queryset by the current store.
3. Repeat ownership validation in the mutating service when relations are
   involved.
4. Return 404 for inaccessible cross-tenant objects where practical.
5. Add a cross-store regression test.

Never query a `Sale`, `Product`, `Variant`, `Customer`, `WantedProduct`, member,
or invitation by unscoped ID in a user-facing endpoint.

### Inventory

`ProductVariant.current_stock` is the cached balance.
`InventoryMovement` is the audit trail. All stock mutation must call
`create_inventory_movement()`.

| Movement | Quantity rule | Source |
| --- | --- | --- |
| `purchase` | positive | Manual inventory API |
| `adjustment` | positive or negative, non-zero | Manual API or sale cancellation |
| `sale` | negative | Checkout only |

The service locks the variant, rejects cross-store variants and negative final
stock, updates the balance, and creates the audit row in one transaction.
Never expose manual `sale` movement creation.

### Product, size, and first-stock workflow

`Product` is the reusable catalog identity; `ProductVariant` is a size with its
own purchase/sale prices; stock exists only on a variant. Keep these creation
steps separate:

1. The product form creates only name, description, and categories with
   `POST /catalog/products/`. A successful new product normally returns
   `variants: []`.
2. The inventory form first selects a product. Products with no variants must
   remain selectable.
3. For an existing size, the form creates only an `InventoryMovement` through
   `POST /inventory/movements/create/`.
4. A user with both `manage_inventory` and `manage_catalog` may select "new
   size". The frontend first creates it through
   `POST /catalog/product/{product_id}/variants/`, then records its first stock
   movement through the normal inventory endpoint.
5. Suggested prices come from the selected product's variant with the greatest
   ID and remain editable. A product without variants has blank price fields.
6. If variant creation succeeds but movement creation fails, do not delete the
   zero-stock variant. Select that variant in the form, explain what happened,
   and let retry submit only the movement request.

Creating a zero-stock variant from Product Detail remains supported. Variant
sizes are trimmed and must be non-blank and unique per product; validation or a
constraint race must return HTTP 400 with a field-level `size` error rather
than HTTP 500. No combined/atomic endpoint is planned for the MVP.

Access details: `view_inventory` or `manage_inventory` exposes the inventory
page and its navigation item; only `manage_inventory` exposes mutation UI; new
size creation additionally requires `manage_catalog`. Backend permissions are
still authoritative.

### Sales

- A sale begins as `draft`.
- Customer is optional but must belong to the same store.
- Only draft sales/items are editable or deletable.
- Line price and cost are snapshots from the variant when the item is added.
- Quantity must be positive.
- Discount is non-negative and cannot exceed line subtotal.
- Total is recalculated after item create/update/delete.
- Checkout locks the sale and variants in deterministic ID order, aggregates
  duplicate variant requirements, validates stock, writes negative movements,
  and marks the sale completed atomically.
- Completed sales record `completed_at`; dashboards and financial reports use
  the completion date rather than the draft creation date.
- Successful checkout creates a pending `sale_completed` NotificationEvent in
  the same transaction when `Store.notification_email` is configured. If
  checkout rolls back, stock, Sale state, and the event all roll back together.
- The event ID is enqueued with `transaction.on_commit()`; model instances are
  never passed to Celery. A broker error after commit is logged and does not
  undo the completed sale or its pending outbox row.
- A store without a notification email completes sales normally without
  creating undeliverable pending events.
- Notification event payloads are JSON snapshots of the completed sale.
  `get_or_create()` plus a database uniqueness constraint on
  `(event_type, sale)` prevents duplicate outbox rows.
- The worker locks the event row, skips an event already marked `sent`, records
  every attempt, and persists either `sent`/`sent_at` or `failed`/`last_error`.
  Temporary SMTP/network errors are retried up to three times with bounded
  exponential delays of 10, 20, and 40 seconds.
- Cancellation is allowed only from completed state, restores stock through
  positive adjustments, and marks the sale cancelled.

### Wanted demand

- Optional product and customer must belong to the current store.
- Matching `(store, product_name, size)` requests increment `wanted_count`
  atomically.
- Every request creates a `WantedCustomerRequest` audit row.

### Dashboard/report correctness

- Metrics are scoped to the current store.
- Only completed sales count toward revenue reports.
- Sale totals and item discounts/costs are aggregated separately to avoid SQL
  join duplication.
- Reports include revenue, discounts, historical unit cost, gross profit,
  average order, daily series, channel breakdown, products, and inventory value.
- Dashboard summary cache keys include the store, requested date range, and a
  per-store version, so one tenant or date range cannot receive another's data.
- Cached dashboard summaries expire after 60 seconds by default.
- Inventory changes, variant/product changes, completed or cancelled sales, and
  wanted-demand changes increment the store cache version only after the
  surrounding database transaction commits.
- Redis failures are fail-open: the dashboard is calculated from PostgreSQL and
  business writes still succeed. Redis is an optimization, not a source of
  truth.

## 10. Frontend routes and access rules

| Route | Access |
| --- | --- |
| `/login` | Guest |
| `/register` | Guest; normal owner registration |
| `/invite/:token` | Public preview; registration or authenticated acceptance |
| `/onboarding/store` | Authenticated user without membership |
| `/` | `view_dashboard` |
| `/products`, `/products/:id`, `/categories` | `manage_catalog` |
| `/sales`, `/sales/:id` | `view_sales` or `create_sale` |
| `/sales/new` | `create_sale` |
| `/inventory` | `view_inventory` or `manage_inventory` |
| `/inventory/history` | `view_inventory` |
| `/customers` | `manage_customers` |
| `/requests` | `manage_wanted` |
| `/members` | `manage_members` in UI; backend additionally requires manager role |
| `/reports` | `view_dashboard` |
| `/profile` | Authenticated member |
| `/settings/store` | Manager only |
| `/more` | Authenticated member |

The UI is mobile-first, max-width 520px, RTL, and Persian. Preserve this visual
direction unless the user explicitly asks for a redesign. Shared colors,
cards, buttons, forms, navigation, and responsive behavior live mainly in
`src/App.css` and shared components.

The original UI screenshot references were supplied from the local folder:

```text
/Users/mohrez/Downloads/temporary things/inventory ui/
```

Those images are not source-controlled, so do not assume they exist on another
machine. The implemented React UI is the durable current reference. For
pixel-level redesign work, inspect or request the source images again before
changing the visual language.

### Frontend data and error conventions

- Use `apiRequest<T>()` for all HTTP calls.
- Keep API types in `src/types/api.ts`.
- Throw/display `ApiError`; invitation errors map stable backend codes to
  Persian messages.
- Invalidate relevant TanStack Query keys after mutations.
- Use the shared pagination envelope for paginated endpoints.
- Use `getAllResults()` only when a complete selector list is required.
- After invitation registration, store JWT, call `refreshUser()`, then navigate.
- Accept login `next` only through `getSafeNextPath()` to prevent open redirects.
- Build invite URLs from `window.location.origin`; never hard-code localhost or
  a production hostname.

## 11. Local development

### Backend

Prerequisites: Python 3.12, PostgreSQL, and permission to create test databases.
Redis is optional for direct local development; without `CACHE_URL`, Django
uses a process-local memory cache.

```bash
cd /Users/mohrez/code/inventory-SaaS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Settings are split into base/development/test/production modules and production
secrets are environment-only. Set `CACHE_URL=redis://localhost:6380/1` to use
the Compose Redis service from a locally running Django process. The dashboard
TTL is configurable with `DASHBOARD_CACHE_TTL_SECONDS` and defaults to 60.

Docker Compose provides PostgreSQL, Redis, the backend, and a separate Celery
worker. Redis is published on host port 6380 to avoid colliding with a system
Redis on 6379:

```bash
docker compose up -d --build db redis backend worker
docker compose exec redis redis-cli ping
docker compose exec worker celery -A config inspect ping
```

Redis database `0` is reserved for the Celery broker and database `1` for the
Django dashboard cache. The worker has `RUN_MIGRATIONS=false`; migrations remain
the backend/release process's responsibility. Tests run Celery tasks eagerly,
so the automated suite does not require a live broker.

Development email defaults to Django's console backend and tests use its
in-memory backend. Production delivery requires selecting the SMTP backend and
supplying host, port, credentials, TLS choice, timeout, and default sender via
environment variables. No email-provider SDK or credential is stored in the
repository.

Sale-completion email delivery uses at-least-once queue semantics. The
persistent event and `sent` check prevent normal duplicate task execution from
resending, but there is still a small unavoidable SMTP gap: a worker crash
after the provider accepts an email and before the database marks it sent can
produce a duplicate on retry. Automatic replay of pending rows left by a
broker outage is not implemented yet.

Render uses the production settings module. A shared production cache requires
provisioning Redis and supplying `CACHE_URL`; otherwise each backend process
falls back to its own local-memory cache.

### Frontend

```bash
cd /Users/mohrez/code/inventory-saas-frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. A custom backend can be supplied
with `VITE_API_BASE_URL`.

## 12. Verification and definition of done

Backend checks:

```bash
cd /Users/mohrez/code/inventory-SaaS
venv/bin/python manage.py check
venv/bin/python manage.py makemigrations --check --dry-run
venv/bin/python manage.py test
```

Optional explicit OpenAPI validation:

```bash
venv/bin/python manage.py spectacular \
  --file /tmp/inventory-openapi.yaml --validate
```

Frontend checks:

```bash
cd /Users/mohrez/code/inventory-saas-frontend
npm test
npm run lint
npm run build
```

At last backend verification on 2026-09-20:

- Django: 155/155 tests passed
- Vitest: 31/31 tests passed
- oxlint: passed without warnings
- TypeScript/Vite production build: passed
- Migration drift check: no changes detected
- `stores.0007_store_invitation_and_default_permissions` applied locally
- OpenAPI validation: zero errors and three non-blocking enum-name collision
  warnings for repeated `role`/`status` choice field names

A feature is not complete until:

1. Backend tenant and capability checks exist.
2. Business mutations are atomic where state can race.
3. API schema/types are updated.
4. Frontend loading, success, empty, and error states are handled.
5. Regression tests cover happy path, authorization, validation, and tenant
   isolation.
6. Concurrency is tested when inventory, counters, membership, or one-time
   tokens are involved.
7. Full Django tests, Vitest, lint, and production build pass.
8. This handoff is updated for new product decisions or public interfaces.

## 13. How an AI should continue this project

Follow this sequence for every task:

1. Read this file and `README.md`.
2. Run `git status --short` in both repositories.
3. Inspect the relevant model, serializer, view, service, permission, frontend
   API adapter, page, and existing tests before changing anything.
4. State the behavior and invariants being preserved.
5. Implement backend contract and tests first when the UI depends on a new API.
6. Implement frontend types, API adapter, UI states, and tests.
7. Do not rewrite unrelated user changes or use destructive Git commands.
8. Run targeted tests while iterating, then the complete verification suite.
9. Report migrations, external state changes, and any remaining risk clearly.

Preferred engineering style:

- Make the smallest coherent change that completes a user workflow.
- Prefer database constraints plus service validation over UI-only rules.
- Use `transaction.atomic()` and `select_for_update()` for race-sensitive
  changes.
- Preserve backward compatibility unless removal was explicitly requested.
- Keep error responses stable enough for the frontend to map them.
- Keep code and tests as behavioral source of truth; update stale docs.
- Never weaken tenant isolation for convenience.

## 14. Known limitations and production blockers

The repository now contains production-oriented configuration, Docker, CI,
health checks, logging, monitoring hooks, and deployment/runbook documentation.
Cloud account configuration, a paid backed-up database, the restore drill, and
real SMS credentials remain external launch gates.

High-priority blockers:

- Password recovery remains feature-flagged off until a Kavenegar account and
  approved OTP template are configured and tested from Render.
- DRF auth throttles and PostgreSQL-backed OTP rate limits exist; invitation
  preview/accept endpoints still need dedicated abuse-rate scopes.
- No automated SMS/email invitation delivery.
- Redis-backed caching is optional. Production still needs a managed Redis
  service and `CACHE_URL` before multiple backend processes can share cached
  dashboard responses.
- The Celery worker, persistent NotificationEvent outbox, per-store destination
  email, post-commit task enqueueing, bounded retry orchestration, and
  plain-text Django email service exist. Production SMTP credentials, automatic
  replay of pending events after a broker outage, and Celery Beat are not
  implemented yet. No result backend is configured because delivery state
  lives in the outbox record instead of storing every task result.
- The public demo account is shared and writable, so concurrent visitors may
  see each other's changes until its guarded tenant reset runs again.
- `WantedCustomerRequest` is stored as an audit trail but does not yet have a
  dedicated history endpoint.
- CI, Render/Vercel configuration, health checks, JSON logging, Sentry hooks,
  and operations runbooks exist. Backups and rollback/restore drills require
  the real cloud resources and must be completed before customer data.
- No subscription/billing/plan enforcement.
- No multi-store membership or store switching by design.
- UI is mobile-first and functional but still needs broader browser/accessibility
  review and deployment testing.
- OpenAPI generation may emit non-blocking enum-name collision warnings for
  repeated fields such as `role` and `status`.

Recommended next engineering phase:

1. Configure a real SMTP provider through environment variables in staging and
   verify delivery without committing credentials.
2. Add a small replay command for old pending events so a temporary broker
   outage can be recovered without manually publishing task IDs.
3. Add one Celery Beat daily sales/low-stock digest after immediate sale
   notification is stable.
4. Keep dashboard caching and notification delivery independent: Redis outages
   may degrade cache/queue behavior but must not corrupt inventory or sales.

## 15. Decision history

Important completed phases, based on Git history and current code:

- Backend tenant isolation and one-membership constraint
- Catalog filters and paginated endpoints
- Complete sale schema and draft item editing/deletion
- Atomic checkout, cancellation, and inventory audit behavior
- Current-user store/membership context
- Frontend mobile RTL foundation and Django integration
- Auth, onboarding, dashboard, catalog, sales, customers, wanted, inventory,
  settings, detail pages, filters, reports, and capability-aware routes
- Inventory history and member capability management
- Store invitation backend, migration, default-permission backfill, API tests,
  concurrency test, and end-to-end smoke path
- Invitation frontend page, manager UI, safe login return, API tests, page-state
  tests, copy-link test, lint, and production build verification
- Product creation without variants and inventory-led size/first-stock creation,
  including permission-aware UI and retry after partial two-request failure
- Guarded one-click demo login plus an atomic service-backed synthetic tenant
  rebuild covering every implemented product workflow
- Atomic sale completion timestamps used by dashboard and financial reports
- Tenant/date-scoped dashboard response caching with post-commit version
  invalidation and database fallback when Redis is unavailable
- Celery worker foundation using Redis DB 0 as broker, eager isolated tests, and
  a real broker-to-worker health-check task
- Transactional sale-completed NotificationEvent outbox with a JSON snapshot,
  pending/sent/failed state, retry metadata, and database-level deduplication
- Optional per-store notification email, environment-driven Django email
  backends, and a tested plain-text sale-completion email service
- Post-commit Celery email delivery with persistent attempt state, duplicate
  suppression for sent events, and bounded retry for transient SMTP failures

Older plans may describe invitations, tenant fixes, reports, or frontend pages
as future work even though they are now implemented. Prefer this document,
current Git history, and passing tests over stale roadmap text.

### Important backend commits on the current main line

| Commit | Outcome |
| --- | --- |
| `04affe7` | Preserved DRF settings while adding pagination and SimpleJWT configuration |
| `ac024d5` | Restored tenant-scoped variant input for sale items |
| `a67636c` | Enforced inventory movement direction and non-negative stock invariants |
| `a2d6783` | Corrected dashboard metrics, date validation, and schema behavior |
| `a2bfbb4` | Stabilized product filters and deterministic pagination ordering |
| `6ca1ff4` | Added the first broad PostgreSQL-backed regression suite |
| `e926530` | Added current user/store/role/effective-permission context |
| `52b9a28` | Returned the complete draft Sale context after creation |
| `7b2ea97` | Added draft SaleItem update/delete and total recalculation |
| `547320d` | Added safe deletion of abandoned draft sales |
| `032d8dc` | Restored correct OpenAPI metadata for sale completion |
| `2e1fb67` | Expanded the backend developer handoff |
| `1a7478b` | Ignored local cookies, editor files, and migration backup artifacts |
| `5f8717f` | Removed obsolete roadmap/task documents that no longer matched code |
| `593df8a` | Added API response fields and member input needed by the frontend |
| `82498ee` | Linked the separate React frontend from backend documentation |
| `5a67c92` | Added server-side search for customer, sale, and inventory lists |
| `6c829f2` | Added product ordering and Wanted search/filter validation |
| `a7148a7` | Added current-user profile and manager store-settings APIs |
| `1ff9a01` | Added financial/inventory reports with historical unit-cost snapshots |
| `421ea5c` | Added secure store invitations, default-permission backfill, and smoke coverage |
| `17098cf` | Recorded atomic sale completion timestamps and used them in reporting |

### How the engineering approach evolved

The project began as a conventional DRF CRUD backend. The main refactoring
sequence was deliberate:

1. Fix critical stock direction, checkout, and cross-store access bugs.
2. Replace ambiguous membership selection with a one-membership invariant.
3. Centralize capability checks while keeping managers implicitly privileged.
4. Move state transitions into services with transactions and row locks.
5. Add tenant, permission, integration, schema, and PostgreSQL concurrency tests.
6. Fill the API gaps exposed by building the real frontend: richer responses,
   item editing, draft deletion, search, profile/settings, and reports.
7. Replace direct employee lookup as the primary onboarding UX with secure
   phone-bound invitations.
8. Introduce Redis first for one measured, read-heavy dashboard use case while
   keeping PostgreSQL authoritative and invalidation transaction-aware.
9. Add Celery as a separately deployable worker foundation before introducing
   notification domain models or external email side effects.
10. Choose standard SMTP email over Telegram for store notifications, keeping
    provider credentials in environment variables and avoiding vendor SDKs.

Future work should continue this pattern: let a concrete workflow expose the
smallest missing contract, implement it end to end, test the invariant, and
commit it independently. Do not build speculative framework layers.
