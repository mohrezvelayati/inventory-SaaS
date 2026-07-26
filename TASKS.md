# Inventory SaaS — Execution Checklist

This file converts `ROADMAP.md` into small, ordered implementation tasks for
the production-ready MVP.

## How to Use This Checklist

- Work in milestone order: `M0` through `M8`.
- Complete tasks in ID order unless a task explicitly says it can run in
  parallel.
- Keep each task small enough for one focused change.
- An implementation task is not complete until its tests and relevant API
  documentation pass.
- Do not mark a milestone gate complete while any release-blocking task in that
  milestone remains open.
- Record unexpected scope beneath the relevant task instead of silently
  expanding it.

## Definition of Done for Every Code Task

- [ ] The implementation matches the current milestone's documented decision.
- [ ] Tenant ownership is checked for every referenced business object.
- [ ] Success, validation-failure, permission, and tenant-denial paths are
      tested when applicable.
- [ ] `manage.py check` passes.
- [ ] `makemigrations --check --dry-run` passes unless the task intentionally
      adds a reviewed migration.
- [ ] OpenAPI output is updated when an API contract changes.
- [ ] No unrelated file is changed.

---

## M0 — Reproducible Development Baseline

### Repository Cleanup

- [ ] **M0-001** Remove the tracked root `.DS_Store` and verify `.gitignore`
      prevents it from returning.
- [ ] **M0-002** Decide and document the supported Python version.
- [ ] **M0-003** Choose one dependency workflow (`pyproject.toml` plus lock file
      is preferred).
- [ ] **M0-004** Add direct runtime dependencies to the chosen manifest.
- [ ] **M0-005** Add development and test dependencies to a separate dependency
      group.
- [ ] **M0-006** Generate and commit the lock file.
- [ ] **M0-007** Verify a fresh virtual environment installs only from the
      manifest and lock file.

### Local Configuration

- [ ] **M0-008** List every required environment variable.
- [ ] **M0-009** Add `.env.example` with variable names and non-secret examples.
- [ ] **M0-010** Add a local PostgreSQL setup option to the README.
- [ ] **M0-011** Document database creation and migration commands.
- [ ] **M0-012** Document API startup, admin creation, and Swagger URLs.
- [ ] **M0-013** Document the check, test, lint, and schema-generation commands.

### Quality Tooling

- [ ] **M0-014** Select and configure a Python formatter.
- [ ] **M0-015** Select and configure a Python linter/import checker.
- [ ] **M0-016** Format the existing code in a standalone mechanical change.
- [ ] **M0-017** Fix existing lint errors without changing behavior.
- [ ] **M0-018** Add a command that validates the generated OpenAPI schema.

### Test Foundation

- [ ] **M0-019** Create a shared test helper for user creation.
- [ ] **M0-020** Create helpers for store and membership creation.
- [ ] **M0-021** Create helpers for category, product, and variant creation.
- [ ] **M0-022** Create helpers for inventory movement creation.
- [ ] **M0-023** Create helpers for customer, sale, and sale-item creation.
- [ ] **M0-024** Create helpers for wanted-product/request creation.
- [ ] **M0-025** Add an authenticated DRF API client helper.
- [ ] **M0-026** Add a smoke test for registration, login, and `/users/me/`.

### Continuous Integration

- [ ] **M0-027** Add a CI job with a PostgreSQL service.
- [ ] **M0-028** Add dependency installation from the lock file to CI.
- [ ] **M0-029** Add formatting and lint checks to CI.
- [ ] **M0-030** Add `manage.py check` to CI.
- [ ] **M0-031** Add migration-drift detection to CI.
- [ ] **M0-032** Add the test suite to CI.
- [ ] **M0-033** Add OpenAPI schema validation to CI.

### M0 Gate

- [ ] **M0-GATE** A clean checkout can be installed, configured, migrated,
      checked, and tested using only documented commands.

---

## M1 — Tenant Isolation Foundation

### Tenant Decision Enforcement

- [ ] **M1-001** Add a reusable domain exception for a missing store membership.
- [ ] **M1-002** Add `get_current_membership(user)` that requires exactly one
      membership.
- [ ] **M1-003** Add `get_current_store(user)` using the membership resolver.
- [ ] **M1-004** Map missing/invalid membership exceptions to a stable API
      response.
