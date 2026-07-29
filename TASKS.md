# Inventory SaaS — Small Task Breakdown

This is the simplified execution checklist for `ROADMAP.md` and
`TECHNICAL_HANDOVER_AND_REFACTOR_PLAN.md`. Tasks are ordered by dependency and
should be implemented with tests in the same coding session.

---

## ⚫ PHASE 0: Reproducible Project Baseline

### Task 0.1: Add Dependency Management
Create a project dependency manifest and lock file containing the current
runtime and development dependencies. Do not rely on the local `venv`.

### Task 0.2: Add Environment Documentation
Add `.env.example` with variable names and safe examples. Document PostgreSQL,
migration, server, test, lint, and schema-generation commands.

### Task 0.3: Add Formatting and Linting
Configure one formatter and linter, then fix existing issues in a standalone
mechanical change.

### Task 0.4: Add PostgreSQL CI
Run formatting, linting, `manage.py check`, migration-drift detection, tests,
and OpenAPI generation in CI against PostgreSQL. Make zero-error OpenAPI
validation a required check after Task 20.5 resolves the two known schema
errors.

---

## 🔴 PHASE 1: Critical Security Fixes (Do First)

> 🟡 Implementation is complete; tests are deferred to Phase 7.

### Task 1: Fix `validate_sale_stock()` Bug 🟡
**File**: `sales/services.py` line 83-108
**Problem**: Both the `if errors` block and `return True` are inside the loop,
so validation stops after the first item. Move both outside the loop.
```
# Current (buggy):
for item in items:
    validate...
    if errors:
        raise ValidationError(...)
    return True

# Fixed:
for item in items:
    validate...
if errors:
    raise ValidationError(...)
return True
```

### Task 1.1: Aggregate Duplicate Variants During Validation 🟡
If the same variant appears on multiple sale lines, validate the combined
quantity. Two individually valid lines must not be able to oversell stock.

### Task 2: Scope `SaleItemCreateView` to the Store 🟡
**File**: `sales/api/views.py` line 47-62
**Problem**: `Sale.objects.get(id=sale_id)` doesn't verify the sale belongs to the user's store.
```python
membership = get_current_membership(self.request.user)
sale = get_object_or_404(
    Sale.objects.filter(store=membership.store),
    id=self.kwargs["sale_id"],
)
```
Fetch through a scoped queryset rather than fetching globally and comparing
afterward.

### Task 3: Scope `SaleCompleteView` to the Store 🟡
**File**: `sales/api/views.py` line 73-85
Use the same scoped lookup as Task 2, adapted to the `request` and `sale_id`
arguments already supplied to `post()`.

### Task 4: Fix and Centralize Permission Resolution 🟡
**Files**: `stores/permissions.py`, `catalog/permissions.py`

`HasPermission` already queries `MembershipPermission` using the correct
relationship. Update it later to use `get_current_membership()`.

The confirmed lookup bug is in `CanCreateVariant`, which filters on the
nonexistent `permission_code` field. Use the real relationships:
```python
MembershipPermission.objects.filter(
    membership=membership,
    permission__code=self.permission_code,
).exists()
```

### Task 5: Fix `cansel_sale` Typo ✅
**File**: `sales/services.py` line 153
Rename `cansel_sale` → `cancel_sale`

### Task 5.1: Fix Reversed Sale Stock Updates 🟡
**Files**: `sales/services.py`, `inventory/services.py`

`create_inventory_movement()` adds its quantity to stock, but
`complete_sale()` currently passes a positive sale quantity. Pass a negative
quantity for sale movements and test that checkout decreases stock.

### Task 5.2: Make Checkout Concurrency-Safe 🟡
Inside one `transaction.atomic()` block:

- Lock the draft Sale with `select_for_update()`.
- Aggregate required quantity by variant.
- Lock affected variants in deterministic ID order.
- Validate from the locked rows.
- Write movements, update stock, then mark the sale completed.

