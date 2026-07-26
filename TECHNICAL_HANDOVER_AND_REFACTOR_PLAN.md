# Inventory SaaS
# Technical Handover & Refactoring Plan

Version: MVP Pre-Production Review


# 1. Project Overview

Inventory SaaS is a multi-tenant inventory and sales management platform built with Django REST Framework.

The platform targets small retail businesses, especially sneaker stores.

Main goals:

- Real-time inventory management
- Product and size management
- Sales tracking
- Customer data collection
- Demand intelligence through wanted products
- Business analytics dashboard


## Core Business Problem

Small stores usually manage inventory and customer demand mentally.

Problems:

- Unknown real-time stock
- Lost sales due to unavailable information
- No historical sales data
- No demand analysis
- Difficult employee onboarding


## Main Workflows

Registration:

User
→ Store Creation
→ Membership
→ Product Setup
→ Inventory Entry
→ Sales
→ Analytics


Demand workflow:

Customer requests unavailable product
→ Wanted Product tracking
→ Demand aggregation
→ Procurement decision


---

# 2. Current Architecture


## Django Apps


users

Responsible for:

- Authentication
- Custom User model


stores

Responsible for:

- Store tenant
- Membership
- Roles
- Employee permissions


catalog

Responsible for:

- Category
- Product
- ProductVariant


inventory

Responsible for:

- Stock movements
- Inventory history


sales

Responsible for:

- Sale
- SaleItem
- Checkout workflow


customers

Responsible for:

- Customer information


wanted

Responsible for:

- Customer demand tracking


dashboard

Responsible for:

- Analytics aggregation



## Architecture Pattern

Current architecture:

Models
↓
Serializers
↓
Views
↓
Services


The project follows:

"Thin Views, Fat Services"


This is a good architectural direction.


---

# 3. Database Design


## Tenant Structure


Current:


User

|

StoreMembership

|

Store


All business data belongs to Store.


Example:

Store

├── Products

├── Inventory

├── Sales

├── Customers

├── Wanted Products



---

# 4. Current Multi-Tenant Problems


## Critical Issue: Tenant Isolation


Current implementation relies on:


request.user.memberships.first()


Problem:

A user can theoretically belong to multiple stores.

Using first() creates undefined behavior.


Example:


User

Store A

Store B


Application does not know which store is active.


---

## Required MVP Decision


For MVP:


ONE USER = ONE STORE MEMBERSHIP


Reason:

- Simplifies architecture
- Removes ambiguity
- Matches current code
- Reduces security risks


Future versions can support multi-store users.


---

# 5. Security Issues


## Critical: Cross Tenant Data Access


Affected areas:


Sales

Problem:


Sale.objects.get(id=id)


without checking:


sale.store == current_store


Risk:

User from Store A can modify Store B sales.


---

## Inventory Mutation Risk


A user may potentially manipulate inventory belonging to another store through:

- ProductVariant references
- Sale items
- Inventory movements


All related objects must validate ownership.


---

# 6. Authentication


Current:

JWT Authentication

Library:

djangorestframework-simplejwt


Flow:


Login

↓

Access Token

↓

Authenticated API Requests



Missing:

- Logout blacklist
- Token revocation
- Password policy
- Rate limiting
- Password reset



---

# 7. Authorization System


## Current Roles


Manager

Store owner

Full access


Seller

Physical store salesperson


Admin

Online/social media salesperson



---

## Current Problem


Permission tables exist:


MembershipPermission


but runtime authorization does not properly use them.


Current state:


Database Permission System

+

Role System


but no complete enforcement.



---

# 8. Target Permission Architecture


## Manager


Manager always has:

FULL ACCESS


No database permission checks required.


---

## Seller/Admin


Access controlled by:


MembershipPermission


Example:


seller:

Can create sale

Cannot modify products

Cannot manage inventory


admin:

Can manage online sales

Cannot manage stock


---

# 9. Critical Bugs


## validate_sale_stock()


Current problem:


Only first SaleItem is validated.


Incorrect:


for item in items:

    validate

    return True



Correct:


for item in items:

    validate


after loop:

return True



---

# 10. Inventory Correctness


## Current Risk


Stock exists in two places:


ProductVariant.current_stock


and


InventoryMovement history



This creates source-of-truth ambiguity.


Recommended:


InventoryMovement is audit source.

ProductVariant.current_stock is cached value.


All changes must go through services.



---

# 11. Concurrency Problems


Current stock checking is vulnerable to race conditions.


Example:


Stock = 1


Seller A sells

Seller B sells


Both pass validation.


Result:

Negative inventory.


Recommended:


Use:


select_for_update()


inside stock modification transactions.



---

# 12. Sales Workflow


Correct workflow:


Create Sale

(status=draft)


↓

Add SaleItems


↓

Calculate total


↓

Complete Sale


↓

Validate stock


↓

Create InventoryMovement


↓

Decrease stock


↓

Mark completed



---

# 13. Required Refactoring Roadmap


## Phase 1 - Security Foundation


Priority: CRITICAL


Tasks:


1. Remove memberships.first()


2. Implement Current Store Context


Example:


get_current_store(request)


3. Add tenant scoped querysets


4. Secure all object lookup


5. Rewrite permission system



---

## Phase 2 - Inventory and Sales Stability


Tasks:


- Fix stock validation
- Review cancel sale logic
- Add inventory locking
- Validate variant ownership
- Improve transaction boundaries



---

## Phase 3 - MVP Completion


Missing:


- Sale detail API
- Sale cancellation API
- Customer CRUD
- Permission management API
- Pagination
- Filtering
- Search



---

## Phase 4 - Production Preparation


Tasks:


- Environment variables
- Production settings split
- Logging
- Monitoring
- Error handling
- CI/CD
- Automated tests



---

# 14. Recommended Target Structure


core/

├── tenant/

│   ├── context.py

│   ├── mixins.py

│   └── permissions.py


Each app:


app/

├── models.py

├── services.py

├── permissions.py

└── api/

    ├── views.py

    ├── serializers.py

    └── urls.py



---

# 15. Testing Requirements


Critical tests:


## Tenant Isolation

User cannot access another store data.


## Permissions

Seller cannot create product.

Manager can.


## Inventory

Cannot sell unavailable stock.


## Sales

Completing sale decreases stock correctly.


## Wanted

Duplicate requests aggregate correctly.



---

# 16. Current Project Evaluation


Architecture:

7/10


Business Model:

8/10


Implementation:

5/10


Production Readiness:

2/10



## Current Health Score


3.5 / 10


Reason:


The project has a strong domain model and good architectural foundation.

However:

- Tenant isolation is incomplete
- Permissions are not enforced
- Inventory correctness has risks
- Testing is missing
- Production configuration is incomplete


The project is NOT production ready.

The next development phase must focus on:

Security → Authorization → Tenant Isolation → Stability

before adding new business features.