- [ ] **M1-005** Inventory every `.memberships.first()` usage in the repository.
- [ ] **M1-006** Replace `.memberships.first()` in `stores`.
- [ ] **M1-007** Replace `.memberships.first()` in `catalog`.
- [ ] **M1-008** Replace `.memberships.first()` in `inventory`.
- [ ] **M1-009** Replace `.memberships.first()` in `sales`.
- [ ] **M1-010** Replace `.memberships.first()` in `customers`.
- [ ] **M1-011** Replace `.memberships.first()` in `wanted`.
- [ ] **M1-012** Replace `.memberships.first()` in `dashboard`.
- [ ] **M1-013** Add API validation that rejects creation of a second store.
- [ ] **M1-014** Add API validation that rejects creation of a second membership
      for a user.
- [ ] **M1-015** Add a data migration that reports or resolves users with
      multiple memberships.
- [ ] **M1-016** Add a database uniqueness constraint on
      `StoreMembership.user`.
- [ ] **M1-017** Test the one-user/one-membership API and database constraints.

### Scoped Query Infrastructure

- [ ] **M1-018** Define a consistent tenant-queryset helper or view mixin.
- [ ] **M1-019** Add a scoped `Category` queryset helper.
- [ ] **M1-020** Add scoped `Product` and `ProductVariant` queryset helpers.
- [ ] **M1-021** Add a scoped `InventoryMovement` queryset helper.
- [ ] **M1-022** Add scoped `Customer` queryset helpers.
- [ ] **M1-023** Add scoped `Sale` and `SaleItem` queryset helpers.
- [ ] **M1-024** Add scoped `WantedProduct` and request queryset helpers.

### Secure Existing Object References

- [ ] **M1-025** Scope `SaleItemCreateView` sale lookup to the current store.
- [ ] **M1-026** Scope `SaleCompleteView` sale lookup to the current store.
- [ ] **M1-027** Scope sale-create customer input to the current store.
- [ ] **M1-028** Scope sale-item variant input to the current store.
- [ ] **M1-029** Scope inventory-movement variant input to the current store.
- [ ] **M1-030** Scope wanted-product input to the current store.
- [ ] **M1-031** Scope wanted-customer input to the current store.
- [ ] **M1-032** Validate product categories belong to the product's store.
- [ ] **M1-033** Add ownership assertions inside catalog mutating services.
- [ ] **M1-034** Add ownership assertions inside inventory mutating services.
- [ ] **M1-035** Add ownership assertions inside sales mutating services.
- [ ] **M1-036** Add ownership assertions inside wanted mutating services.
- [ ] **M1-037** Standardize inaccessible cross-tenant objects as `404`.

### Tenant Test Matrix

- [ ] **M1-038** Test catalog list/create denial across stores.
- [ ] **M1-039** Test variant reference denial across stores.
- [ ] **M1-040** Test inventory read/mutation denial across stores.
- [ ] **M1-041** Test customer read/reference denial across stores.
- [ ] **M1-042** Test sale read/mutation denial across stores.
- [ ] **M1-043** Test wanted read/reference denial across stores.
- [ ] **M1-044** Test dashboard data never includes another store.
- [ ] **M1-045** Search for remaining global business-object querysets and
      document why each is safe or fix it.

### M1 Gate

- [ ] **M1-GATE** Every existing endpoint and service has an explicit tenant
      boundary, and cross-store tests pass for every accepted object ID.

---

## M2 — Inventory and Sales Correctness

### Movement Contract

- [ ] **M2-001** Document signed movement quantity semantics in code and API
      documentation.
- [ ] **M2-002** Add validation that purchase quantities are positive.
- [ ] **M2-003** Add validation that sale quantities are negative.
- [ ] **M2-004** Allow adjustment quantities to be positive or negative but not
      zero.
- [ ] **M2-005** Prevent clients from creating `sale` movements through the
      generic movement endpoint.
- [ ] **M2-006** Split manual movement input from movement output serializers.
- [ ] **M2-007** Test all movement-type/quantity combinations.

### Atomic Stock Service

