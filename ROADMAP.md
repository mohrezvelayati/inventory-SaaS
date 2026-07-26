# Inventory SaaS — Roadmap to a Production-Ready MVP

The commit-sized implementation backlog for this roadmap is maintained in
[`TASKS.md`](TASKS.md).

## Goal

Deliver a secure, mobile-first inventory and sales platform that a small retail
store can use in production for:

- Product and size-variant management
- Stock entry, adjustment, and history
- Customer management
- Draft sale creation and checkout
- Unavailable-product demand tracking
- Store dashboard analytics
- Employee access with manager-controlled permissions

This roadmap treats the source code as authoritative. Security, tenant
isolation, and inventory correctness must be completed before new business
features.

## MVP Decisions

These decisions remove ambiguity from the current implementation:

1. One user can belong to exactly one store for the MVP.
2. Every business object belongs to that store, directly or through a parent.
3. A Manager has full store access.
4. Seller and Admin are descriptive roles; their capabilities are assigned by
   the Manager.
5. `InventoryMovement.quantity` is signed: stock-in is positive and stock-out
   is negative.
6. `ProductVariant.current_stock` is a cached balance. Inventory movements are
   the audit trail, and all stock changes go through inventory services.
7. Completed sales are immutable. Draft sales may be cancelled. Returns and
   refunds are post-MVP workflows.
8. Prices use whole currency units. The currency and business timezone must be
   explicitly configured before launch.

## Current Baseline

The project already has a coherent Django REST Framework domain skeleton:

- JWT and session authentication
- Store memberships, roles, and configurable permissions
- Categories, products, and variants
- Inventory movements and current stock
- Customers
- Draft sales, sale items, and sale completion
- Wanted-product aggregation
- Dashboard aggregation services
- OpenAPI and Swagger integration

The current code is not production-safe. Known release blockers include:

- Cross-tenant sale and inventory mutations
- Ambiguous `.memberships.first()` store resolution
- Sale completion increasing stock instead of decreasing it
- Stock validation checking only the first sale item
- Missing row locks during stock changes
- Incomplete and inconsistent permission enforcement
- Unrestricted membership creation and role escalation
- Unscoped serializer relation querysets
- Wanted-request fields being ignored or lost
- Empty automated test modules
- Development-only settings and hardcoded secrets

---

## Milestone 0 — Reproducible Development Baseline

**Outcome:** Any developer or CI runner can install, configure, and verify the
project consistently.

### Work

- Add a dependency manifest and lock file. Do not rely on the local `venv`.
- Add `.env.example` containing names only, with safe development defaults
  where appropriate.
- Document setup, migrations, test execution, and local API startup.
- Add code-quality tooling for formatting, linting, and import checks.
- Add a CI workflow that runs checks, migration drift detection, and tests
  against PostgreSQL.
- Establish test factories/builders for User, Store, Membership, Product,
  Variant, Customer, Sale, and WantedProduct.
- Record and protect the current API version under `/api/v1/`.

### Acceptance

- A clean checkout can be installed using documented commands.
- CI passes `manage.py check`, `makemigrations --check --dry-run`, linting, and
  an initial test suite.
- No generated environment, cache, or OS files are tracked.

---

## Milestone 1 — Tenant Isolation Foundation

**Outcome:** A user cannot read or mutate another store's data.

### Work

- Enforce one membership per user:
  - Reject a second store or membership through the API.
  - Add a database uniqueness constraint on `StoreMembership.user`.
  - Plan a data migration before applying the constraint to existing data.
- Add a centralized tenant resolver such as
  `get_current_membership(user)` / `get_current_store(user)`.
- Return a controlled API error when a user has no membership.
- Replace every `.memberships.first()` call.
- Add tenant-scoped queryset mixins/helpers for list and object endpoints.
- Scope sale lookups in item creation, completion, detail, and cancellation.
- Scope all serializer relation fields at request time:
  - Customer must belong to the active store.
  - Product and variant must belong to the active store.
  - Wanted product/customer links must belong to the active store.
