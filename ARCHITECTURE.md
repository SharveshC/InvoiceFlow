# 🏗️ InvoiceFlow - Complete Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Architecture](#component-architecture)
4. [Database Schema](#database-schema)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Technology Stack](#technology-stack)
9. [API Endpoints](#api-endpoints)
10. [Unique Selling Points](#unique-selling-points)

---

## System Overview

InvoiceFlow is a **multi-tenant B2B SaaS invoice management application** built with Django and PostgreSQL. It enables businesses to create companies, manage clients/products, generate invoices, track payments, and export financial reports.

### Key Characteristics
- **Multi-Tenant**: Users can manage multiple companies with complete data isolation
- **Role-Based**: Owner, Admin, Staff roles for team collaboration
- **Self-Hostable**: No vendor lock-in, complete data control
- **GST-Ready**: Built-in GST number support for Indian market
- **Real-Time**: Live dashboard metrics and payment tracking

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Desktop    │  │    Mobile    │  │    Tablet    │         │
│  │  (Browser)   │  │  (Browser)   │  │  (Browser)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│           │                 │                 │                  │
│           └─────────────────┴─────────────────┘                  │
│                             │                                    │
│                      HTTPS / HTTP                                │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                     PRESENTATION LAYER                            │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Django Templates (DTL)                       │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐       │    │
│  │  │   index    │  │  dashboard │  │  invoices  │       │    │
│  │  │   login    │  │  clients   │  │  products  │       │    │
│  │  │  signup    │  │  payments  │  │   reports  │       │    │
│  │  └────────────┘  └────────────┘  └────────────┘       │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                      APPLICATION LAYER                             │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    Django Views                             │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Authentication: home, login, signup, logout      │  │    │
│  │  │  Company: create_company, switch_company          │  │    │
│  │  │  Clients: clients, add_client, edit_client,       │  │    │
│  │  │           delete_client                             │  │    │
│  │  │  Products: products, add_product, edit_product,    │  │    │
│  │  │            delete_product                           │  │    │
│  │  │  Invoices: invoices, create_invoice,               │  │    │
│  │  │            invoice_details, cancel_invoice,        │  │    │
│  │  │            generate_invoice_pdf                     │  │    │
│  │  │  Payments: payments, record_payment                │  │    │
│  │  │  Reports: export_report                             │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Business Logic Layer                          │    │
│  │  • Multi-tenant data isolation                            │    │
│  • Company context management                                 │    │
│  • Invoice calculations (subtotal, tax, discount, total)      │    │
│  • Payment tracking & status updates                           │    │
│  • Overdue detection                                          │    │
│  • Transaction safety (atomic operations)                       │    │
│  • Row locking for concurrent payments                         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                       DATA ACCESS LAYER                            │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   Django ORM                                 │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Models: Company, Membership, Customer, Product,   │  │    │
│  │  │          Invoice, InvoiceItem, Payment, User       │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │  • Query optimization (select_related, prefetch_related) │    │
│  │  • Aggregations (Sum, Count)                              │    │
│  │  • Constraints (unique, foreign key)                     │    │
│  │  • Transactions (atomic)                                  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                      DATA STORAGE LAYER                           │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    PostgreSQL 12+                          │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Tables: auth_user, myapp_company,                 │  │    │
│  │  │          myapp_membership, myapp_customer,         │  │    │
│  │  │          myapp_product, myapp_invoice,              │  │    │
│  │  │          myapp_invoiceitem, myapp_payment          │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │  • ACID compliance                                          │    │
│  │  • Foreign key constraints                                 │    │
│  │  • Unique constraints                                      │    │
│  │  • Indexes for performance                                  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                    EXTERNAL SERVICES                              │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   ReportLab  │  │  Email (Future)│  │ Payment (Future)│       │
│  │  PDF Generation│  │   Brevo/SendGrid│  │  Stripe/Razorpay│      │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Authentication Module

```
┌─────────────────────────────────────────────────────────┐
│                  AUTHENTICATION COMPONENT                │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │   Signup     │───▶│  User Model   │                   │
│  └──────────────┘    └──────────────┘                   │
│         │                      │                            │
│         │                      ▼                            │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │    Login     │───▶│  Session     │                   │
│  └──────────────┘    │  Management  │                   │
│         │            └──────────────┘                   │
│         │                      │                            │
│         ▼                      ▼                            │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │   Logout     │    │  @login_required                 │
│  └──────────────┘    │  Decorator   │                   │
│                      └──────────────┘                   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Features**:
- Email-based authentication
- Password validation (Django validators)
- Session management
- CSRF protection
- Login required decorator for protected routes

---

### 2. Multi-Tenant Company Management

```
┌─────────────────────────────────────────────────────────┐
│              MULTI-TENANT COMPANY COMPONENT               │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │              User (Django Auth)                   │    │
│  └─────────────────────────────────────────────────┘    │
│                        │                                  │
│                        │ 1:N                               │
│                        ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Membership Table                     │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  user_id (FK)                             │    │    │
│  │  │  company_id (FK)                          │    │    │
│  │  │  role (OWNER/ADMIN/STAFF)                 │    │    │
│  │  │  UniqueConstraint(user, company)          │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                        │                                  │
│                        │ 1:N                               │
│                        ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │                Company Table                       │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  name, email, phone, address, gst_number │    │    │
│  │  │  All child data linked via company_id    │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                        │                                  │
│                        │ 1:N                               │
│         ┌──────────────┼──────────────┐                    │
│         ▼              ▼              ▼                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │ Customer │  │ Product  │  │ Invoice  │                │
│  └──────────┘  └──────────┘  └──────────┘                │
│                                                           │
│  Session: current_company_id stored for context          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Data Isolation**:
- All data (customers, products, invoices) linked to company_id
- Views filter by current_company
- Session-based company switching
- No cross-company data access

---

### 3. Invoice Generation Component

```
┌─────────────────────────────────────────────────────────┐
│              INVOICE GENERATION COMPONENT                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  User Input                                               │
│     │                                                     │
│     ▼                                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Form Validation Layer                    │    │
│  │  • Invoice number uniqueness check                │    │
│  │  • Customer validation                              │    │
│  │  • Date validation (issue ≤ due)                   │    │
│  │  • Product validation                              │    │
│  │  • Quantity/price validation                        │    │
│  └─────────────────────────────────────────────────┘    │
│     │                                                     │
│     ▼                                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │         Calculation Engine                         │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  For each invoice item:                  │    │    │
│  │  │    line_subtotal = quantity × unit_price   │    │    │
│  │  │    line_tax = line_subtotal × (tax/100)    │    │    │
│  │  │    line_total = line_subtotal + line_tax   │    │    │
│  │  │                                            │    │    │
│  │  │  Invoice totals:                           │    │    │
│  │  │    subtotal = Σ line_subtotal              │    │    │
│  │  │    total_tax = Σ line_tax                  │    │    │
│  │  │    total = subtotal + total_tax - discount │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│     │                                                     │
│     ▼                                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │         Transaction Block (Atomic)               │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  1. Create Invoice record                │    │    │
│  │  │  2. Create InvoiceItem records            │    │    │
│  │  │  3. Rollback on any error                 │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│     │                                                     │
│     ▼                                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │              PDF Generation (ReportLab)           │    │
│  │  • Company header                                 │    │
│  │  • Customer details                               │    │
│  │  • Invoice items table                           │    │
│  │  • Totals summary                                 │    │
│  │  • Payment summary                               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

### 4. Payment Processing Component

```
┌─────────────────────────────────────────────────────────┐
│              PAYMENT PROCESSING COMPONENT                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  User selects invoice → enters payment amount            │
│     │                                                     │
│     ▼                                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │         Pre-flight Validation (No Lock)           │    │
│  │  • Invoice exists and belongs to company          │    │
│  │  • Invoice not cancelled                           │    │
│  │  • Payment amount > 0                              │    │
│  │  • Payment date valid                              │    │
│  └─────────────────────────────────────────────────┘    │
│     │                                                     │
│     ▼                                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │     Transaction Block with Row Lock               │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  SELECT invoice FOR UPDATE                 │    │    │
│  │  │  (prevents concurrent modifications)       │    │    │
│  │  │                                            │    │    │
│  │  │  Calculate already paid:                  │    │    │
│  │  │    paid_amount = Σ payments.amount        │    │    │
│  │  │                                            │    │    │
│  │  │  Calculate remaining:                      │    │    │
│  │  │    remaining = invoice.total - paid_amount │─┐    │
│  │  │                                            │ │    │
│  │  │  Validate:                                  │ │    │
│  │  │    remaining > 0 (not fully paid)         │ │    │
│  │  │    amount ≤ remaining (no overpayment)     │ │    │
│  │  │                                            │ │    │
│  │  │  Create Payment record                     │ │    │
│  │  │                                            │ │    │
│  │  │  Update invoice status:                     │ │    │
│  │  │    if new_paid >= total: status = PAID     │ │    │
│  │  │    elif due_date < today: status = OVERDUE │ │    │
│  │  │    else: status = SENT                      │ │    │
│  │  │                                            │ │    │
│  │  │  Commit transaction                         │ │    │
│  │  └─────────────────────────────────────────┘ │ │    │
│  └─────────────────────────────────────────────────┘ │ │    │
│     │                                                   │ │    │
│     ▼                                                   │ │    │
│  ┌─────────────────────────────────────────────────┐ │ │    │
│  │         Error Handling                            │◀┘ │    │
│  │  • Overpayment error                              │    │    │
│  │  • Already fully paid error                       │    │    │
│  │  • Cancelled invoice error                        │    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Concurrency Safety**:
- Row-level locking with `select_for_update()`
- Pre-flight validation outside transaction
- Atomic transaction for payment creation
- Status update within same transaction

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE SCHEMA                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐                                           │
│  │     User         │                                           │
│  │  (Django Auth)    │                                           │
│  │  ┌──────────────┐│                                           │
│  │  │ id (PK)       ││                                           │
│  │  │ username      ││                                           │
│  │  │ email         ││                                           │
│  │  │ password      ││                                           │
│  │  │ first_name    ││                                           │
│  │  └──────────────┘│                                           │
│  └────────┬─────────┘                                           │
│           │ 1:N                                                 │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │   Membership     │                                           │
│  │  ┌──────────────┐│                                           │
│  │  │ user_id (FK) ││◀─────────────────┐                       │
│  │  │ company_id   ││                  │                       │
│  │  │ role          ││                  │                       │
│  │  │ created_at    ││                  │                       │
│  │  └──────────────┘│                  │                       │
│  └────────┬─────────┘                  │                       │
│           │ 1:N                         │                         │
│           ▼                             │                         │
│  ┌──────────────────┐                   │                         │
│  │    Company       │                   │                         │
│  │  ┌──────────────┐│                   │                         │
│  │  │ id (PK)       ││                   │                         │
│  │  │ name          ││                   │                         │
│  │  │ email         ││                   │                         │
│  │  │ phone         ││                   │                         │
│  │  │ address       ││                   │                         │
│  │  │ gst_number    ││                   │                         │
│  │  │ created_at    ││                   │                         │
│  │  │ updated_at    ││                   │                         │
│  │  └──────────────┘│                   │                         │
│  └────────┬─────────┘                   │                         │
│           │                             │                         │
│           ├─────────────────────────────┼─────────────────────┐   │
│           │ 1:N                         │ 1:N                 │   │
│           ▼                             ▼                     │   │
│  ┌──────────────────┐         ┌──────────────────┐           │   │
│  │    Customer      │         │    Product       │           │           │
│  │  ┌──────────────┐│         │  ┌──────────────┐│           │   │
│  │  │ id (PK)       ││         │  │ id (PK)       ││           │   │
│  │  │ company_id    ││         │  │ company_id    ││           │   │
│  │  │ name          ││         │  │ name          ││           │   │
│  │  │ email         ││         │  │ description   ││           │   │
│  │  │ phone         ││         │  │ price         ││           │   │
│  │  │ address       ││         │  │ tax           ││           │   │
│  │  │ gst_number    ││         │  │ created_at    ││           │   │
│  │  │ created_at    ││         │  │ updated_at    ││           │   │
│  │  │ updated_at    ││         │  └──────────────┘│           │   │
│  │  └──────────────┘│         └────────┬─────────┘           │   │
│  └────────┬─────────┘                  │                     │   │
│           │                             │                     │   │
│           │ 1:N                         │                     │   │
│           ▼                             │                     │   │
│  ┌──────────────────┐                  │                     │   │
│  │     Invoice      │                  │                     │   │
│  │  ┌──────────────┐│                  │                     │   │
│  │  │ id (PK)       ││                  │                     │   │
│  │  │ company_id    ││                  │                     │   │
│  │  │ customer_id   ││◀─────────────────┘                     │   │
│  │  │ invoice_number││                                        │   │
│  │  │ issue_date    ││                                        │   │
│  │  │ due_date      ││                                        │   │
│  │  │ status        ││                                        │   │
│  │  │ subtotal      ││                                        │   │
│  │  │ tax_amount    ││                                        │   │
│  │  │ discount_amount││                                       │   │
│  │  │ total         ││                                        │   │
│  │  │ notes         ││                                        │   │
│  │  │ created_at    ││                                        │   │
│  │  │ updated_at    ││                                        │   │
│  │  └──────────────┘│                                        │   │
│  └────────┬─────────┘                                        │   │
│           │ 1:N                                            │   │
│           │                                                │   │
│           ├────────────────┐                               │   │
│           │                │                               │   │
│           ▼                ▼                               │   │
│  ┌──────────────────┐  ┌──────────────────┐                 │   │
│  │   InvoiceItem   │  │     Payment      │                 │   │
│  │  ┌──────────────┐│  │  ┌──────────────┐│                 │   │
│  │  │ id (PK)       ││  │  │ id (PK)       ││                 │   │
│  │  │ invoice_id    ││◀─┘  │ invoice_id    ││◀─────────────────┘   │
│  │  │ product_id    ││─────│ amount         ││                     │
│  │  │ quantity      ││     │ payment_method││                     │
│  │  │ unit_price    ││     │ payment_date  ││                     │
│  │  │ tax           ││     │ notes         ││                     │
│  │  │ discount      ││     │ created_at    ││                     │
│  │  │ line_total    ││     └──────────────┘│                     │
│  │  └──────────────┘│                      │                     │
│  └──────────────────┘                      └─────────────────────┘   │
│                                                                   │
│  Constraints:                                                       │
│  • Membership: UniqueConstraint(user, company)                     │
│  • Invoice: UniqueConstraintcompany, invoice_number)              │
│  • All foreign keys: ON_DELETE=CASCADE/PROTECT as appropriate      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Table Details

#### Company
```sql
CREATE TABLE myapp_company (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(254) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    gst_number VARCHAR(15),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Membership
```sql
CREATE TABLE myapp_membership (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES myapp_company(id) ON DELETE CASCADE,
    role VARCHAR(10) DEFAULT 'STAFF',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, company_id)
);
```

#### Invoice
```sql
CREATE TABLE myapp_invoice (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES myapp_company(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES myapp_customer(id) ON DELETE PROTECT,
    invoice_number VARCHAR(50) NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'DRAFT',
    subtotal DECIMAL(12,2) DEFAULT 0,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    discount_amount DECIMAL(12,2) DEFAULT 0,
    total DECIMAL(12,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, invoice_number)
);
```

---

## Data Flow Diagrams

### Invoice Creation Flow

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. Click "Create Invoice"
       ▼
┌─────────────────────────┐
│  create_invoice view    │
│  - Get current_company  │
│  - Get customers list   │
│  - Get products list    │
└──────┬──────────────────┘
       │
       │ 2. Render form
       ▼
┌─────────────────────────┐
│  create_invoice.html    │
│  - Customer dropdown    │
│  - Product selector     │
│  - Dynamic item rows    │
└──────┬──────────────────┘
       │
       │ 3. Submit form
       ▼
┌─────────────────────────┐
│  POST create_invoice    │
│  - Validate inputs      │
│  - Calculate totals    │
│  - Check uniqueness     │
└──────┬──────────────────┘
       │
       │ 4. Atomic transaction
       ▼
┌─────────────────────────┐
│  Database Transaction  │
│  1. Create Invoice     │
│  2. Create InvoiceItems│
│  3. Commit             │
└──────┬──────────────────┘
       │
       │ 5. Success
       ▼
┌─────────────────────────┐
│  Redirect to invoices   │
└─────────────────────────┘
```

### Payment Recording Flow

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. Click "Record Payment"
       ▼
┌─────────────────────────┐
│  record_payment view    │
│  - Get current_company  │
│  - Get unpaid invoices  │
│  - Annotate paid_amount │
└──────┬──────────────────┘
       │
       │ 2. Render form
       ▼
┌─────────────────────────┐
│  record_payment.html    │
│  - Invoice dropdown     │
│  - Show remaining bal   │
│  - Payment method sel   │
└──────┬──────────────────┘
       │
       │ 3. Submit payment
       ▼
┌─────────────────────────┐
│  POST record_payment    │
│  - Pre-flight validation│
│  - Check not cancelled  │
└──────┬──────────────────┘
       │
       │ 4. Atomic + Row Lock
       ▼
┌─────────────────────────┐
│  Transaction Block      │
│  1. SELECT FOR UPDATE  │
│  2. Calculate remaining │
│  3. Validate amount     │
│  4. Create Payment      │
│  5. Update status       │
│  6. Commit              │
└──────┬──────────────────┘
       │
       │ 5. Success
       ▼
┌─────────────────────────┐
│  Redirect to payments    │
└─────────────────────────┘
```

### Dashboard Data Flow

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. Access /dashboard/
       ▼
┌─────────────────────────┐
│  @login_required check  │
│  - Verify authentication│
└──────┬──────────────────┘
       │
       │ 2. Get company context
       ▼
┌─────────────────────────┐
│  get_user_company_      │
│  context()              │
│  - Get user memberships │
│  - Get companies list   │
│  - Get current_company  │
└──────┬──────────────────┘
       │
       │ 3. Calculate metrics
       ▼
┌─────────────────────────┐
│  Dashboard calculations │
│  - Total revenue       │
│  - Paid invoices count │
│  - This month revenue  │
│  - Pending amount       │
│  - Overdue amount       │
│  - Recent invoices      │
└──────┬──────────────────┘
       │
       │ 4. Render dashboard
       ▼
┌─────────────────────────┐
│  after_login.html       │
│  - Display stats cards  │
│  - Recent invoices table│
│  - Quick actions        │
└─────────────────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SECURITY LAYERS                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  1. AUTHENTICATION LAYER                           │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Django Authentication System        │    │    │
│  │  │  • Password hashing (PBKDF2)           │    │    │
│  │  │  • Session management                 │    │    │
│  │  │  • @login_required decorator           │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  2. AUTHORIZATION LAYER                            │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Company-level data isolation        │    │    │
│  │  │  • User-company membership check        │    │    │
│  │  │  • Role-based access (OWNER/ADMIN/STAFF)│    │    │
│  │  │  • Session-based company context       │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  3. INPUT VALIDATION LAYER                        │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Django form validation              │    │    │
│  │  │  • Decimal validation for money       │    │    │
│  │  │  • Date validation                      │    │    │
│  │  │  • Email validation                     │    │    │
│  │  │  • Required field checks               │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │|
│  │  4. CSRF PROTECTION LAYER                          │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • CSRF tokens on all POST forms       │    │    │
│  │  │  • Middleware validation               │    │    │
│  │  │  • SameSite cookie attribute           │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  5. DATABASE SECURITY LAYER                         │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Parameterized queries (ORM)         │    │    │
│  │  │  • Foreign key constraints            │    │    │
│  │  │  • Unique constraints                  │    │    │
│  │  │  • ProtectedError handling             │    │    │
│  │  │  • Transaction atomicity               │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  6. BUSINESS LOGIC SECURITY                       │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Row locking for concurrent payments │    │    │
│  │  │  • Overpayment prevention              │    │    │
│  │  │  • Invoice status rules                │    │    │
│  │  │  • Company ownership verification      │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────────────────────┐
│              DEVELOPMENT ENVIRONMENT                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Developer Machine                                 │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  Python 3.10+                             │    │    │
│  │  │  Django 5.0.1                             │    │    │
│  │  │  PostgreSQL (local)                        │    │    │
│  │  │  manage.py runserver                       │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Local PostgreSQL                                │    │
│  │  • Database: invoiceflow                         │    │
│  │  • Connection: localhost:5432                   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  Configuration: .env file with local DB credentials       │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Production Environment (Recommended)

```
┌─────────────────────────────────────────────────────────┐
│              PRODUCTION ENVIRONMENT                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Load Balancer (Nginx/HAProxy)                    │    │
│  │  • SSL/TLS termination                            │    │
│  │  • Static file serving                            │    │
│  │  • Reverse proxy to Gunicorn                       │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Application Server (Gunicorn)                    │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  Django application                        │    │    │
│  │  │  Multiple workers                         │    │    │
│  │  │  DEBUG = False                             │    │    │
│  │  │  ALLOWED_HOSTS configured                 │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  PostgreSQL Database (Managed/Cloud)              │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • High availability (replication)        │    │    │
│  │  │  • Automated backups                      │    │    │
│  │  │  • Connection pooling                     │    │    │
│  │  │  • SSL connections                        │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Static Files Storage                             │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • AWS S3 / DigitalOcean Spaces          │    │    │
│  │  │  • CDN distribution (CloudFlare)          │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Optional: Redis Cache                            │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Session storage                         │    │    │
│  │  │  • Query result caching                   │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Docker Deployment (Alternative)

```
┌─────────────────────────────────────────────────────────┐
│              DOCKER COMPOSE DEPLOYMENT                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  docker-compose.yml                                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │  services:                                        │    │
│  │    db:                                            │    │
│  │      image: postgres:15                          │    │
│  │      volumes:                                     │    │
│  │        - postgres_data:/var/lib/postgresql/data   │    │
│  │    web:                                           │    │
│  │      build: .                                    │    │
│  │      command: gunicorn InvoiceFlow.wsgi          │    │
│  │      ports:                                      │    │
│  │        - "8000:8000"                             │    │
│  │      depends_on:                                 │    │
│  │        - db                                       │    │
│  │    nginx:                                         │    │
│  │      image: nginx                                │    │
│  │      ports:                                      │    │
│  │        - "80:80"                                 │    │
│  │      volumes:                                     │    │
│  │        - ./nginx.conf:/etc/nginx/nginx.conf       │    │
│  │  volumes:                                         │    │
│  │    postgres_data:                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.10+ | Core language |
| Framework | Django | 5.0.1 | Web framework |
| Database | PostgreSQL | 12+ | Relational database |
| ORM | Django ORM | Built-in | Database abstraction |
| PDF Generation | ReportLab | Latest | Invoice PDFs |
| Environment | python-dotenv | Latest | Config management |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Templates | Django Templates (DTL) | Server-side rendering |
| Styling | CSS3 | Custom dark theme |
| JavaScript | Vanilla JS | Form interactions |
| Icons | Unicode/Text | Lightweight icons |

### Development Tools

| Tool | Purpose |
|------|---------|
| pip | Package management |
| virtualenv | Environment isolation |
| git | Version control |
| manage.py | Django CLI |

---

## API Endpoints

### Public Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Landing page |
| GET | `/login/` | Login form |
| POST | `/login/` | Authenticate user |
| GET | `/signup/` | Signup form |
| POST | `/signup/` | Register user |

### Protected Endpoints (@login_required)

#### Company Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dashboard/` | Main dashboard |
| POST | `/logout/` | Logout user |
| GET/POST | `/create-company/` | Create company |
| GET | `/switch-company/<id>/` | Switch active company |

#### Client Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/clients/` | List clients |
| GET/POST | `/clients/add/` | Add client |
| GET/POST | `/clients/<id>/edit/` | Edit client |
| POST | `/clients/<id>/delete/` | Delete client |

#### Product Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/products/` | List products |
| GET/POST | `/products/add/` | Add product |
| GET/POST | `/products/<id>/edit/` | Edit product |
| POST | `/products/<id>/delete/` | Delete product |

#### Invoice Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/invoices/` | List invoices |
| GET/POST | `/invoices/create/` | Create invoice |
| GET | `/invoices/<id>/` | Invoice details |
| POST | `/invoices/<id>/cancel/` | Cancel invoice |
| GET | `/invoices/<id>/pdf/` | Download PDF |

#### Payment Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/payments/` | List payments |
| GET/POST | `/payments/record/` | Record payment |

#### Reports
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/reports/export/` | Export financial report |

---

## Unique Selling Points

### What Makes InvoiceFlow Unique?

#### 1. **Multi-Company Management**
- **Competitors**: Most platforms support single business entity
- **InvoiceFlow**: Users can create and manage multiple companies with instant switching
- **Use Case**: Freelancers with multiple businesses, agencies managing multiple client companies

#### 2. **Simplicity Over Complexity**
- **Competitors**: FreshBooks, QuickBooks include full accounting (bookkeeping, taxes, payroll)
- **InvoiceFlow**: Focused purely on invoicing - no accounting bloat
- **Use Case**: Businesses that just need invoicing, not full accounting suite

#### 3. **Self-Hostable & Privacy-Focused**
- **Competitors**: All major competitors are SaaS-only (data on their servers)
- **InvoiceFlow**: Can be self-hosted on your own infrastructure
- **Use Case**: Privacy-conscious businesses, regulated industries, data sovereignty requirements

#### 4. **No Monthly Fees**
- **Competitors**: 
  - FreshBooks: $23-70/month
  - QuickBooks: $38/month+
  - Xero: $20/month+
  - Zoho Invoice: Free up to 500 invoices, then paid
- **InvoiceFlow**: One-time setup, no recurring costs
- **Use Case**: Cost-conscious small businesses, startups

#### 5. **GST-Ready for Indian Market**
- **Competitors**: Global platforms have generic tax support
- **InvoiceFlow**: Built-in GST number fields for companies and customers
- **Use Case**: Indian businesses with GST compliance requirements

#### 6. **Modern Dark-Themed UI**
- **Competitors**: Traditional, often dated interfaces
- **InvoiceFlow**: Modern, responsive dark theme designed for 2026+
- **Use Case**: Users preferring modern aesthetics, reduced eye strain

#### 7. **Real-Time Dashboard**
- **Competitors**: Dashboards often require refresh or are delayed
- **InvoiceFlow**: Live metrics calculated on every dashboard load
- **Use Case**: Business owners needing up-to-date financial overview

#### 8. **Lightweight Performance**
- **Competitors**: Heavy JavaScript frameworks, slow load times
- **InvoiceFlow**: Vanilla JavaScript, minimal dependencies, fast performance
- **Use Case**: Users on slower connections, mobile users

### Feature Comparison Matrix

| Feature | InvoiceFlow | FreshBooks | Zoho Invoice | QuickBooks | Wave |
|---------|-------------|------------|--------------|------------|-------|
| **Multi-Company** | ✅ Native | ❌ | ❌ | ❌ | ❌ |
| **Self-Hostable** | ✅ Yes | ❌ | ❌ | ❌ | ❌ |
| **Monthly Cost** | ✅ $0 | $23-70 | Free (500 inv) | $38+ | Free |
| **GST Support** | ✅ Built-in | ⚠️ Generic | ⚠️ Generic | ⚠️ Generic | ❌ |
| **Accounting** | ❌ No | ✅ Full | ⚠️ Basic | ✅ Full | ⚠️ Basic |
| **Time Tracking** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes | ❌ |
| **Recurring Invoices** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes | ❌ |
| **Expense Tracking** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Multi-Currency** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Payment Gateway** | ⚠️ Future | ✅ Integrated | ✅ Integrated | ✅ Integrated | ✅ Integrated |
| **API Access** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes | ❌ |
| **Mobile App** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes | ❌ |
| **Integrations** | ❌ No | 100+ | Zoho suite | 1000+ | Limited |
| **Data Export** | ✅ PDF | ✅ Multiple | ✅ Multiple | ✅ Multiple | ✅ CSV |
| **Custom Branding** | ⚠️ Basic | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

### Target Market

**InvoiceFlow is ideal for**:
1. Small businesses in India with GST requirements
2. Freelancers managing multiple business entities
3. Privacy-conscious users wanting data control
4. Cost-conscious businesses avoiding monthly fees
5. Users preferring simple, focused tools over complex suites
6. Businesses needing self-hosted solutions for compliance

**InvoiceFlow is NOT ideal for**:
1. Businesses needing full accounting (bookkeeping, taxes, payroll)
2. Businesses with international clients needing multi-currency
3. Businesses requiring time tracking and project billing
4. Businesses needing extensive third-party integrations
5. Businesses requiring mobile apps

---

## Future Roadmap

### Phase 1: Core Enhancements (Next 3 months)
- [ ] Recurring invoices
- [ ] Email invoice delivery
- [ ] Quote/estimate workflow
- [ ] Credit notes
- [ ] Multi-currency support

### Phase 2: Integrations (3-6 months)
- [ ] Payment gateway integration (Stripe, Razorpay)
- [ ] Email notifications (Brevo/SendGrid)
- [ ] Calendar integration
- [ ] REST API for third-party access

### Phase 3: Advanced Features (6-12 months)
- [ ] Time tracking
- [ ] Expense tracking
- [ ] Advanced reporting
- [ ] Team collaboration features
- [ ] Client portal

### Phase 4: Enterprise (12+ months)
- [ ] White-labeling
- [ ] SSO integration
- [ ] Advanced permissions
- [ ] Audit logs
- [ ] Multi-region deployment

---

## Conclusion

InvoiceFlow is a well-architected, focused invoice management SaaS that differentiates itself through:

1. **Multi-tenant architecture** with company isolation
2. **Simplicity** - focused on invoicing, not accounting
3. **Self-hostability** - complete data control
4. **Cost-effectiveness** - no monthly fees
5. **Modern UX** - dark theme, responsive design
6. **GST readiness** - tailored for Indian market

The architecture is production-ready with proper security, data validation, transaction safety, and scalable design patterns. While it lacks some features of mature competitors (recurring invoices, time tracking, integrations), its focus on core invoicing functionality makes it an excellent choice for its target market.

---

**Document Version**: 1.0  
**Last Updated**: October 28, 2026  
**Author**: InvoiceFlow Development Team