- [ ] **M2-008** Re-fetch the target variant inside the inventory transaction.
- [ ] **M2-009** Lock the target variant using `select_for_update()`.
- [ ] **M2-010** Calculate the new stock from the locked database value.
- [ ] **M2-011** Reject an update that would produce negative stock.
- [ ] **M2-012** Save only the `current_stock` field.
- [ ] **M2-013** Create the movement in the same transaction as the stock
      update.
- [ ] **M2-014** Test transaction rollback when movement creation fails.
- [ ] **M2-015** Test concurrent movement requests against PostgreSQL.
- [ ] **M2-016** Search for direct `current_stock` writes and remove or justify
      each one.

### Sale Item Validation

- [ ] **M2-017** Reject zero or negative sale-item quantities in the service.
- [ ] **M2-018** Reject negative discounts.
- [ ] **M2-019** Reject discounts greater than the line subtotal.
- [ ] **M2-020** Validate sale and variant store ownership in `add_sale_item`.
- [ ] **M2-021** Return the created SaleItem rather than the parent sale.
- [ ] **M2-022** Set `serializer.instance` so item-create output includes
      calculated prices.
- [ ] **M2-023** Test unit-price snapshots and final-price calculations.

### Stock Validation

- [ ] **M2-024** Move stock error raising outside the sale-item loop.
- [ ] **M2-025** Move the successful return outside the sale-item loop.
- [ ] **M2-026** Aggregate requested quantities by variant.
- [ ] **M2-027** Report all insufficient variants in one validation response.
- [ ] **M2-028** Test insufficient stock on the first item.
- [ ] **M2-029** Test insufficient stock on a later item.
- [ ] **M2-030** Test two individually valid lines whose combined quantity is
      insufficient.

### Atomic Sale Completion

- [ ] **M2-031** Re-fetch and lock the Sale inside `complete_sale`.
- [ ] **M2-032** Reject non-draft sales after acquiring the lock.
- [ ] **M2-033** Load and aggregate all sale items inside the transaction.
- [ ] **M2-034** Lock affected variants in a deterministic ID order.
- [ ] **M2-035** Validate stock from the locked variant rows.
- [ ] **M2-036** Pass negative quantities when creating sale movements.
- [ ] **M2-037** Mark the sale completed only after every movement succeeds.
- [ ] **M2-038** Return the completed Sale representation from the endpoint.
- [ ] **M2-039** Test that completion decreases each stock balance exactly once.
- [ ] **M2-040** Test that any failed movement rolls back the full checkout.
- [ ] **M2-041** Test concurrent double-completion requests.
- [ ] **M2-042** Test concurrent sales competing for the final unit.

### Sale State Rules

- [ ] **M2-043** Prevent adding items to completed sales.
- [ ] **M2-044** Prevent adding items to cancelled sales.
- [ ] **M2-045** Prevent completion of an empty sale.
- [ ] **M2-046** Rename `cansel_sale` to `cancel_sale`.
- [ ] **M2-047** Keep draft cancellation stock-neutral.
- [ ] **M2-048** Test all allowed and denied sale state transitions.

### Reconciliation

- [ ] **M2-049** Add a command that sums movements per variant.
- [ ] **M2-050** Compare movement sums with cached `current_stock`.
- [ ] **M2-051** Report mismatches without modifying data by default.
- [ ] **M2-052** Add command tests for matched and mismatched variants.
- [ ] **M2-053** Decide whether sale movements need a source sale/item foreign
      key for idempotency and audit history.
- [ ] **M2-054** Implement the reviewed source-link migration if approved.

### M2 Gate

- [ ] **M2-GATE** Stock remains correct after purchases, adjustments, checkout,
      rollback, duplicate lines, and concurrent requests.

---

## M3 — Authorization and Employee Management

### Capability Catalog

- [ ] **M3-001** Finalize capability names and descriptions.
- [ ] **M3-002** Add a uniqueness constraint to `Permission.code`.
- [ ] **M3-003** Add an idempotent capability seed migration or command.
- [ ] **M3-004** Test capability seeding twice to prove idempotency.
- [ ] **M3-005** Document Manager, Seller, and Admin behavior.

### Permission Engine