- Repeat ownership validation inside mutating services as defense in depth.
- Use `404` for inaccessible tenant objects so object existence is not leaked.

### Required Tests

- Store A cannot list, retrieve, update, delete, or reference Store B data.
- Cross-store sale, variant, customer, product, and wanted IDs are rejected.
- A user cannot create a second store or second membership.
- A user without a membership receives a stable client error, not a server
  exception.

### Acceptance

- Every business queryset and object lookup has an explicit tenant boundary.
- Tenant-isolation integration tests cover every API that accepts an object ID.

---

## Milestone 2 — Inventory and Sales Correctness

**Outcome:** Checkout is atomic, concurrency-safe, auditable, and always
produces the correct stock balance.

### Work

- Fix sale stock direction so completion writes negative movement quantities.
- Move stock validation and error raising outside the item loop.
- Aggregate required quantity by variant before validation. Two sale lines for
  the same variant must be validated as one requirement.
- Lock the draft sale and affected variants with `select_for_update()` inside
  one completion transaction.
- Re-fetch locked database rows instead of updating stale serializer objects.
- Prevent two concurrent completion requests from completing the same sale.
- Define and enforce movement invariants:
  - Purchase quantity is positive.
  - Sale quantity is negative and can only be created by sale completion.
  - Adjustment quantity may be positive or negative.
  - The resulting stock can never be negative.
- Validate discount is non-negative and does not exceed the line subtotal.
- Validate seller, customer, sale, and variants all belong to the same store.
- Make completed sale items and totals immutable.
- Rename `cansel_sale` to `cancel_sale` and expose draft cancellation safely.
- Add a stock reconciliation command that compares cached stock with the sum
  of movements and reports mismatches.
- Consider linking sale movements to their originating sale/item for stronger
  auditability and idempotency.

### Required Tests

- Purchase and adjustment movements update stock correctly.
- Completing a sale decreases stock exactly once.
- Every sale item is validated.
- Duplicate variant lines are validated using their combined quantity.
- Insufficient stock rolls back the entire completion.
- Cross-store variants cannot be added to a sale.
- Concurrent checkouts cannot oversell or double-complete a sale.
- Empty, completed, cancelled, and invalid sales cannot be completed.
- Invalid discounts are rejected.

### Acceptance

- There is no code path that changes `current_stock` outside the inventory
  service.
- Stock and movement history remain consistent after success and rollback.
- Concurrency tests pass against PostgreSQL.

---

## Milestone 3 — Authorization and Employee Management

**Outcome:** Managers control what employees can do, with no privilege
escalation path.

### Work

- Make `Permission.code` unique and define the supported capability catalog.
- Seed capabilities through a data migration or idempotent management command.
- Fix permission queries, including the broken variant permission lookup.
- Keep Manager as an implicit full-access role.
- Make `HasPermission` resolve the current membership and check assigned
  capabilities for Seller/Admin.
- Create an endpoint-to-capability matrix and apply it consistently.
- Restrict membership listing, creation, role changes, permission assignment,
  and removal to Managers.
- Prevent a user from assigning their own role or permissions.
- Prevent removal/demotion of the store's last Manager.
- Replace raw arbitrary-user membership creation with a controlled employee
  onboarding or invitation flow.
- Add APIs to list capabilities and assign/revoke them for an employee.

### Suggested Capabilities

- `manage_catalog`
- `view_inventory`
- `manage_inventory`
- `create_sale`
- `view_sales`
- `manage_customers`
- `manage_wanted`
- `view_dashboard`
- `manage_members`

### Required Tests

- Manager has full access without explicit permission rows.
- Seller/Admin are denied by default.
- Each assigned capability grants only its intended actions.
- Employees cannot manage memberships or elevate themselves.
- Permissions never apply across stores.

### Acceptance

- Every non-public endpoint has an intentional permission policy.
- The effective permission behavior is documented in OpenAPI.