Test simultaneous checkout for the final unit and simultaneous completion of
the same sale against PostgreSQL.

---

## 🟠 PHASE 2: Tenant Isolation Foundation

### Task 6: Create `get_current_membership()` Helper 🟡
**File**: `stores/services.py`
```python
def get_current_membership(user):
    """Return the user's only store membership."""
    try:
        return user.memberships.select_related("store").get()
    except StoreMembership.DoesNotExist:
        raise NoMembershipError
    except StoreMembership.MultipleObjectsReturned:
        raise MultipleMembershipsError
```
For the MVP, never choose an arbitrary or deterministic "first" store.

Also replace or remove the broken `get_user_stores()` implementation, which
currently fetches the first membership globally instead of filtering by user.

### Task 7: Replace All `.memberships.first()` Calls 🟡
Replace in these files:
- [x] `stores/api/views.py`
- [x] `stores/permissions.py`
- [x] `catalog/api/views.py`
- [x] `catalog/permissions.py`
- [x] `inventory/api/views.py`
- [x] `sales/api/views.py`
- [x] `customers/api/views.py`
- [x] `wanted/api/views.py`
- [x] `dashboard/api/views.py`
- [x] Remove or consolidate duplicate `dashboard/views.py`

### Task 7.1: Enforce One Membership Per User 🟡

- [x] Reject creation of a second store or membership through the API.
- [x] Add a data migration that handles existing duplicate memberships.
- [x] Add a database uniqueness constraint on `StoreMembership.user`.
- [ ] Test the rule at both API and database levels.

### Task 8: Scope Sale Customer Input to Store 🟡
**File**: `sales/api/serializers.py`

Set the customer relation queryset from the request's current store; also
validate ownership inside `create_sale()`.

### Task 9: Scope Sale Variant Input to Store
**File**: `sales/api/serializers.py`

Set the variant relation queryset from the request's current store; also
validate `variant.product.store == sale.store` inside `add_sale_item()`.

### Task 10: Scope Inventory Variant Input to Store
**File**: `inventory/api/serializers.py`

Set the relation queryset from the request's current store and repeat the
ownership check inside the inventory service.

### Task 10.1: Scope Wanted Relations to the Store
Scope Product and Customer relations to the current store in the serializer
and repeat ownership checks in `create_wanted()`.

### Task 10.2: Add Complete Tenant-Isolation Tests
For each endpoint accepting an object ID, test that Store A cannot read,
mutate, or reference Store B's Product, Variant, Customer, Sale, Inventory, or
Wanted data. Return `404` for inaccessible tenant objects.

---

## 🟡 PHASE 3: Permission System

