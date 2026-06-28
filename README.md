# Inventory SaaS

A mobile-first inventory and sales management platform built for small retail businesses and online shops.

## Problem

Many small businesses still manage inventory using memory, paper notes, spreadsheets, or messaging apps. As inventory grows, this leads to:

* Lost sales due to incorrect stock information
* Dependency on the owner's knowledge
* Lack of sales and demand insights
* Difficult onboarding of new sellers
* No visibility into products customers wanted but could not buy

## Solution

Inventory SaaS centralizes inventory, sales, customer, and demand data into a single platform.

The goal is simple:

> Turn business knowledge into structured and actionable data.

## MVP Features

### Inventory Management

* Product management
* Product variants (sizes)
* Real-time stock visibility
* Inventory adjustments

### Sales Tracking

* Sales registration
* Customer tracking
* Payment methods
* Sales channels

### Demand Tracking

Record products customers requested but were unavailable.

### Dashboard

* Daily sales
* Revenue
* Low-stock products
* Most requested products

## Architecture

Multi-tenant SaaS

Each account owns a single store and all related data.

Core entities:

* Store
* User
* Category
* Product
* ProductVariant
* Customer
* Sale
* SaleItem
* InventoryMovement
* Request

## Target Audience

* Sneaker stores
* Small fashion retailers
* Online shops
* Small businesses with 1–10 employees

## Tech Stack

### Backend

* Django
* Django REST Framework
* PostgreSQL

### Frontend

* 

## Project Status

Currently in MVP development.

## Roadmap

### Phase 1

* Inventory
* Sales
* Requests
* Dashboard

### Phase 2

* CRM
* Customer campaigns
* SMS notifications

### Phase 3

* Suppliers
* Purchase management
* Reorder suggestions

### Phase 4

* Multi-branch support
* Financial reporting
* Profit analysis

## License

MIT License