---

## Milestone 4 — Complete and Stabilize the MVP API

**Outcome:** The backend exposes all workflows needed by the mobile-first
client.

### Catalog

- Add category detail/update/delete.
- Add product detail/update/delete.
- Add variant list/detail/update/delete.
- Expose and validate product categories correctly.
- Define deletion rules for products/variants with sales or movement history.
- Add product search, category filtering, stock filtering, and pagination.

### Inventory

- Add a tenant-scoped movement-history list endpoint.
- Filter by product, variant, movement type, creator, and date range.
- Separate manager stock-adjustment input from read serializers.
- Never expose a generic endpoint that can forge sale movements.

### Sales

- Add sale detail.
- Add draft item update/removal.
- Add draft cancellation.
- Add filtering by status, seller, customer, channel, and date range.
- Return the created SaleItem and calculated prices from item creation.
- Return the completed sale representation from checkout.
- Standardize service validation errors as documented `400` responses.

### Customers

- Add detail/update/delete.
- Add search by name and phone.
- Preserve customer history when a customer is removed.
- Use `create_customer()` consistently for phone-number deduplication.

### Wanted Products

- Accept, validate, and save brand, customer, and `created_by`.
- Ensure linked product/customer belong to the store.
- Make aggregation concurrency-safe.
- Reconcile `get_or_create` fields with the database uniqueness constraint.
- Add wanted detail/history and optional resolution/link-to-product behavior.

### Cross-Cutting API Work

- Add global pagination defaults and per-endpoint limits.
- Add consistent response/error envelopes only if the frontend needs them.
- Validate all date parameters with serializers.
- Add schema serializers for Dashboard and SaleComplete views.
- Generate an OpenAPI schema with zero errors.
- Add API examples for every write operation.

### Acceptance

- All README MVP workflows are available through documented APIs.
- OpenAPI matches the URL modules and actual request/response behavior.
- API integration tests cover successful and denied paths.

---

## Milestone 5 — Dashboard and Business Data Quality

**Outcome:** Managers receive accurate, efficient, and understandable business
metrics.

### Work

- Validate `date_from` and `date_to`, including ordering and maximum range.
- Define whether date ranges are inclusive and document timezone behavior.
- Configure the launch currency and business timezone.
- Move Python-side stock summation to database aggregation.
- Consolidate dashboard aggregates to avoid unnecessary repeated queries.
- Add appropriate `select_related`, `prefetch_related`, and database indexes.
- Verify revenue, discount, order count, top products, low stock, and wanted
  rankings against known fixtures.
- Remove or consolidate duplicate/unused dashboard modules.
- Define low-stock threshold configuration rather than hardcoding `2`.

### Acceptance

- Dashboard queries remain within an agreed query-count budget.
- Every metric has a deterministic definition and automated tests.

---

## Milestone 6 — Mobile-First Frontend

**Outcome:** A store can complete all MVP workflows without using Swagger or
the Django admin.

### Product Decision

Choose and document the frontend stack before implementation. The current
repository does not contain a frontend. The client must consume `/api/v1/`
without duplicating backend authorization logic.

### Required Screens

- Registration, login, logout, and password recovery
- Store onboarding
- Dashboard
- Category, product, and variant management
- Inventory list, stock entry, adjustment, and movement history
- New sale flow optimized for quick mobile checkout
- Sale list, detail, draft editing, completion, and cancellation
- Customer list, search, create, and edit
- Wanted request capture and demand ranking
- Employee list, role display, and capability assignment
- Account and store settings

### UX Requirements

- Mobile-first layouts and touch targets
- Fast product/size lookup during checkout
- Clear stock availability and low-stock states
- Confirmation for destructive or final actions
- Accessible forms, validation messages, loading states, and empty states
- Safe token storage and automatic refresh behavior
- No UI-only permission assumptions; handle backend `401`/`403` responses
- Basic end-to-end tests for onboarding, stock entry, sale, and wanted request