### Task 11: Define Capability Catalog
Make `Permission.code` unique and seed these permissions with an idempotent
data migration or management command:
```
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

### Task 12: Apply Permission Classes to Views
Keep authentication and add the appropriate capability class:
- [ ] `catalog/api/views.py` → `CanManageCatalog`
- [ ] `inventory/api/views.py` → `CanViewInventory` / `CanManageInventory`
- [ ] `sales/api/views.py` → `CanCreateSale` / `CanViewSale`
- [ ] `dashboard/api/views.py` → `CanViewDashboard`
- [ ] `customers/api/views.py` → `CanManageCustomers`
- [ ] `wanted/api/views.py` → `CanManageWanted`
- [ ] `stores/api/views.py` → `CanManageMembers`

Manager has implicit full access. Seller/Admin are denied unless the Manager
assigns the required capability.

### Task 13: Restrict Membership Management
Only Managers should be able to:
- [ ] Add members
- [ ] Change roles
- [ ] Remove members
- [ ] Assign or revoke capabilities

Also prevent self-promotion, cross-store membership changes, and
removal/demotion of the store's final Manager. Add detail/update/remove and
capability-assignment APIs before claiming this task complete.

---

## 🟢 PHASE 4: Missing API Endpoints

### Task 14: Add Sale Detail Endpoint
**New**: `GET /api/v1/sales/{sale_id}/`
- File: Add to `sales/api/views.py` — `SaleDetailView(generics.RetrieveAPIView)`
- File: Add to `sales/api/serializers.py` — already have `SaleSerializer`

### Task 15: Add Sale Cancellation Endpoint
**New**: `POST /api/v1/sales/{sale_id}/cancel/`
- File: Add to `sales/api/views.py`
- Service: Rename `cansel_sale` → `cancel_sale` in `sales/services.py`

### Task 16: Add Customer CRUD Endpoints
**New**:
- `GET /api/v1/customers/{id}/` — Retrieve
- `PUT /api/v1/customers/{id}/` — Update
- `DELETE /api/v1/customers/{id}/` — Delete
- Files: `customers/api/views.py`

### Task 17: Add Category Detail/Update/Delete
**New**:
- `GET /api/v1/catalog/categories/{id}/`
- `PUT /api/v1/catalog/categories/{id}/`
- `DELETE /api/v1/catalog/categories/{id}/`
- Files: `catalog/api/views.py`

### Task 18: Add Product Search & Filtering
**Enhancement**:
- `?search=name` — search by product name
- `?category_id=id` — filter by category
- `?stock_status=in_stock|low_stock|out_of_stock`
- Files: `catalog/api/views.py`

### Task 19: Add Sales Filtering
**Enhancement**:
- `?status=draft|completed|cancelled`
- `?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- `?channel=store|instagram`
- Files: `sales/api/views.py`

### Task 20: Configure DRF Pagination
**File**: `config/settings.py`

