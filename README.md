# 🚀 InvoiceFlow

## 💡 Why InvoiceFlow?

InvoiceFlow is a comprehensive, multi-tenant Django-based application designed for B2B SaaS invoicing. It was built to eliminate the hassle of managing multiple companies, clients, products, invoices, and payments by providing a unified, centralized dashboard for businesses of all sizes.

![InvoiceFlow Banner](https://img.shields.io/badge/InvoiceFlow-B2B%20SaaS%20Invoicing-blue?style=for-the-badge&logo=django)

## ✨ Features

### 🎯 Core Features
- **Multi-Tenant Architecture**: Users can create and manage multiple companies and switch between them effortlessly
- **Role-based Access**: Assign different roles (Owner, Admin, Staff) to users within a company to ensure secure access control
- **Interactive Dashboard**: View key metrics such as total revenue, pending amounts, overdue invoices, and recent activity at a glance

### 🏢 Client & Product Management
- **Centralized Client Hub**: Easily add, edit, and manage clients for each company
- **Product Catalog**: Manage products or services with pricing and tax details

### 🧾 Invoice Generation & Management
- **Status Tracking**: Create and manage invoices with various statuses (Draft, Sent, Paid, Overdue, Cancelled)
- **Automated Calculations**: Automatically calculate subtotals, taxes, and discounts based on invoice items
- **PDF Generation**: Generate, view, and download professional invoices as PDF documents (powered by ReportLab)

### 💳 Payment Tracking
- **Multi-Method Support**: Record payments against specific invoices using different payment methods (Cash, UPI, Card, Bank Transfer)
- **Real-time Updates**: Keep track of pending and paid amounts automatically when a payment is recorded

### 📊 Reporting & Analytics
- **Export Reports**: Generate and export CSV/PDF reports for business analytics and accounting purposes

## 🛠️ Tech Stack

### Backend
- **Python 3** - Core programming language
- **Django 5.x** - High-level Python Web framework
- **PostgreSQL** - Primary robust relational database
- **ReportLab** - PDF generation engine

### Frontend
- **HTML/CSS** - Structure and styling
- **Django Templates (DTL)** - Server-side rendering for dynamic pages

## 📦 Installation

### Prerequisites
- **Python** (v3.10 or higher)
- **pip** (Python package installer)
- **PostgreSQL** (Installed and running)
- **Git**

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/SharveshC/InvoiceFlow.git
   cd InvoiceFlow
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```bash
   pip install django reportlab psycopg2-binary python-dotenv
   ```
   *(Note: Alternatively use `pip install -r requirements.txt` if available)*

4. **Configure Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-django-secret-key
   DB_NAME=invoiceflow_db
   DB_USER=postgres
   DB_PASSWORD=your-db-password
   DB_HOST=localhost
   DB_PORT=5432
   ```

5. **Run Database Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a Superuser (Optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run Development Server**
   ```bash
   python manage.py runserver
   ```
   
   The app will be available at `http://localhost:8000/`

## 🎮 Usage

### Getting Started

1. **Sign Up / Login**
   - Navigate to the landing page and sign up for a new account or log in
   
2. **Create a Company**
   - Upon logging in, create your first company to start managing its billing
   - Switch between multiple companies from the top navigation bar

3. **Add Clients & Products**
   - Navigate to the "Clients" section to add new customers
   - Go to "Products" to build your catalog of services or items

4. **Generate Invoices**
   - Click on "Create Invoice" and select a client
   - Add products/items, adjust quantities, and apply discounts or taxes
   - Save as Draft or Mark as Sent
   - Download the generated PDF invoice

5. **Record Payments**
   - When a client pays, go to the invoice and click "Record Payment"
   - Select the payment method and enter the amount. The dashboard metrics will update automatically

## 🏗️ Architecture & Codebase Details

### 📊 System Architecture

![Architecture Diagram](assets/diagram.png)

### 📁 Project Structure

```
InvoiceFlow/
├── .env                   # Environment variables (not in repo)
├── .gitignore             # Git ignore rules
├── manage.py              # Django CLI utility
├── README.md              # Project documentation
├── InvoiceFlow/           # Project configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py        # Database (PostgreSQL), Apps, and Middleware config
│   ├── urls.py            # Global URL routing
│   └── wsgi.py
└── myapp/                 # Core Django Application
    ├── admin.py           # Admin panel configuration
    ├── apps.py            # App configuration
    ├── models.py          # Database schema (Company, Invoice, Customer, etc.)
    ├── views.py           # Business logic, dashboard metrics, PDF generation
    ├── urls.py            # App-level routing
    ├── templates/         # HTML templates (Django Template Language)
    └── migrations/        # Database migration files
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Contributors

- **Sharvesh C**  
  GitHub: [@SharveshC](https://github.com/SharveshC)