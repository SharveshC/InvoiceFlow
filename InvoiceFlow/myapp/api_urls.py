from django.urls import path
from . import api_views, views

urlpatterns = [
    # Health check
    path("health/", api_views.api_health_check, name="api_health_check"),
    # Authentication endpoints
    path("auth/csrf/", api_views.api_csrf_token, name="api_csrf_token"),
    path("auth/signup/", api_views.api_signup, name="api_signup"),
    path("auth/login/", api_views.api_login, name="api_login"),
    path("auth/logout/", api_views.api_logout, name="api_logout"),
    path("auth/user/", api_views.api_current_user, name="api_current_user"),
    # Company endpoints
    path("companies/", api_views.api_create_company, name="api_create_company"),
    path("companies/<int:company_id>/switch/", api_views.api_switch_company, name="api_switch_company"),
    # Customer endpoints
    path("customers/", api_views.api_customers_list_create, name="api_customers_list_create"),
    path("customers/<int:customer_id>/", api_views.api_customer_detail, name="api_customer_detail"),
    # Product endpoints
    path("products/", api_views.api_products_list_create, name="api_products_list_create"),
    path("products/<int:product_id>/", api_views.api_product_detail, name="api_product_detail"),
    # Invoice endpoints
    path("invoices/", api_views.api_invoices_list_create, name="api_invoices_list_create"),
    path("invoices/<int:invoice_id>/", api_views.api_invoice_detail, name="api_invoice_detail"),
    path("invoices/<int:invoice_id>/cancel/", api_views.api_invoice_cancel, name="api_invoice_cancel"),
    path("invoices/<int:invoice_id>/pdf/", views.generate_invoice_pdf, name="api_invoice_pdf"),
    # Payment endpoints
    path("payments/", api_views.api_payments_list_create, name="api_payments_list_create"),
    path("payments/<int:payment_id>/", api_views.api_payment_detail, name="api_payment_detail"),
    # Report & Analytics endpoints
    path("reports/summary/", api_views.api_reports_summary, name="api_reports_summary"),
    path("reports/export/", views.export_report, name="api_export_report"),
]