- [ ] **M3-006** Make `HasPermission` use the centralized membership resolver.
- [ ] **M3-007** Keep Manager as an explicit implicit-full-access branch.
- [ ] **M3-008** Check `MembershipPermission.permission__code` for employees.
- [ ] **M3-009** Deny employee access when `required_permission` is unset.
- [ ] **M3-010** Fix `CanCreateVariant`'s invalid permission field lookup.
- [ ] **M3-011** Remove duplicate one-off permission logic where
      `HasPermission` can be reused.
- [ ] **M3-012** Unit-test Manager, granted employee, ungranted employee, and
      missing-membership paths.

### Endpoint Policy

- [ ] **M3-013** Write the endpoint-to-capability matrix.
- [ ] **M3-014** Apply catalog permissions.
- [ ] **M3-015** Apply inventory permissions.
- [ ] **M3-016** Apply sales permissions.
- [ ] **M3-017** Apply customer permissions.
- [ ] **M3-018** Apply wanted permissions.
- [ ] **M3-019** Apply dashboard permissions.
- [ ] **M3-020** Apply store/member-management permissions.
- [ ] **M3-021** Add permission information to OpenAPI endpoint descriptions.
- [ ] **M3-022** Add API tests for every matrix row.

### Secure Membership Management

- [ ] **M3-023** Restrict membership listing to Managers or explicitly granted
      employees.
- [ ] **M3-024** Restrict membership creation to Managers.
- [ ] **M3-025** Prevent assigning a membership to another store.
- [ ] **M3-026** Prevent non-Managers from assigning the Manager role.
- [ ] **M3-027** Prevent users from changing their own role.
- [ ] **M3-028** Prevent deletion or demotion of the final Manager.
- [ ] **M3-029** Define employee onboarding by username/phone or invitation.
- [ ] **M3-030** Replace raw arbitrary-user membership creation with the
      selected onboarding flow.
- [ ] **M3-031** Add membership detail/update/remove endpoints.
- [ ] **M3-032** Add capability-list endpoint.
- [ ] **M3-033** Add employee capability assignment endpoint.
- [ ] **M3-034** Add employee capability revocation endpoint.
- [ ] **M3-035** Add self-escalation and cross-store membership tests.

### M3 Gate

- [ ] **M3-GATE** Every private endpoint has a tested capability policy, and no
      employee can elevate their own access.

---

## M4 — Complete and Stabilize the MVP API

### Shared API Behavior

- [ ] **M4-001** Configure global page-number or cursor pagination.
- [ ] **M4-002** Set and document maximum page sizes.
- [ ] **M4-003** Add common filter dependencies.
- [ ] **M4-004** Define consistent validation-error output.
- [ ] **M4-005** Convert service/domain exceptions to documented `400`
      responses.
- [ ] **M4-006** Add serializers for query/date parameters.
- [ ] **M4-007** Add request/response examples for every write endpoint.

### Categories

- [ ] **M4-008** Add tenant-scoped category retrieve endpoint.
- [ ] **M4-009** Add tenant-scoped category update endpoint.
- [ ] **M4-010** Define category deletion behavior for assigned products.
- [ ] **M4-011** Add category delete endpoint using that behavior.
- [ ] **M4-012** Ensure service-created categories set `serializer.instance`.
- [ ] **M4-013** Add category CRUD and tenant tests.

### Products

- [ ] **M4-014** Add categories to product input/output serializers.
- [ ] **M4-015** Validate all assigned categories belong to the store.
- [ ] **M4-016** Add tenant-scoped product retrieve endpoint.
- [ ] **M4-017** Add tenant-scoped product update endpoint.
- [ ] **M4-018** Define deletion/archive behavior for products with history.
- [ ] **M4-019** Add product delete/archive endpoint.
- [ ] **M4-020** Add product name search.
- [ ] **M4-021** Add category filtering.
- [ ] **M4-022** Add stock-state filtering.
- [ ] **M4-023** Add product CRUD, search, filter, pagination, and tenant tests.

### Variants

- [ ] **M4-024** Add variant list under a tenant-scoped product.
- [ ] **M4-025** Add tenant-scoped variant retrieve endpoint.
- [ ] **M4-026** Add variant update endpoint for size and prices.
- [ ] **M4-027** Prevent direct stock updates through the variant endpoint.
- [ ] **M4-028** Define deletion/archive behavior for variants with history.
- [ ] **M4-029** Add variant delete/archive endpoint.
- [ ] **M4-030** Add variant CRUD, history-protection, and tenant tests.