### Acceptance

- A first-time Manager can onboard a store and complete a sale on a phone.
- An employee sees only actions allowed by their assigned capabilities.
- Critical end-to-end workflows pass in CI.

---

## Milestone 7 — Production Operations and Security

**Outcome:** The system can be deployed, monitored, backed up, and recovered
safely.

### Work

- Split development and production configuration.
- Load secret key, database, allowed hosts, CORS/CSRF origins, and other secrets
  from environment variables.
- Remove all hardcoded credentials and rotate any exposed values.
- Configure HTTPS redirect, secure cookies, HSTS, trusted proxy behavior, and
  production renderers.
- Configure token lifetimes explicitly.
- Add refresh-token blacklisting/logout.
- Apply Django password validators during registration and password changes.
- Add password reset and account recovery.
- Add throttling for login, registration, password reset, and expensive APIs.
- Configure static-file serving and a production WSGI/ASGI server.
- Add structured logs, request correlation IDs, health checks, and error
  tracking.
- Add database backup, restore, retention, and migration procedures.
- Add Docker or an equivalent reproducible deployment package.
- Add staging and production CI/CD with migration and rollback steps.
- Run dependency, secret, and static security scans.
- Resolve all relevant `manage.py check --deploy` warnings.

### Acceptance

- Staging is deployed from CI using production-like PostgreSQL.
- Backup restoration and rollback are rehearsed.
- No secret exists in source control or generated API output.
- Health checks, logs, and error alerts are operational.

---

## Milestone 8 — Release Verification

**Outcome:** The MVP is approved for real store data.

### Release Gates

- Tenant-isolation tests pass for every object-reference endpoint.
- Inventory and concurrent-checkout tests pass against PostgreSQL.
- Critical service and permission paths have complete behavioral coverage;
  overall backend coverage target is at least 80%.
- Frontend critical-path end-to-end tests pass.
- OpenAPI generation has zero errors and documented behavior matches runtime.
- Model/migration drift check passes.
- Django deployment check has no unresolved launch-blocking warning.
- Performance smoke tests cover large product, movement, customer, and sale
  lists.
- Accessibility and mobile-browser smoke tests pass.
- A clean staging database can complete:
  1. User registration and login
  2. Store onboarding
  3. Employee setup
  4. Product and variant creation
  5. Stock purchase entry
  6. Customer creation
  7. Draft sale and checkout
  8. Correct stock deduction
  9. Wanted request capture
  10. Accurate dashboard reporting
- Launch checklist, support process, and incident rollback owner are recorded.

## Definition of MVP Complete

The MVP is complete only when:

1. No known cross-tenant read or mutation is possible.
2. Inventory cannot become incorrect through normal API use or concurrent
   checkout.
3. Employee authorization is enforced by the backend.
4. All promised MVP workflows are usable from the mobile-first frontend.
5. Critical workflows have automated backend and end-to-end coverage.
6. The application is deployed with secure configuration, monitoring, and
   tested backups.

## Recommended Execution Order

Do not develop these milestones as independent feature tracks. Use this
dependency order:

`M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8`

Testing and API documentation are part of every milestone, not tasks deferred
to the end. Production infrastructure can be prepared in parallel after M0,
but release remains blocked until M1–M6 are accepted.

## Indicative Effort

For one experienced full-stack developer working with an available product
owner, the production-ready MVP is approximately 7–10 focused weeks. This is a
planning range, not a commitment; frontend stack selection, employee
invitation requirements, deployment platform, and the condition of any live
database can materially change it.

## Post-MVP Backlog

After the release gates pass:

- Suppliers and purchase orders
- Reorder suggestions
- Returns and refunds
- Customer campaigns and SMS notifications
- Barcode/QR scanning
- Import/export
- Multi-branch stores
- Financial and profit reporting
- Multi-currency support
- Advanced analytics and trends
- Soft deletion and archival policies
