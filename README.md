# 🚀 InvoiceFlow

[![React](https://img.shields.io/badge/React-19.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.3-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Django](https://img.shields.io/badge/Django-5.0.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.15-red?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![WCAG AA](https://img.shields.io/badge/WCAG_2.1-AA_Compliant-success?style=for-the-badge&logo=w3c)](https://www.w3.org/WAI/standards-guidelines/wcag/)
[![Vercel](https://img.shields.io/badge/Vercel-Frontend-black?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)
[![Render](https://img.shields.io/badge/Render-Backend-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)

---

## 💡 About InvoiceFlow

**InvoiceFlow** is a modern, production-ready B2B SaaS invoice management application. It couples a high-performance **React 19 Single Page Application (SPA)** powered by **Vite** with a secure **Django 5 & Django REST Framework** backend and **PostgreSQL** database.

Designed for multi-tenant business operations, InvoiceFlow enables companies and teams to manage clients, product catalogs, professional invoices, payment reconciliation, and financial analytics with zero friction.

---

## 📸 Preview

### 📊 Dashboard
![Dashboard](InvoiceFlow/assets/dashboard.png)

### 👥 Clients
![Clients](InvoiceFlow/assets/clients.png)

### 📦 Products & Services
![Products](InvoiceFlow/assets/products.png)

### 🧾 Creating Invoices
![Creating Invoice](InvoiceFlow/assets/Creating_Invoice.png)

### 📄 Invoice View & PDF Generation
![Invoice View](InvoiceFlow/assets/Invoice.png)

### 💳 Payments Tracking
![Payments](InvoiceFlow/assets/payments.png)

---

## ✨ Key Features & Architecture

### ⚛️ Modern React 19 Frontend (SPA)
- **Fluid Single-Page Navigation**: Instantaneous view transitions across Dashboard, Clients, Products, Invoices, Payments, and Reports without full-page reloads.
- **Tab-Scoped Session Authentication**:
  - **Isolated Tabs**: Opening InvoiceFlow in a fresh browser tab (`Ctrl+T` or new window) strictly requires login without breaking active sessions in other tabs.
  - **Duplicate Tab Protection**: Duplicated tabs automatically detect context duplication and require login.
  - **Reload & History Resilience**: Implements the **W3C Navigation Timing Level 2 API** (`performance.getEntriesByType('navigation')`), ensuring that fast or slow page refreshes (`F5`), cold starts, and browser Back/Forward traversals preserve authentication seamlessly.
  - **Cross-Tab Synchronized Logout**: Utilizes native **`BroadcastChannel`** messaging so that an explicit sign-out in any tab immediately invalidates and transitions all sibling tabs to the login screen, eliminating stale UI.
- **Guided Empty States**: Users can freely explore every section of the application even before creating a company, with guided empty state prompts directing them to set up their workspace.
- **100% WCAG 2.1 AA Accessibility**: Enhanced contrast ratios across typography, status badges, buttons, and alert states for maximum readability.
- **Sub-Second Vite Builds**: Configured with Vite 8 and Oxlint for ultra-fast compilation and static code analysis.

### 🏢 Multi-Tenant Architecture & Workspace Management
- **Company-Level Data Isolation**: Every customer, item, invoice, and payment is strictly partitioned by company workspace.
- **Multi-Company Management**: Users can create multiple companies and switch between active workspaces with a single click.
- **Membership Structure**: Foundation in place with company memberships associated with user accounts. *(Fine-grained multi-role permissions/RBAC enforcement across team members is planned on the roadmap).*
- **Instant Workspace Switching**: Switch between multiple registered businesses from the top bar with automatic context refresh.

### 🧾 Invoicing & Automated Accounting
- **Line Item Composition**: Add and customize invoice line items with individual quantities, unit rates, and description notes.
- **Real-Time Financial Calculations**: Automated calculation of subtotals, GST/tax rates, and discounts.
- **Lifecycle Status Engine**: Invoices transition through states: `DRAFT` $\rightarrow$ `SENT` $\rightarrow$ `PAID`, with automated detection of `OVERDUE` balances and manual cancellation (`CANCELLED`).
- **Dynamic PDF Generation**: Download print-ready, professionally styled PDF invoices on-the-fly generated via ReportLab.

### 💳 Payment Tracking & Reconciliation
- **Flexible Payments**: Support for partial payments, full settlement, and strict validation to prevent overpayments.
- **Multi-Method Support**: Record receipts via UPI, Bank Transfer, Credit/Debit Card, or Cash.
- **Automatic Balance Updating**: Every payment immediately updates remaining balance, invoice status, and dashboard cash flow metrics.

### 📈 Reports & Analytics
- **Dashboard Financial KPIs**: Instant summaries for Total Revenue, Outstanding Balance, Overdue Invoices, and Active Clients.
- **Company Audit PDF Reports**: Export complete company-level billing and collection statements as formatted PDFs.

---

## 🛠️ Technology Stack

| Layer | Technologies | Role / Description |
|---|---|---|
| **Frontend SPA** | **React 19**, **Vite 8**, **Oxlint** | Reactive user interface, component architecture, fast build bundling |
| **Frontend Styling** | Plain Modular **CSS** | High-performance, zero-runtime CSS; fully WCAG 2.1 AA compliant |
| **Backend REST API** | **Django 5.0.1**, **Django REST Framework 3.15** | RESTful API endpoints (`/api/*`), serialization, business logic |
| **Authentication & Security** | Django Session Auth, CSRF Protection | Secure HTTP cookies, CSRF tokens, secure headers, reverse-proxy SSL detection |
| **Database** | **PostgreSQL** (Supabase / Local) | Relational database with multi-tenant relational schema and constraints |
| **PDF Generation** | **ReportLab 5.0** | Server-side programmatic PDF compilation for invoices and reports |
| **Production WSGI** | **Gunicorn 21.2**, **Whitenoise 6.6** | Production Python WSGI HTTP server and static asset streaming |
| **Hosting (Frontend)** | **Vercel** | Edge deployment for React frontend with API route rewrites to Render |
| **Hosting (Backend)** | **Render** | Managed containerized web service hosting the Django REST backend |
| **Hosting (Database)** | **Supabase** | Managed PostgreSQL database cluster |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Browser"]
        ReactApp["React 19 SPA (Vite)\n(Components, Tab Auth, State)"]
        Storage["sessionStorage + window.name\n(Tab Isolation)"]
        Channel["BroadcastChannel\n(Cross-Tab Sync)"]
        ReactApp <--> Storage
        ReactApp <--> Channel
    end

    subgraph Edge ["Frontend Hosting (Vercel)"]
        VercelCDN["Vercel Edge Network\n(Static Assets /dist)"]
        RewriteRules["API Rewrites\n/api/* -> Render Backend"]
        VercelCDN --> ReactApp
        ReactApp -- API Requests --> RewriteRules
    end

    subgraph Backend ["Backend Hosting (Render)"]
        Gunicorn["Gunicorn WSGI Server"]
        DjangoApp["Django 5.0 REST API\n(Session Auth, CSRF Middleware)"]
        ReportLab["ReportLab PDF Engine"]
        RewriteRules --> Gunicorn
        Gunicorn --> DjangoApp
        DjangoApp --> ReportLab
    end

    subgraph Database ["Database (Supabase / PostgreSQL)"]
        Postgres[("PostgreSQL\n(Multi-tenant Relational DB)")]
        DjangoApp <--> Postgres
    end
```

### 🗄️ Entity-Relationship Model

```mermaid
erDiagram
    USER ||--o{ MEMBERSHIP : has
    COMPANY ||--o{ MEMBERSHIP : includes
    COMPANY ||--o{ CUSTOMER : has
    COMPANY ||--o{ PRODUCT : has
    COMPANY ||--o{ INVOICE : issues
    CUSTOMER ||--o{ INVOICE : receives
    INVOICE ||--o{ INVOICE_ITEM : contains
    PRODUCT ||--o{ INVOICE_ITEM : included_in
    INVOICE ||--o{ PAYMENT : has
```

---

## 📁 Project Directory Structure

```text
InvoiceFlow/
├── .env.example                       # Reference environment variables
├── .gitignore                         # Git exclusion rules
├── requirements.txt                   # Backend Python dependencies
├── README.md                          # Comprehensive project documentation
│
├── frontend/                          # React 19 + Vite Frontend SPA
│   ├── index.html                     # SPA entry point
│   ├── package.json                   # Frontend dependencies & scripts
│   ├── vite.config.js                 # Vite bundler & API dev proxy config
│   ├── src/
│   │   ├── main.jsx                   # React DOM root mounting
│   │   ├── App.jsx                    # Primary app router, auth state & tab lifecycle
│   │   ├── App.css                    # WCAG AA compliant responsive design system
│   │   ├── services/
│   │   │   └── api.js                 # DRF API client (CSRF, cookies & error handling)
│   │   └── components/
│   │       ├── Dashboard.jsx          # Metrics, workspace stats & company switcher
│   │       ├── Login.jsx              # Secure session login interface
│   │       ├── Signup.jsx             # User registration
│   │       ├── Customers.jsx          # Customer/Client CRUD interface
│   │       ├── Products.jsx           # Product/Service catalog management
│   │       ├── Invoices.jsx           # Invoice builder, status & PDF triggers
│   │       ├── Payments.jsx           # Payment recording & reconciliation
│   │       ├── Reports.jsx            # Financial reporting and export hub
│   │       └── CompanyRequiredState.jsx # Reusable empty state for new workspaces
│   └── dist/                          # Compiled production assets
│
└── InvoiceFlow/                       # Django Backend Project
    ├── manage.py                      # Django management script
    ├── assets/                        # Diagrams, screenshots, and visual assets
    ├── InvoiceFlow/                   # Project configuration
    │   ├── settings.py                # Security, DRF, database & cookie configuration
    │   ├── urls.py                    # Root URL router (/api/* and views)
    │   └── wsgi.py                    # WSGI entry point for Gunicorn
    └── myapp/                         # Core Django application
        ├── models.py                  # PostgreSQL relational schema
        ├── serializers.py             # DRF Model serializers
        ├── api_views.py               # REST API views (auth, clients, invoices, payments)
        ├── api_urls.py                # REST API route mappings
        ├── views.py                   # Legacy template views & PDF generation logic
        ├── tests.py                   # 100+ comprehensive automated unit & integration tests
        ├── test_browser_auth.py       # Real Chrome DevTools Protocol (CDP) E2E tests
        └── migrations/                # Database migration history
```

---

## ⚡ Getting Started Locally

### 1. Prerequisites
- **Python** (v3.11 or higher)
- **Node.js** (v18 or higher) and **npm**
- **PostgreSQL** (v14 or higher, running locally or on Supabase)
- **Git**

---

### 2. Backend Setup (Django REST API)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SharveshC/InvoiceFlow.git
   cd InvoiceFlow
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secure-django-secret-key
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

   # Local PostgreSQL configuration
   DB_NAME=invoiceflow
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=127.0.0.1
   DB_PORT=5432

   # Or use a Supabase connection string:
   # DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```

5. **Apply database migrations:**
   ```bash
   python InvoiceFlow/manage.py migrate
   ```

6. **Create an administrator account (optional):**
   ```bash
   python InvoiceFlow/manage.py createsuperuser
   ```

7. **Start the Django development server:**
   ```bash
   python InvoiceFlow/manage.py runserver 127.0.0.1:8000
   ```
   *The backend REST API is available at `http://127.0.0.1:8000/api/`.*

---

### 3. Frontend Setup (React 19 + Vite)

1. **Open a new terminal and navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install
   ```

3. **Launch the Vite development server:**
   ```bash
   npm run dev
   ```
   *The React application will be accessible at `http://localhost:5173/`.*
   *Vite automatically proxies `/api/*` requests to `http://127.0.0.1:8000/`.*

---

## 🧪 Testing & Verification

InvoiceFlow includes an extensive test suite covering backend logic, REST APIs, and automated browser behavior.

### 1. Django Backend Test Suite
Runs all 103+ unit and integration tests (company isolation, RBAC, invoice totals, overpayment guards):
```bash
python InvoiceFlow/manage.py test myapp --noinput
```

### 2. Real-World Chrome End-to-End Browser Tests
Runs automated browser lifecycle tests via Chrome DevTools Protocol (CDP) verifying tab isolation, duplicate tab restrictions, slow reload resilience, and cross-tab logout synchronization:
```bash
python InvoiceFlow/manage.py test myapp.test_browser_auth --noinput
```

### 3. Frontend Code Quality & Static Analysis
Checks JavaScript and JSX syntax using Oxlint:
```bash
npm --prefix frontend run lint
```

### 4. Production Build Verification
Compiles the React production bundle:
```bash
npm --prefix frontend run build
```

---

## 🚢 Deployment Architecture (₹0 Free Tier)

| Component | Target Platform | Build Command / Setup |
|---|---|---|
| **Frontend** | **Vercel** | **Root Directory**: `frontend`<br>**Build Command**: `npm run build`<br>**Output Directory**: `dist`<br>**Edge Rewrites**: Route `/api/:path*` to Render backend URL |
| **Backend** | **Render** | **Environment**: Python 3.12<br>**Build Command**: `pip install -r requirements.txt && python InvoiceFlow/manage.py collectstatic --noinput`<br>**Start Command**: `gunicorn --chdir InvoiceFlow InvoiceFlow.wsgi:application` |
| **Database** | **Supabase** | Managed PostgreSQL database with `DATABASE_URL` configured in Render environment variables |

---

## 🗺️ Roadmap & Upcoming Features

- [ ] **Multi-Role RBAC & Invitations**: Team member invitations with granular permission enforcement (`OWNER`, `ADMIN`, `STAFF`) across API endpoints and UI actions.
- [ ] **Email Invoice Dispatch**: Send PDF invoices directly to clients via SMTP/email service integrations.
- [ ] **Payment Gateway Integration**: Direct online payment checkout links (Stripe / Razorpay).

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