### Inventory History

- [ ] **M4-031** Add a tenant-scoped movement list endpoint.
- [ ] **M4-032** Add product and variant filters.
- [ ] **M4-033** Add movement-type and creator filters.
- [ ] **M4-034** Add validated date-range filters.
- [ ] **M4-035** Add pagination and deterministic ordering.
- [ ] **M4-036** Add movement-history filter and tenant tests.

### Sales

- [ ] **M4-037** Add tenant-scoped sale retrieve endpoint.
- [ ] **M4-038** Add draft sale-item update service and endpoint.
- [ ] **M4-039** Add draft sale-item removal service and endpoint.
- [ ] **M4-040** Recalculate totals after item update/removal.
- [ ] **M4-041** Add draft cancellation endpoint.
- [ ] **M4-042** Add status filtering.
- [ ] **M4-043** Add seller and customer filtering.
- [ ] **M4-044** Add channel filtering.
- [ ] **M4-045** Add validated date-range filtering.
- [ ] **M4-046** Add deterministic ordering and pagination.
- [ ] **M4-047** Add sale detail/item editing/filter/cancel/tenant tests.

### Customers

- [ ] **M4-048** Route customer creation through `create_customer`.
- [ ] **M4-049** Define whether an existing phone updates the customer's name.
- [ ] **M4-050** Add tenant-scoped customer retrieve endpoint.
- [ ] **M4-051** Add customer update endpoint.
- [ ] **M4-052** Define customer deletion/anonymization behavior with sales.
- [ ] **M4-053** Add customer delete/anonymize endpoint.
- [ ] **M4-054** Add name and phone search.
- [ ] **M4-055** Add pagination and ordering.
- [ ] **M4-056** Add customer CRUD, deduplication, history, and tenant tests.

### Wanted Products

- [ ] **M4-057** Add brand to the wanted service's create/update behavior.
- [ ] **M4-058** Add customer input to the wanted serializer.
- [ ] **M4-059** Save `created_by` on each WantedCustomerRequest.
- [ ] **M4-060** Align `get_or_create` fields with the database uniqueness
      constraint.
- [ ] **M4-061** Make wanted-count increments concurrency-safe.
- [ ] **M4-062** Add tenant-scoped wanted retrieve endpoint.
- [ ] **M4-063** Add wanted customer-request history endpoint.
- [ ] **M4-064** Define and add wanted resolve/link-to-product behavior.
- [ ] **M4-065** Add wanted aggregation, field-preservation, concurrency, and
      tenant tests.

### OpenAPI

- [ ] **M4-066** Add an explicit Dashboard response serializer.
- [ ] **M4-067** Add explicit SaleComplete request/response schema metadata.
- [ ] **M4-068** Reconcile generated paths with every URL module.
- [ ] **M4-069** Resolve all schema-generation errors.
- [ ] **M4-070** Verify Swagger can execute each documented write flow.

### M4 Gate

- [ ] **M4-GATE** Every backend workflow required by the README MVP has a
      tenant-safe, capability-protected, tested, and documented API.

---

## M5 — Dashboard and Business Data Quality

### Metric Definitions

- [ ] **M5-001** Define orders, revenue, and discount calculations.
- [ ] **M5-002** Define top-product ranking and tie behavior.
- [ ] **M5-003** Define inventory totals and low-stock behavior.
- [ ] **M5-004** Define wanted-product ranking and tie behavior.
- [ ] **M5-005** Define inclusive date ranges and business timezone.
- [ ] **M5-006** Define the launch currency and whole-unit display.

### Dashboard Input

- [ ] **M5-007** Add a dashboard query serializer.
- [ ] **M5-008** Validate ISO date input.
- [ ] **M5-009** Reject `date_from` after `date_to`.
- [ ] **M5-010** Add a maximum reporting range.
- [ ] **M5-011** Add invalid/default/custom date-range tests.

### Query Improvements

- [ ] **M5-012** Replace Python stock summation with SQL aggregation.
- [ ] **M5-013** Combine compatible sales aggregates.
- [ ] **M5-014** Add required `select_related`/`prefetch_related` calls.
- [ ] **M5-015** Capture query plans for frequent dashboard filters.
- [ ] **M5-016** Add reviewed indexes for store/status/date lookups.
- [ ] **M5-017** Add a configurable low-stock threshold.
- [ ] **M5-018** Remove or merge duplicate/unused dashboard modules.

