

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

Frontend implementation is still under development.

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

## Roadmap

### Phase 1 — MVP

* [ ] Inventory management
* [ ] Product variants
* [ ] Inventory movements
* [ ] Sales registration
* [ ] Customer tracking
* [ ] Product request tracking
* [ ] Dashboard
* [ ] Low-stock insights
* [ ] Demand insights

### Phase 2 — Customer Relationship Management

* [ ] CRM features
* [ ] Customer segmentation
* [ ] Customer campaigns
* [ ] SMS notifications
* [ ] Purchase history insights

### Phase 3 — Purchasing

* [ ] Supplier management
* [ ] Purchase orders
* [ ] Purchase management
* [ ] Reorder suggestions
* [ ] Supplier history

### Phase 4 — Business Intelligence

* [ ] Multi-branch support
* [ ] Financial reporting
* [ ] Profit analysis
* [ ] Advanced sales analytics
* [ ] Demand forecasting

---

## Why I Am Building This

The purpose of this project is not only to build a CRUD inventory application.

The broader goal is to explore how a small business can turn everyday operational activity into useful structured data.

A sale provides sales data.

An inventory adjustment provides stock history.

A customer request provides demand data.

When these events are connected, the system can gradually provide better answers to questions such as:

```text
What is selling?

What is running out?

What are customers asking for?

What products are causing lost sales?

What should the business consider restocking?
```

That is the direction behind Inventory SaaS.

---

## Development Notes

This repository represents an active work in progress.

You may encounter:

```text
unfinished features
changing APIs
database migrations
refactoring
questionable commits
bugs that definitely looked impossible five minutes earlier
```

👷 **Developer at work.**

---

## License

This project is licensed under the MIT License.
