# 🏗️ InvoiceFlow - Complete Architecture Documentation (React Frontend)

## Table of Contents
1. [System Overview](#system-overview)
2. [High-Level Design (HLD)](#high-level-design-hld)
3. [Low-Level Design (LLD)](#low-level-design-lld)
4. [Architecture Diagrams](#architecture-diagrams)
5. [Component Architecture](#component-architecture)
6. [Data Flow Diagrams](#data-flow-diagrams)
7. [API Architecture](#api-architecture)
8. [Frontend Architecture](#frontend-architecture)
9. [Security Architecture](#security-architecture)
10. [Deployment Architecture](#deployment-architecture)
11. [Technology Stack](#technology-stack)
12. [API Endpoints](#api-endpoints)

---

## System Overview

InvoiceFlow is a **modern multi-tenant B2B SaaS invoice management application** with a **React frontend** and **Django REST Framework backend**. It enables businesses to create companies, manage clients/products, generate invoices, track payments, and export financial reports.

### Key Characteristics
- **Modern SPA Architecture**: React 19 with Vite for fast development
- **RESTful API**: Django REST Framework for backend services
- **Multi-Tenant**: Users can manage multiple companies with complete data isolation
- **Session-Based Auth**: Django sessions with CSRF protection
- **Real-Time State**: React state management with cross-tab synchronization
- **Responsive Design**: Mobile-first dark-themed UI

---

## High-Level Design (HLD)

### System Architecture Overview

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
│                     FRONTEND LAYER (React)                        │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              React Application (Vite)                      │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  App.jsx (Root Component)                         │    │    │
│  │  │  • Authentication State Management               │    │    │
│  │  │  • Company Context Management                    │    │    │
│  │  │  • Tab Session Management                        │    │    │
│  │  │  • Cross-Tab Synchronization                    │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Dashboard Component                            │    │    │
│  │  │  • Tab Navigation (Dashboard/Clients/Products)   │    │    │
│  │  │  • Company Switcher                              │    │    │
│  │  │  • Company Creation Form                        │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Feature Components                             │    │    │
│  │  │  • Customers.jsx (CRUD operations)              │    │    │
│  │  │  • Products.jsx (CRUD operations)               │    │    │
│  │  │  • Invoices.jsx (CRUD + PDF download)           │    │    │
│  │  │  • Payments.jsx (Record + List)                │    │    │
│  │  │  • Reports.jsx (Analytics + Export)             │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Auth Components                                │    │    │
│  │  │  • Login.jsx                                    │    │    │
│  │  │  • Signup.jsx                                   │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  API Service Layer                              │    │    │
│  │  │  • api.js (Centralized API calls)               │    │    │
│  │  │  • CSRF Token Management                        │    │    │
│  │  │  • Error Handling                               │    │    │
│  │  │  • Auth Failure Handling                        │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              State Management                             │    │
│  │  • React useState for component state                    │    │
│  │  • SessionStorage for tab persistence                    │    │
│  │  • BroadcastChannel for cross-tab sync                  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ Vite Dev Server  │
                    │  (Port 5173)     │
                    │  Proxy: /api →  │
                    │  localhost:8000  │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                      API GATEWAY LAYER                           │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Django REST Framework                        │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  API Endpoints (/api/)                            │    │    │
│  │  │  • /api/auth/csrf/ - CSRF token                   │    │    │
│  │  │  • /api/auth/login/ - User login                  │    │    │
│  │  │  • /api/auth/signup/ - User registration           │    │    │
│  │  │  • /api/auth/logout/ - User logout                 │    │    │
│  │  │  • /api/auth/user/ - Current user info             │    │    │
│  │  │  • /api/companies/ - Company CRUD                 │    │    │
│  │  │  • /api/customers/ - Customer CRUD                │    │    │
│  │  │  • /api/products/ - Product CRUD                 │    │    │
│  │  │  • /api/invoices/ - Invoice CRUD + PDF            │    │    │
│  │  │  • /api/payments/ - Payment CRUD                  │    │    │
│  │  │  • /api/reports/ - Analytics & Export             │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Serializers (DRF)                              │    │    │
│  │  │  • UserSerializer                               │    │    │
│  │  │  • CompanySerializer                            │    │    │
│  │  │  • CustomerSerializer                           │    │    │
│  │  │  • ProductSerializer                            │    │    │
│  │  │  • InvoiceSerializer                            │    │    │
│  │  │  • PaymentSerializer                            │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                           │
├─────────────────────────────┼────────────────────────────────────┤
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Django Views (api_views.py)                   │    │
│  │  • Authentication logic                                 │    │
│  │  • Multi-tenant data isolation                          │    │
│  │  • Company context management                           │    │
│  │  • Invoice calculations (subtotal, tax, total)            │    │
│  │  • Payment tracking & status updates                      │    │
│  │  • Transaction safety (atomic operations)                  │    │
│  │  • Row locking for concurrent payments                    │    │
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
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Models: Company, Membership, Customer, Product,   │    │    │
│  │  │          Invoice, InvoiceItem, Payment, User       │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
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
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Tables: auth_user, myapp_company,                 │    │    │
│  │  │          myapp_membership, myapp_customer,         │    │    │
│  │  │          myapp_product, myapp_invoice,              │    │    │
│  │  │          myapp_invoiceitem, myapp_payment          │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  • ACID compliance                                          │    │
│  │  • Foreign key constraints                                 │    │
│  │  • Unique constraints                                      │    │
│  │  • Indexes for performance                                  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Low-Level Design (LLD)

### 1. Authentication Flow

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. Open App
       ▼
┌─────────────────────────┐
│  React App (App.jsx)     │
│  - Check sessionStorage  │
│  - Validate tab session  │
│  - Check BroadcastChannel│
└──────┬──────────────────┘
       │
       │ 2. No session?
       ▼
┌─────────────────────────┐
│  Login Component        │
│  - Email/Password form  │
└──────┬──────────────────┘
       │
       │ 3. Submit login
       ▼
┌─────────────────────────┐
│  api.loginUser()        │
│  - POST /api/auth/login/│
│  - Send CSRF token      │
└──────┬──────────────────┘
       │
       │ 4. Django API
       ▼
┌─────────────────────────┐
│  api_login() view       │
│  - Authenticate user    │
│  - Create session       │
│  - Get company context  │
└──────┬──────────────────┘
       │
       │ 5. Return user data
       ▼
┌─────────────────────────┐
│  React App             │
│  - Set tab session      │
│  - Set user state      │
│  - Set company context │
│  - Broadcast LOGOUT to  │
│    other tabs          │
└──────┬──────────────────┘
       │
       │ 6. Render Dashboard
       ▼
┌─────────────────────────┐
│  Dashboard Component   │
│  - Show company data    │
│  - Enable navigation   │
└─────────────────────────┘
```

### 2. Tab Session Management

```
┌─────────────────────────────────────────────────────────┐
│           TAB SESSION MANAGEMENT (App.jsx)                │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Session Storage Keys:                                    │
│  • invoiceflow_tab_session                               │
│    { tabId, userId, username, authenticatedAt }          │
│  • invoiceflow_tab_unloaded_at                           │
│    timestamp of beforeunload event                       │
│                                                           │
│  Window Name:                                             │
│  • window.name = tabId (unique per tab)                  │
│                                                           │
│  Validation Logic:                                        │
│  1. Check sessionStorage for session                      │
│  2. Validate window.name matches session.tabId            │
│  3. Check for browser restart (unloaded_at > 20s)        │
│  4. If valid, restore session                            │
│  5. If invalid, call clearTabSession()                    │
│                                                           │
│  Cross-Tab Synchronization:                               │
│  • BroadcastChannel('invoiceflow_auth_channel')            │
│  • On logout: broadcast { type: 'LOGOUT' }                │
│  • On receive: clear session, redirect to login           │
│                                                           │
│  Auth Failure Handling:                                   │
│  • api.js sets authFailureHandler                        │
│  • On 401/403: call handler                              │
│  • Handler clears session and redirects                   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 3. API Request Flow

```
┌─────────────┐
│  Component │
│  (e.g.,    │
│  Customers)│
└──────┬──────┘
       │
       │ 1. Call API function
       ▼
┌─────────────────────────┐
│  api.js (apiRequest)   │
│  - Get CSRF token       │
│  - Add X-CSRFToken      │
│  - Add credentials      │
└──────┬──────────────────┘
       │
       │ 2. Fetch request
       ▼
┌─────────────────────────┐
│  Django Middleware      │
│  - CSRF validation     │
│  - Session validation  │
│  - Authentication      │
└──────┬──────────────────┘
       │
       │ 3. API View
       ▼
┌─────────────────────────┐
│  api_views.py          │
│  - Check permissions   │
│  - Get company context │
│  - Execute business    │
│    logic               │
└──────┬──────────────────┘
       │
       │ 4. Django ORM
       ▼
┌─────────────────────────┐
│  PostgreSQL            │
│  - Query data          │
│  - Return results      │
└──────┬──────────────────┘
       │
       │ 5. Return JSON
       ▼
┌─────────────────────────┐
│  React Component       │
│  - Update state        │
│  - Re-render UI        │
└─────────────────────────┘
```

### 4. Company Switching Flow

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. Select company
       ▼
┌─────────────────────────┐
│  Dashboard.jsx         │
│  - handleSwitchCompany()│
└──────┬──────────────────┘
       │
       │ 2. Call API
       ▼
┌─────────────────────────┐
│  api.switchCompany()    │
│  - POST /api/companies/ │
│    {id}/switch/         │
└──────┬──────────────────┘
       │
       │ 3. Django API
       ▼
┌─────────────────────────┐
│  api_switch_company()  │
│  - Update session      │
│  - Get new company     │
│  - Return context      │
└──────┬──────────────────┘
       │
       │ 4. Update state
       ▼
┌─────────────────────────┐
│  Dashboard.jsx         │
│  - setCurrentCompany()  │
│  - setCompanies()      │
│  - Refresh all data    │
└──────┬──────────────────┘
       │
       │ 5. Re-render
       ▼
┌─────────────────────────┐
│  All Components        │
│  - Re-fetch data       │
│  - Update UI           │
└─────────────────────────┘
```

---

## Architecture Diagrams

### 1. Component Hierarchy Diagram

```
App.jsx (Root)
├── Auth State Management
│   ├── Tab Session Management
│   ├── Cross-Tab Synchronization
│   └── Auth Failure Handling
│
├── Auth Container
│   ├── Login.jsx
│   └── Signup.jsx
│
└── Dashboard.jsx (Authenticated)
    ├── Header
    │   ├── Brand Title
    │   ├── Company Switcher
    │   └── User Menu
    │
    ├── Sidebar Navigation
    │   ├── Dashboard Tab
    │   ├── Customers Tab
    │   ├── Products Tab
    │   ├── Invoices Tab
    │   ├── Payments Tab
    │   └── Reports Tab
    │
    ├── Content Area
    │   ├── CompanyRequiredState.jsx
    │   │   └── Company Creation Form
    │   │
    │   ├── Customers.jsx
    │   │   ├── Customer List
    │   │   ├── Add Customer Form
    │   │   ├── Edit Customer Form
    │   │   └── Delete Confirmation
    │   │
    │   ├── Products.jsx
    │   │   ├── Product List
    │   │   ├── Add Product Form
    │   │   ├── Edit Product Form
    │   │   └── Delete Confirmation
    │   │
    │   ├── Invoices.jsx
    │   │   ├── Invoice List (with filters)
    │   │   ├── Create Invoice Form
    │   │   ├── Invoice Details View
    │   │   ├── PDF Download
    │   │   └── Cancel Invoice
    │   │
    │   ├── Payments.jsx
    │   │   ├── Payment List (with filters)
    │   │   ├── Record Payment Form
    │   │   └── Payment Details
    │   │
    │   └── Reports.jsx
    │       ├── Summary Dashboard
    │       ├── Date Range Picker
    │       └── PDF Export
    │
    └── Footer
```

### 2. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    DATA FLOW ARCHITECTURE                   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐                                        │
│  │   User       │                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 1. User Action (click, form submit)            │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │ React Event  │                                        │
│  │   Handler    │                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 2. Update Component State                         │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │   useState   │                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 3. Call API Service                             │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │  api.js      │                                        │
│  │  (apiRequest)│                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 4. HTTP Request (with CSRF token)               │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │ Django API   │                                        │
│  │  (api_views) │                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 5. Business Logic                               │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │ Django ORM   │                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 6. Database Query                               │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │ PostgreSQL   │                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 7. Return Data                                   │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │ JSON Response│                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 8. Update State                                   │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │   useState   │                                        │
│  └──────┬───────┘                                        │
│         │                                                 │
│         │ 9. Re-render Component                           │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │   UI Update │                                        │
│  └──────────────┘                                        │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 3. State Management Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  STATE MANAGEMENT                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  App.jsx State:                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  user: User | null                               │    │
│  │  currentCompany: Company | null                 │    │
│  │  companies: Company[]                           │    │
│  │  view: 'login' | 'signup' | 'authenticated'     │    │
│  │  loading: boolean                               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  Dashboard.jsx State:                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │  activeTab: 'dashboard' | 'clients' | ...       │    │
│  │  showCreateForm: boolean                        │    │
│  │  [form fields for company creation]             │    │
│  │  switchingId: number | null                     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  Component-Level State:                                   │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Customers.jsx:                                 │    │
│  │    customers: Customer[]                         │    │
│  │    showAddForm: boolean                         │    │
│  │    editingCustomer: Customer | null             │    │
│  │    searchQuery: string                          │    │
│  │                                                   │    │
│  │  Products.jsx:                                   │    │
│  │    products: Product[]                          │    │
│  │    showAddForm: boolean                         │    │
│  │    editingProduct: Product | null               │    │
│  │    searchQuery: string                          │    │
│  │                                                   │    │
│  │  Invoices.jsx:                                   │    │
│  │    invoices: Invoice[]                          │    │
│  │    showCreateForm: boolean                       │    │
│  │    selectedInvoice: Invoice | null               │    │
│  │    filters: { search, status }                  │    │
│  │                                                   │    │
│  │  Payments.jsx:                                   │    │
│  │    payments: Payment[]                          │    │
│  │    showRecordForm: boolean                       │    │
│  │    filters: { search, method, invoiceId }       │    │
│  │                                                   │    │
│  │  Reports.jsx:                                    │    │
│  │    summaryData: object                           │    │
│  │    dateRange: { start, end }                    │    │
│  │    selectedPreset: string                       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  Session Storage:                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  invoiceflow_tab_session                        │    │
│  │  invoiceflow_tab_unloaded_at                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  BroadcastChannel:                                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │  invoiceflow_auth_channel                       │    │
│  │  Events: { type: 'LOGOUT' }                     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Frontend Components

#### 1. App.jsx (Root Component)
**Responsibilities**:
- Authentication state management
- Tab session persistence
- Cross-tab synchronization
- Route management (login/signup/dashboard)
- Global error handling

**Key Functions**:
- `getTabSession()` - Retrieve and validate tab session
- `setTabSession()` - Create new tab session
- `clearTabSession()` - Clear session on logout
- `handleLoginSuccess()` - Process successful login
- `handleSignupSuccess()` - Process successful signup
- `handleLogout()` - Process logout with cross-tab sync

#### 2. Dashboard.jsx (Main Container)
**Responsibilities**:
- Tab navigation management
- Company switching
- Company creation
- User menu
- Layout management

**Key Functions**:
- `handleCreateCompany()` - Create new company
- `handleSwitchCompany()` - Switch active company
- `handleNavigateToCreateCompany()` - Navigate to company creation

#### 3. Feature Components

**Customers.jsx**:
- List customers with search
- Add/Edit/Delete customers
- Form validation
- API integration

**Products.jsx**:
- List products with search
- Add/Edit/Delete products
- Form validation
- API integration

**Invoices.jsx**:
- List invoices with filters (search, status)
- Create new invoices
- View invoice details
- Download PDF
- Cancel invoices
- API integration

**Payments.jsx**:
- List payments with filters
- Record new payments
- View payment details
- API integration

**Reports.jsx**:
- Display financial summary
- Date range filtering
- Preset filters (today, this month, etc.)
- Export to PDF
- API integration

#### 4. Auth Components

**Login.jsx**:
- Email/password form
- Validation
- API integration
- Switch to signup

**Signup.jsx**:
- Full name/email/password form
- Validation
- API integration
- Switch to login

#### 5. Utility Components

**CompanyRequiredState.jsx**:
- Display when user has no companies
- Prompt to create first company
- Company creation form

### Backend Components

#### 1. API Views (api_views.py)

**Authentication Endpoints**:
- `api_health_check()` - Health check
- `api_csrf_token()` - CSRF token generation
- `api_signup()` - User registration
- `api_login()` - User authentication
- `api_logout()` - User logout
- `api_current_user()` - Current user info

**Company Endpoints**:
- `api_create_company()` - Create company
- `api_switch_company()` - Switch active company

**Customer Endpoints**:
- `api_customers_list_create()` - List/Create customers
- `api_customer_detail()` - Get/Update/Delete customer

**Product Endpoints**:
- `api_products_list_create()` - List/Create products
- `api_product_detail()` - Get/Update/Delete product

**Invoice Endpoints**:
- `api_invoices_list_create()` - List/Create invoices
- `api_invoice_detail()` - Get/Update/Delete invoice
- `api_invoice_cancel()` - Cancel invoice
- `api_invoice_pdf()` - Download PDF (reuses view)

**Payment Endpoints**:
- `api_payments_list_create()` - List/Create payments
- `api_payment_detail()` - Get/Update/Delete payment

**Report Endpoints**:
- `api_reports_summary()` - Financial summary
- `api_export_report()` - Export PDF (reuses view)

#### 2. Serializers (serializers.py)

**Purpose**: Convert Django models to JSON and vice versa

**Serializers**:
- `UserSerializer` - User data
- `CompanySerializer` - Company data
- `CustomerSerializer` - Customer data
- `ProductSerializer` - Product data
- `InvoiceSerializer` - Invoice data
- `InvoiceItemSerializer` - Invoice item data
- `PaymentSerializer` - Payment data

---

## API Architecture

### API Endpoint Structure

```
/api/
├── health/                    [GET]  - Health check
├── auth/
│   ├── csrf/                 [GET]  - Get CSRF token
│   ├── signup/               [POST] - Register user
│   ├── login/                [POST] - Login user
│   ├── logout/               [POST] - Logout user
│   └── user/                 [GET]  - Current user info
├── companies/
│   ├── /                     [POST] - Create company
│   └── <id>/switch/          [POST] - Switch company
├── customers/
│   ├── /                     [GET, POST] - List/Create
│   └── <id>/                 [GET, PUT, DELETE] - Detail
├── products/
│   ├── /                     [GET, POST] - List/Create
│   └── <id>/                 [GET, PUT, DELETE] - Detail
├── invoices/
│   ├── /                     [GET, POST] - List/Create
│   ├── <id>/                 [GET, PUT, DELETE] - Detail
│   ├── <id>/cancel/          [POST] - Cancel invoice
│   └── <id>/pdf/             [GET]  - Download PDF
├── payments/
│   ├── /                     [GET, POST] - List/Create
│   └── <id>/                 [GET, PUT, DELETE] - Detail
└── reports/
    ├── summary/              [GET]  - Financial summary
    └── export/               [GET]  - Export PDF
```

### Request/Response Format

**Standard Success Response**:
```json
{
  "id": 1,
  "name": "Company Name",
  "email": "company@example.com",
  ...
}
```

**Standard Error Response**:
```json
{
  "error": "Error message description"
}
```

**Paginated List Response**:
```json
[
  { "id": 1, "name": "Item 1", ... },
  { "id": 2, "name": "Item 2", ... }
]
```

### Authentication Flow

1. **Initial Load**:
   ```
   GET /api/auth/csrf/ → Set CSRF cookie
   ```

2. **Login**:
   ```
   POST /api/auth/login/
   Headers: X-CSRFToken: <token>
   Body: { "email": "...", "password": "..." }
   Response: { "user": {...}, "current_company": {...}, "companies": [...] }
   ```

3. **Authenticated Request**:
   ```
   GET /api/customers/
   Headers: X-CSRFToken: <token> (for POST/PUT/DELETE)
   Cookies: sessionid=<session>
   Response: [{...}, {...}]
   ```

4. **Logout**:
   ```
   POST /api/auth/logout/
   Headers: X-CSRFToken: <token>
   Response: { "message": "Logged out successfully" }
   ```

---

## Frontend Architecture

### Directory Structure

```
frontend/
├── public/
│   ├── favicon.svg
│   └── icons.svg
├── src/
│   ├── assets/
│   │   └── hero.png
│   ├── components/
│   │   ├── CompanyRequiredState.jsx
│   │   ├── Customers.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Invoices.jsx
│   │   ├── Login.jsx
│   │   ├── Payments.jsx
│   │   ├── Products.jsx
│   │   ├── Reports.jsx
│   │   └── Signup.jsx
│   ├── services/
│   │   └── api.js
│   ├── App.css
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
├── index.html
├── package.json
├── vite.config.js
└── vercel.json
```

### Component Communication

```
App.jsx (Parent)
    │
    ├── Props: user, currentCompany, companies
    │
    ├── Callbacks: onCompanyUpdated, onLogout
    │
    └── Dashboard.jsx (Child)
            │
            ├── Props: user, currentCompany, companies
            │
            ├── Callbacks: onCompanyUpdated, onLogout
            │
            └── Feature Components (Grandchildren)
                    │
                    ├── Props: currentCompany
                    │
                    └── API calls (via api.js)
```

### State Management Strategy

**Local State (useState)**:
- Component-specific state (forms, modals, filters)
- Temporary UI state (loading, errors)

**Session Storage**:
- Tab session persistence
- Cross-tab session validation

**BroadcastChannel**:
- Cross-tab logout synchronization
- Session invalidation propagation

**No Global State Management**:
- No Redux/Context API needed
- Props drilling for shared state
- Simple and maintainable

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────────┐
│              SECURITY LAYERS                             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  1. FRONTEND SECURITY                              │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Tab session validation                  │    │    │
│  │  │  • Window.name matching                    │    │    │
│  │  │  • Browser restart detection               │    │    │
│  │  │  • Cross-tab logout sync                   │    │    │
│  │  │  • Auth failure handling                   │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  2. CSRF PROTECTION                                │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • CSRF cookie on every request          │    │    │
│  │  │  • X-CSRFToken header on POST/PUT/DELETE  │    │    │
│  │  │  • Django middleware validation           │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  3. SESSION AUTHENTICATION                         │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Django session middleware             │    │    │
│  │  │  • Session cookie (sessionid)            │    │    │
│  │  │  • @login_required decorator              │    │    │
│  │  │  • Session expiration handling            │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  4. API PERMISSIONS                                │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • DRF permission classes                 │    │    │
│  │  │  • IsAuthenticated for protected routes   │    │    │
│  │  │  • AllowAny for auth endpoints             │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  5. COMPANY DATA ISOLATION                        │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Session-based company context          │    │    │
│  │  │  • Filter queries by current_company      │    │    │
│  │  │  • Membership validation                  │    │    │
│  │  │  • No cross-company data access            │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  6. DATABASE SECURITY                               │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Parameterized queries (ORM)           │    │    │
│  │  │  • Foreign key constraints               │    │    │
│  │  │  • Unique constraints                     │    │    │
│  │  │  • Transaction atomicity                   │    │    │
│  │  │  • Row locking for payments                │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Security Features

**Frontend**:
- Tab session validation prevents session hijacking
- Cross-tab logout prevents stale sessions
- Window.name matching prevents tab duplication
- Browser restart detection expires old sessions

**Backend**:
- CSRF protection on all state-changing requests
- Session-based authentication
- Company-level data isolation
- Row locking for concurrent payments
- SQL injection prevention (ORM)

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
│  │  │  React Dev Server (Vite)                │    │    │
│  │  │  Port: 5173                               │    │    │
│  │  │  Proxy: /api → localhost:8000           │    │    │
│  │  │  Hot Module Replacement (HMR)           │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           │ HTTP                           │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Django Development Server                        │    │
│  │  Port: 8000                                       │    │
│  │  DEBUG = True                                     │    │
│  │  Local PostgreSQL                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  PostgreSQL (Local)                               │    │
│  │  Database: invoiceflow                             │    │
│  └─────────────────────────────────────────────────┘    │
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
│  │  Frontend (Vercel)                                 │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  React Build (Static Files)              │    │    │
│  │  │  • Optimized bundle                      │    │    │
│  │  │  • Minified JS/CSS                       │    │    │
│  │  │  • Asset optimization                    │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  Vercel Edge Network                    │    │    │
│  │  │  • Global CDN                            │    │    │
│  │  │  • SSL/TLS                              │    │    │
│  │  │  • Edge rewrites to backend              │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           │ HTTPS                          │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Backend (Render)                                  │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  Gunicorn Application Server            │    │    │
│  │  │  • Multiple workers                      │    │    │
│  │  │  • DEBUG = False                         │    │    │
│  │  │  • ALLOWED_HOSTS configured              │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  WhiteNoise (Static Files)               │    │    │
│  │  │  • Static file serving                   │    │    │
│  │  │  • Gzip compression                     │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  PostgreSQL (Render/Supabase)                     │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  • Managed database                     │    │    │
│  │  │  • Automated backups                    │    │    │
│  │  │  • High availability                     │    │    │
│  │  │  • SSL connections                       │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Deployment Configuration

**Vercel Configuration (vercel.json)**:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend-render-url.com/api/:path*"
    }
  ]
}
```

**Django Production Settings**:
```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

---

## Technology Stack

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | React | 19.3.1 | UI framework |
| Build Tool | Vite | 8.3.5 | Build tool & dev server |
| Language | JavaScript | ES6+ | Application logic |
| Styling | CSS3 | - | Custom dark theme |
| HTTP Client | Fetch API | Native | API requests |
| State | React Hooks | - | State management |

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.10+ | Backend logic |
| Framework | Django | 5.0.1 | Web framework |
| API Framework | Django REST Framework | Latest | REST API |
| Database | PostgreSQL | 12+ | Relational database |
| ORM | Django ORM | Built-in | Database abstraction |
| PDF Generation | ReportLab | Latest | Invoice PDFs |
| Static Files | WhiteNoise | Latest | Static file serving |

### Development Tools

| Tool | Purpose |
|------|---------|
| npm | Package management |
| Vite | Build tool & dev server |
| oxlint | Linting |
| pip | Python package management |
| virtualenv | Environment isolation |
| git | Version control |

---

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health/` | Public | Health check |
| GET | `/api/auth/csrf/` | Public | Get CSRF token |
| POST | `/api/auth/signup/` | Public | Register user |
| POST | `/api/auth/login/` | Public | Login user |
| POST | `/api/auth/logout/` | Authenticated | Logout user |
| GET | `/api/auth/user/` | Authenticated | Current user info |

### Company Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/companies/` | Authenticated | Create company |
| POST | `/api/companies/<id>/switch/` | Authenticated | Switch company |

### Customer Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/customers/` | Authenticated | List customers |
| POST | `/api/customers/` | Authenticated | Create customer |
| GET | `/api/customers/<id>/` | Authenticated | Get customer |
| PUT | `/api/customers/<id>/` | Authenticated | Update customer |
| DELETE | `/api/customers/<id>/` | Authenticated | Delete customer |

### Product Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/products/` | Authenticated | List products |
| POST | `/api/products/` | Authenticated | Create product |
| GET | `/api/products/<id>/` | Authenticated | Get product |
| PUT | `/api/products/<id>/` | Authenticated | Update product |
| DELETE | `/api/products/<id>/` | Authenticated | Delete product |

### Invoice Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/invoices/` | Authenticated | List invoices |
| POST | `/api/invoices/` | Authenticated | Create invoice |
| GET | `/api/invoices/<id>/` | Authenticated | Get invoice |
| PUT | `/api/invoices/<id>/` | Authenticated | Update invoice |
| DELETE | `/api/invoices/<id>/` | Authenticated | Delete invoice |
| POST | `/api/invoices/<id>/cancel/` | Authenticated | Cancel invoice |
| GET | `/api/invoices/<id>/pdf/` | Authenticated | Download PDF |

### Payment Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/payments/` | Authenticated | List payments |
| POST | `/api/payments/` | Authenticated | Record payment |
| GET | `/api/payments/<id>/` | Authenticated | Get payment |
| PUT | `/api/payments/<id>/` | Authenticated | Update payment |
| DELETE | `/api/payments/<id>/` | Authenticated | Delete payment |

### Report Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/reports/summary/` | Authenticated | Financial summary |
| GET | `/api/reports/export/` | Authenticated | Export PDF |

---

## Conclusion

InvoiceFlow is a modern, well-architected full-stack application with:

### Architecture Highlights

1. **Modern SPA**: React 19 with Vite for fast development and optimized production builds
2. **RESTful API**: Django REST Framework for clean, scalable backend services
3. **Session-Based Auth**: Secure Django sessions with CSRF protection
4. **Multi-Tenant**: Complete company isolation with easy switching
5. **Tab Session Management**: Advanced session handling with cross-tab synchronization
6. **Responsive Design**: Mobile-first dark-themed UI
7. **Production-Ready**: Configured for Vercel (frontend) and Render (backend)

### Key Design Decisions

- **No Global State**: Simple props drilling instead of Redux/Context
- **Session Storage**: Tab persistence without complex state management
- **BroadcastChannel**: Cross-tab logout synchronization
- **CSRF Protection**: Security-first approach for all state changes
- **Company Context**: Session-based company switching for multi-tenancy

### Scalability

The architecture supports:
- Horizontal scaling (stateless API with session storage)
- Vertical scaling (optimized database queries)
- CDN distribution (static frontend assets)
- Multi-region deployment (Vercel Edge Network)

---

**Document Version**: 2.0 (React Frontend)  
**Last Updated**: November 17, 2026  
**Author**: InvoiceFlow Development Team