### Metric Verification

- [ ] **M5-019** Test orders/revenue/discount against fixed fixtures.
- [ ] **M5-020** Test top products against fixed fixtures.
- [ ] **M5-021** Test total and low stock against fixed fixtures.
- [ ] **M5-022** Test wanted ranking against fixed fixtures.
- [ ] **M5-023** Add dashboard query-count tests.

### M5 Gate

- [ ] **M5-GATE** Every dashboard metric has a documented definition, correct
      fixture output, tenant isolation, and an accepted query budget.

---

## M6 — Mobile-First Frontend

### Frontend Foundation

- [ ] **M6-001** Select and document the frontend framework and package manager.
- [ ] **M6-002** Decide whether the frontend lives in this repository or a
      separate repository.
- [ ] **M6-003** Scaffold the application with TypeScript.
- [ ] **M6-004** Add formatting, linting, unit tests, and build checks.
- [ ] **M6-005** Add frontend checks to CI.
- [ ] **M6-006** Define mobile breakpoints, spacing, typography, colors, and
      touch-target minimums.
- [ ] **M6-007** Build shared button, input, select, dialog, table/list, badge,
      loading, empty, and error components.

### API and Authentication

- [ ] **M6-008** Generate or hand-build a typed API client from OpenAPI.
- [ ] **M6-009** Add environment-based API base URL configuration.
- [ ] **M6-010** Implement safe access/refresh token handling.
- [ ] **M6-011** Implement automatic token refresh.
- [ ] **M6-012** Implement global `401`, `403`, validation, and network error
      handling.
- [ ] **M6-013** Build registration screen.
- [ ] **M6-014** Build login and logout flows.
- [ ] **M6-015** Build password recovery/reset flows.
- [ ] **M6-016** Add authenticated-route protection.
- [ ] **M6-017** Load current user, store, role, and capabilities.
- [ ] **M6-018** Hide unavailable actions while still relying on backend
      enforcement.

### Onboarding and Navigation

- [ ] **M6-019** Build mobile navigation and desktop navigation shell.
- [ ] **M6-020** Build no-store onboarding state.
- [ ] **M6-021** Build store creation flow.
- [ ] **M6-022** Add global loading, offline/network, and fatal error states.

### Dashboard

- [ ] **M6-023** Build date-range controls.
- [ ] **M6-024** Build sales summary cards.
- [ ] **M6-025** Build inventory and low-stock sections.
- [ ] **M6-026** Build top-products and top-wanted sections.
- [ ] **M6-027** Add dashboard loading, empty, error, and permission states.

### Catalog

- [ ] **M6-028** Build category list/create/edit/delete UI.
- [ ] **M6-029** Build paginated/searchable product list.
- [ ] **M6-030** Build product create/edit form with categories.
- [ ] **M6-031** Build product detail with variants.
- [ ] **M6-032** Build variant create/edit/archive UI.
- [ ] **M6-033** Add destructive-action confirmations.

### Inventory

- [ ] **M6-034** Build inventory list with product/size search.
- [ ] **M6-035** Build stock purchase entry form.
- [ ] **M6-036** Build stock adjustment form.
- [ ] **M6-037** Build movement history with filters and pagination.
- [ ] **M6-038** Add clear low-stock and insufficient-stock states.

### Sales

- [ ] **M6-039** Build paginated/filterable sale list.
- [ ] **M6-040** Build fast mobile product/variant picker.
- [ ] **M6-041** Build optional customer picker/create shortcut.
- [ ] **M6-042** Build draft sale creation.
- [ ] **M6-043** Build draft item add/update/remove interactions.
- [ ] **M6-044** Build totals and discount display.
- [ ] **M6-045** Build checkout confirmation and completion.
- [ ] **M6-046** Build sale detail.
- [ ] **M6-047** Build draft cancellation.
- [ ] **M6-048** Prevent repeat submissions while checkout is pending.

### Customers and Wanted

- [ ] **M6-049** Build searchable customer list.
- [ ] **M6-050** Build customer create/edit/detail UI.
- [ ] **M6-051** Build wanted-request capture form.
- [ ] **M6-052** Build wanted ranking list and detail/history UI.
- [ ] **M6-053** Build wanted link/resolve-to-product interaction.