Merge these keys into the existing `REST_FRAMEWORK` dictionary; do not replace
the authentication, permission, or schema configuration:
```python
REST_FRAMEWORK = {
    # existing settings...
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### Task 20.1: Complete Product and Variant CRUD
Add tenant-scoped Product detail/update/delete and Variant
list/detail/update/delete APIs. Stock must remain read-only in variant updates;
all stock changes go through inventory services.

### Task 20.2: Add Inventory Movement History
The current API lists inventory balances and only creates movements. Add a
tenant-scoped, paginated movement-history endpoint with product, variant, type,
creator, and validated date filters.

### Task 20.3: Fix Wanted-Request Data Loss
**Files**: `wanted/api/serializers.py`, `wanted/api/views.py`,
`wanted/services.py`

- [ ] Add Customer input to the serializer.
- [ ] Save `brand`.
- [ ] Save `created_by=user` on `WantedCustomerRequest`.
- [ ] Align `get_or_create` fields with the `(store, product_name, size)`
      database uniqueness constraint.
- [ ] Make `wanted_count` increments concurrency-safe.

### Task 20.4: Fix Sale Creation and Item Responses

- [ ] Resolve the mismatch where `payment_method` is optional in the serializer
      but required by the database. For the current MVP, make it required.
- [ ] Make `add_sale_item()` return the created SaleItem.
- [ ] Set `serializer.instance` so the response includes unit and final prices.
- [ ] Reject negative discounts and discounts above the line subtotal.

### Task 20.5: Complete OpenAPI Schemas
Add explicit request/response schema information for Dashboard and
SaleComplete. Reconcile generated paths with URL modules and reach zero schema
generation errors.

---

## 🔵 PHASE 5: Dashboard & Query Optimization

### Task 21: Move Stock Summation to SQL
**File**: `dashboard/services/inventory.py`
```python
# Instead of Python sum(), use:
ProductVariant.objects.filter(product__store=store).aggregate(
    total_stock=Sum('current_stock')
)['total_stock'] or 0
```

### Task 22: Add Select/Prefetch Related to Dashboard Queries
**Files**: `dashboard/services/*.py`

Measure query counts first. Combine compatible aggregates and add
`select_related()`/`prefetch_related()` only where Python dereferences related
objects. Do not blindly prefetch Sale items or select Store in `.values()` and
aggregate queries.

### Task 23: Make Low-Stock Threshold Configurable
**File**: `config/settings.py` — add `LOW_STOCK_THRESHOLD = 2`
**File**: `dashboard/services/inventory.py` — use setting instead of hardcoded `2`.

### Task 23.1: Validate Dashboard Dates and Metrics
Add a query serializer that validates ISO dates, `date_from <= date_to`, and a
maximum range. Define and test revenue, discounts, top products, stock,
low-stock, and wanted rankings in the configured business timezone.

---

## 🟣 PHASE 6: Production Preparation

### Task 24: Add Environment Variable Support
**Install**: `django-environ` or `python-decouple`
**File**: `.env.example` — list all required variables
**File**: settings modules — load secret key, database, debug, allowed hosts,
CORS/CSRF origins, timezone, and other environment-specific values.

### Task 25: Split Settings
Create:
- [ ] `config/settings/base.py` — common settings
- [ ] `config/settings/dev.py` — development overrides
- [ ] `config/settings/test.py` — test overrides
- [ ] `config/settings/prod.py` — production overrides

Renaming `config/settings.py` to a package also requires updating
`DJANGO_SETTINGS_MODULE` defaults in `manage.py`, `config/asgi.py`, and
`config/wsgi.py`.

### Task 26: Add Application Logging
Configure structured application/request logging and correlation IDs. Log
useful failures and security events rather than every service call. Redact
tokens, passwords, phone numbers, and secrets.

### Task 27: Add Rate Limiting
Add DRF throttles for authenticated and anonymous API traffic. To apply a
separate `login` rate to SimpleJWT, subclass `TokenObtainPairView`, attach
`ScopedRateThrottle`, set `throttle_scope = "login"`, and route the subclass.
Setting a `login` rate in settings alone does not throttle the stock SimpleJWT
view.

### Task 28: Apply Existing Password Validators
`AUTH_PASSWORD_VALIDATORS` are already configured. Call
`django.contrib.auth.password_validation.validate_password()` from
`RegisterSerializer`, and reuse it for password change/reset flows.

### Task 29: Add Database Indexes
Use realistic data and query plans before adding indexes. Review:
- [ ] `Sale(store, status, created_at)`
- [ ] `InventoryMovement(variant, created_at)`
- [ ] Dashboard date/status lookups

Foreign keys already receive indexes, and the Customer `(store, phone_number)`
unique constraint already creates a composite unique index. Do not add
duplicate indexes without evidence.

### Task 29.1: Add Remaining Production Security

- [ ] HTTPS redirect, secure cookies, trusted proxy handling, and reviewed HSTS
- [ ] Explicit CORS and trusted CSRF-origin handling
- [ ] Explicit JWT lifetimes, refresh-token blacklist, and logout
- [ ] Password change and reset
- [ ] Production WSGI/ASGI server and static-file handling
- [ ] `manage.py check --deploy` with no unresolved launch blocker

---

## ⚪ PHASE 7: Testing

### Task 30: Create Test Helpers/Factories
**File**: `tests/factories.py` or `tests/helpers.py`
- [ ] `create_user()`
- [ ] `create_store(user)`
- [ ] `create_product(store)`
- [ ] `create_variant(product)`
- [ ] `create_customer(store)`
- [ ] `create_sale(store, seller)`

Create these helpers before Tasks 1–29 and add tests alongside each
implementation. Phase 7 closes remaining coverage gaps; it is not the first
time tests are written.

### Task 31: Write Tenant Isolation Tests
**File**: `tests/test_tenant_isolation.py`
- [ ] Store A cannot see Store B products
- [ ] Store A cannot complete Store B sales
- [ ] Cross-store variant reference is rejected
- [ ] Every API accepting an object ID has a cross-store denial test

### Task 32: Write Sale Flow Tests
**File**: `tests/test_sale_flow.py`
- [ ] Create draft → Add items → Complete → Stock decreases
- [ ] Complete with insufficient stock → Error
- [ ] Later sale items and duplicate variant lines are validated
- [ ] Cancel draft → No stock change
- [ ] Double-complete protection
- [ ] Concurrent checkout cannot oversell

### Task 33: Write Permission Tests
**File**: `tests/test_permissions.py`
- [ ] Manager can do everything
- [ ] Seller without permission is denied
- [ ] Seller with permission is allowed

---

## 🟤 PHASE 8: Mobile-First Frontend

### Task 34: Select and Scaffold the Frontend
Choose the framework, TypeScript setup, package manager, repository location,
quality tooling, design tokens, shared components, and frontend CI build.

### Task 35: Build Authentication and Onboarding
Implement registration, login, logout, token refresh, password recovery,
protected routes, current-user/capability loading, store onboarding, and
mobile navigation.

### Task 36: Build Dashboard and Catalog
Implement Dashboard, Category, Product, and Variant screens with loading,
empty, validation, permission, pagination, search, and mobile states.

### Task 37: Build Inventory and Sales
Implement inventory balance/history, stock purchase/adjustment, sale
list/detail, fast mobile draft creation, item editing, checkout, and draft
cancellation.

### Task 38: Build Customers, Wanted, and Employees
Implement Customer CRUD/search, Wanted capture/ranking/history, employee
onboarding, and capability assignment.

### Task 39: Add Frontend Verification
Add accessibility and supported-mobile-browser checks plus end-to-end tests
for onboarding, stock entry, checkout, wanted capture, and employee denial.

---

## 🟢 PHASE 9: Deployment and Release

### Task 40: Package and Deploy Staging
Choose the host, add a reproducible non-root container/package, health and
readiness endpoints, PostgreSQL, static files, and automated staging deploy.

### Task 41: Add Observability and Recovery
Configure error tracking, uptime/error alerts, automated backups, retention,
and a tested restore procedure. Document deployment, migration, incident, and
rollback steps.

### Task 42: Run Release Gates
Against staging:

- [ ] Backend, frontend, tenant, permission, concurrency, and end-to-end tests
- [ ] At least 80% overall backend coverage with critical paths fully covered
- [ ] OpenAPI generation with zero errors
- [ ] No migration drift or launch-blocking deployment warning
- [ ] Dependency, secret, and static security scans
- [ ] Performance smoke tests for large lists, Dashboard, and checkout
- [ ] Manual onboarding → stock → sale → wanted → dashboard workflow
- [ ] Backup restoration and deployment rollback rehearsal

Release only after every gate passes.

---

## Suggested Execution Order

```
Phase 0: Tasks 0.1–0.4
     ↓
Create Task 30 test helpers
     ↓
Tenant base: Tasks 6 and 7.1
     ↓
Phase 1: Tasks 1–5.2 with tests
     ↓
Remaining Phase 2: Tasks 7–10.2 with tests
     ↓
Phase 3: Tasks 11–13 with tests
     ↓
Phase 4: Tasks 14–20.5 with tests
     ↓
Phase 5: Tasks 21–23.1
     ↓
Phase 6: Tasks 24–29.1
     ↓
Phase 7: Tasks 31–33 and coverage review
     ↓
Phase 8: Tasks 34–39
     ↓
Phase 9: Tasks 40–42
```

Do not use the previous 12–15 hour estimate. The work includes security
architecture, migrations, PostgreSQL concurrency tests, missing APIs,
frontend, deployment, and release verification. `ROADMAP.md` gives an
indicative 7–10 focused weeks for one experienced full-stack developer, but
actual effort depends on product and hosting decisions.

---

## Starting Point

Begin with **Task 0.1**. Ask Codex to implement one task at a time and verify
it before moving to the next.