### Employees and Settings

- [ ] **M6-054** Build employee list.
- [ ] **M6-055** Build employee onboarding/invitation UI.
- [ ] **M6-056** Build capability assignment UI.
- [ ] **M6-057** Build employee role/removal confirmations.
- [ ] **M6-058** Build account and store settings.

### Frontend Verification

- [ ] **M6-059** Add accessibility checks to shared components.
- [ ] **M6-060** Test layouts on supported mobile viewport sizes.
- [ ] **M6-061** Add end-to-end registration/store onboarding test.
- [ ] **M6-062** Add end-to-end stock purchase test.
- [ ] **M6-063** Add end-to-end sale checkout test.
- [ ] **M6-064** Add end-to-end wanted-request test.
- [ ] **M6-065** Add end-to-end employee permission test.

### M6 Gate

- [ ] **M6-GATE** A Manager can operate the complete MVP on a phone, and an
      employee sees and performs only granted actions.

---

## M7 — Production Operations and Security

### Settings and Secrets

- [ ] **M7-001** Split base, development, test, and production settings.
- [ ] **M7-002** Load `SECRET_KEY` from the environment.
- [ ] **M7-003** Load PostgreSQL configuration from the environment.
- [ ] **M7-004** Load allowed hosts from the environment.
- [ ] **M7-005** Configure CORS and trusted CSRF origins explicitly.
- [ ] **M7-006** Move business timezone/currency configuration out of hardcoded
      development values.
- [ ] **M7-007** Remove hardcoded credentials from source.
- [ ] **M7-008** Rotate every credential that has appeared in source control.
- [ ] **M7-009** Add startup validation for required production variables.

### Web and Token Security

- [ ] **M7-010** Enable production HTTPS redirect.
- [ ] **M7-011** Configure secure session and CSRF cookies.
- [ ] **M7-012** Configure HSTS after HTTPS behavior is verified.
- [ ] **M7-013** Configure trusted proxy/forwarded-protocol handling.
- [ ] **M7-014** Set explicit access and refresh token lifetimes.
- [ ] **M7-015** Enable refresh-token blacklist support.
- [ ] **M7-016** Add logout/token-revocation endpoint and tests.
- [ ] **M7-017** Apply Django password validators during registration.
- [ ] **M7-018** Add authenticated password-change endpoint.
- [ ] **M7-019** Add password reset request/confirm endpoints.
- [ ] **M7-020** Add throttles for login and registration.
- [ ] **M7-021** Add throttles for password reset and expensive report APIs.

### Runtime Packaging

- [ ] **M7-022** Select the hosting platform.
- [ ] **M7-023** Add a production WSGI/ASGI server dependency.
- [ ] **M7-024** Configure static-file collection and serving.
- [ ] **M7-025** Add a container image or equivalent reproducible package.
- [ ] **M7-026** Run the container as a non-root user.
- [ ] **M7-027** Add application health and readiness endpoints.
- [ ] **M7-028** Add a production startup command that applies reviewed
      migrations safely.

### Observability

- [ ] **M7-029** Add structured application logging.
- [ ] **M7-030** Add request correlation IDs.
- [ ] **M7-031** Redact tokens, passwords, phone numbers, and secrets from logs.
- [ ] **M7-032** Configure error tracking.
- [ ] **M7-033** Configure uptime/health monitoring.
- [ ] **M7-034** Add alerts for elevated errors and failed checkouts.

### Database Operations

- [ ] **M7-035** Configure automated PostgreSQL backups.
- [ ] **M7-036** Define backup retention.
- [ ] **M7-037** Document and test database restoration.
- [ ] **M7-038** Document forward and rollback migration procedures.
- [ ] **M7-039** Add staging data seeding without production personal data.

### Delivery Pipeline

- [ ] **M7-040** Add automated staging deployment.
- [ ] **M7-041** Add a staging smoke-test job.
- [ ] **M7-042** Add controlled production deployment.
- [ ] **M7-043** Add dependency vulnerability scanning.
- [ ] **M7-044** Add source secret scanning.
- [ ] **M7-045** Add static security analysis.
- [ ] **M7-046** Run `manage.py check --deploy` and resolve all launch blockers.
- [ ] **M7-047** Write deployment, rollback, and incident runbooks.

### M7 Gate

- [ ] **M7-GATE** Staging is securely deployed, observable, recoverable from a
      tested backup, and reproducible from CI.

---

## M8 — Release Verification

### Automated Release Gates

- [ ] **M8-001** Run the complete backend suite against PostgreSQL.
- [ ] **M8-002** Confirm tenant matrix coverage for every object-reference API.
- [ ] **M8-003** Confirm concurrency tests run reliably in CI.
- [ ] **M8-004** Measure backend coverage and close critical gaps.
- [ ] **M8-005** Reach at least 80% overall backend coverage.
- [ ] **M8-006** Run all frontend unit/component tests.
- [ ] **M8-007** Run all critical end-to-end tests.
- [ ] **M8-008** Generate and validate OpenAPI with zero errors.
- [ ] **M8-009** Confirm no model/migration drift.
- [ ] **M8-010** Confirm no unresolved deployment-check launch blocker.
- [ ] **M8-011** Run dependency, secret, and static security scans.

### Performance and Compatibility

- [ ] **M8-012** Seed staging with large product, customer, movement, and sale
      datasets.
- [ ] **M8-013** Load-test authentication and common list APIs.
- [ ] **M8-014** Load-test sale completion under stock contention.
- [ ] **M8-015** Measure and accept dashboard response performance.
- [ ] **M8-016** Test supported mobile browsers and viewport sizes.
- [ ] **M8-017** Complete keyboard and accessibility smoke tests.

### Manual Staging Script

- [ ] **M8-018** Register and log in as a new Manager.
- [ ] **M8-019** Create a store.
- [ ] **M8-020** Add an employee and assign limited capabilities.
- [ ] **M8-021** Create category, product, and variants.
- [ ] **M8-022** Enter purchased stock and verify movement history.
- [ ] **M8-023** Create a customer.
- [ ] **M8-024** Create a draft sale and edit its items.
- [ ] **M8-025** Complete the sale and verify exact stock deduction.
- [ ] **M8-026** Capture repeated wanted requests and verify aggregation/history.
- [ ] **M8-027** Verify dashboard values from the staged transactions.
- [ ] **M8-028** Confirm the limited employee is denied Manager-only actions.
- [ ] **M8-029** Cancel a draft and verify stock is unchanged.
- [ ] **M8-030** Verify logout and password recovery.

### Launch Preparation

- [ ] **M8-031** Restore the latest staging backup into a clean environment.
- [ ] **M8-032** Rehearse deployment rollback.
- [ ] **M8-033** Freeze and publish the v1 API schema.
- [ ] **M8-034** Publish user onboarding and support instructions.
- [ ] **M8-035** Assign monitoring, support, incident, and rollback owners.
- [ ] **M8-036** Record known non-blocking limitations.
- [ ] **M8-037** Obtain release approval.

### M8 Gate

- [ ] **M8-GATE** All automated and manual gates pass, operational ownership is
      assigned, and the MVP is approved for real store data.

---

## Immediate Work Queue

Start with these tasks:

1. `M0-001` — repository cleanup
2. `M0-002` — supported Python version
3. `M0-003` — dependency workflow
4. `M0-004` — runtime dependency manifest
5. `M0-005` — development dependency group
6. `M0-006` — lock file
7. `M0-007` — clean installation verification
8. `M0-008` — environment variable inventory
9. `M0-009` — `.env.example`
10. `M0-010` through `M0-013` — setup and verification documentation

Do not begin feature expansion in M4 until M1–M3 pass their gates.

## Post-MVP Epics

Keep these as epics until the MVP release. Break each into small tasks only when
it is prioritized:

- [ ] **P1** Suppliers and purchase orders
- [ ] **P2** Reorder suggestions
- [ ] **P3** Returns and refunds
- [ ] **P4** Customer campaigns and SMS notifications
- [ ] **P5** Barcode and QR scanning
- [ ] **P6** Import and export
- [ ] **P7** Multi-branch stores
- [ ] **P8** Financial and profit reporting
- [ ] **P9** Multi-currency support
- [ ] **P10** Advanced analytics and trends
- [ ] **P11** Soft deletion and archival policies
