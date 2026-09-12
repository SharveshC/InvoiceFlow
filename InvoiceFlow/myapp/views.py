from decimal import Decimal, InvalidOperation
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .models import (
    Company,
    Membership,
    Customer,
    Product,
    Invoice,
    InvoiceItem,
    Payment,
)


def home(request):
    return render(request, "index.html")


def login_page(request):
    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = User.objects.get(email__iexact=email)
            username = user.username

        except User.DoesNotExist:
            username = None

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        return render(request, "login.html", {"error": "Invalid email or password."})

    return render(request, "login.html")


def signup(request):
    if request.method == "POST":

        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "signup.html", {"error": "Passwords do not match."})

        if User.objects.filter(email__iexact=email).exists():
            return render(
                request,
                "signup.html",
                {"error": "An account with this email already exists."},
            )

        username = email

        user = User.objects.create_user(
            username=username, email=email, password=password
        )

        user.first_name = full_name
        user.save()

        return redirect("login")

    return render(request, "signup.html")


from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render


@login_required
def dashboard(request):

    # ==========================================
    # USER'S COMPANIES
    # ==========================================

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    # ==========================================
    # CURRENT COMPANY
    # ==========================================

    current_company_id = request.session.get("current_company_id")

    current_company = None

    if current_company_id:

        current_company = next(
            (company for company in companies if company.id == current_company_id),
            None,
        )

    if current_company is None and companies:

        current_company = companies[0]

        request.session["current_company_id"] = current_company.id

    # ==========================================
    # DEFAULT DASHBOARD VALUES
    # ==========================================

    total_revenue = 0

    paid_invoices_count = 0

    pending_amount = 0
    pending_invoice_count = 0

    overdue_amount = 0
    overdue_invoice_count = 0

    this_month_revenue = 0
    this_month_paid_invoices = 0

    recent_invoices = []

    # ==========================================
    # CURRENT COMPANY DATA
    # ==========================================

    if current_company:

        today = date.today()

        # ======================================
        # COMPANY INVOICES
        # ======================================

        company_invoices = Invoice.objects.filter(company=current_company)

        # ======================================
        # TOTAL REVENUE
        # ======================================

        total_revenue = (
            Payment.objects.filter(invoice__company=current_company).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # ======================================
        # PAID INVOICES
        # ======================================

        paid_invoices_count = company_invoices.filter(status="PAID").count()

        # ======================================
        # THIS MONTH REVENUE
        # ======================================

        this_month_revenue = (
            Payment.objects.filter(
                invoice__company=current_company,
                payment_date__year=today.year,
                payment_date__month=today.month,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # ======================================
        # PAID INVOICES THIS MONTH
        # ======================================

        this_month_paid_invoices = company_invoices.filter(
            status="PAID",
            updated_at__year=today.year,
            updated_at__month=today.month,
        ).count()

        # ======================================
        # PENDING + OVERDUE
        # ======================================

        unpaid_invoices = company_invoices.exclude(
            status__in=[
                "PAID",
                "CANCELLED",
            ]
        )

        for invoice in unpaid_invoices:

            paid_amount = invoice.payments.aggregate(total=Sum("amount"))["total"] or 0

            remaining_amount = invoice.total - paid_amount

            if remaining_amount > 0:

                pending_amount += remaining_amount

                pending_invoice_count += 1

                # ------------------------------
                # OVERDUE
                # ------------------------------

                if invoice.due_date < today:

                    overdue_amount += remaining_amount

                    overdue_invoice_count += 1

        # ======================================
        # RECENT INVOICES
        # ======================================

        recent_invoices = company_invoices.select_related("customer").order_by(
            "-created_at"
        )[:5]

    # ==========================================
    # DASHBOARD CONTEXT
    # ==========================================

    context = {
        # Company
        "companies": companies,
        "current_company": current_company,
        # Revenue
        "total_revenue": total_revenue,
        "this_month_revenue": this_month_revenue,
        # Paid
        "paid_invoices_count": paid_invoices_count,
        "this_month_paid_invoices": this_month_paid_invoices,
        # Pending
        "pending_amount": pending_amount,
        "pending_invoice_count": pending_invoice_count,
        # Overdue
        "overdue_amount": overdue_amount,
        "overdue_invoice_count": overdue_invoice_count,
        # Recent invoices
        "recent_invoices": recent_invoices,
    }

    return render(
        request,
        "after_login.html",
        context,
    )


def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")

    return redirect("home")


@login_required
def create_company(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        gst_number = request.POST.get("gst_number")

        if not name or not email or not phone or not address:
            return render(
                request,
                "create_company.html",
                {"error": "Please fill in all required fields."},
            )

        company = Company.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number or None,
        )

        Membership.objects.create(user=request.user, company=company, role="OWNER")

        request.session["current_company_id"] = company.id

        return redirect("dashboard")

    return render(request, "create_company.html")


@login_required
def switch_company(request, company_id):

    membership = Membership.objects.filter(
        user=request.user, company_id=company_id
    ).first()

    if membership is None:
        return redirect("dashboard")

    request.session["current_company_id"] = company_id

    return redirect("dashboard")


@login_required
def clients(request):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    customers = Customer.objects.filter(company=current_company).order_by("-created_at")

    return render(
        request,
        "clients.html",
        {
            "customers": customers,
            "current_company": current_company,
            "companies": companies,
        },
    )


@login_required
def add_client(request):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        gst_number = request.POST.get("gst_number")

        if not name or not email or not phone or not address:
            return render(
                request,
                "add_client.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "error": "Please fill in all required fields.",
                },
            )

        Customer.objects.create(
            company=current_company,
            name=name,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number or None,
        )

        return redirect("clients")

    return render(
        request,
        "add_client.html",
        {
            "current_company": current_company,
            "companies": companies,
        },
    )


@login_required
def edit_client(request, client_id):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    customer = Customer.objects.filter(id=client_id, company=current_company).first()

    if customer is None:
        return redirect("clients")

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        gst_number = request.POST.get("gst_number")

        if not name or not email or not phone or not address:
            return render(
                request,
                "edit_client.html",
                {
                    "customer": customer,
                    "current_company": current_company,
                    "companies": companies,
                    "error": "Please fill in all required fields.",
                },
            )

        customer.name = name
        customer.email = email
        customer.phone = phone
        customer.address = address
        customer.gst_number = gst_number or None
        customer.save()

        return redirect("clients")

    return render(
        request,
        "edit_client.html",
        {
            "customer": customer,
            "current_company": current_company,
            "companies": companies,
        },
    )


@login_required
def delete_client(request, client_id):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    customer = Customer.objects.filter(id=client_id, company=current_company).first()

    if customer is None:
        return redirect("clients")

    if request.method == "POST":
        customer.delete()
        return redirect("clients")

    return redirect("clients")


@login_required
def products(request):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    products = Product.objects.filter(company=current_company).order_by("-created_at")

    return render(
        request,
        "products.html",
        {
            "products": products,
            "current_company": current_company,
            "companies": companies,
        },
    )


@login_required
def add_product(request):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    if request.method == "POST":

        name = request.POST.get("name")
        description = request.POST.get("description")
        price = request.POST.get("price")
        tax = request.POST.get("tax")

        if not name or not price:
            return render(
                request,
                "add_product.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "error": "Product name and price are required.",
                },
            )

        Product.objects.create(
            company=current_company,
            name=name,
            description=description or None,
            price=price,
            tax=tax or 0,
        )

        return redirect("products")

    return render(
        request,
        "add_product.html",
        {
            "current_company": current_company,
            "companies": companies,
        },
    )


@login_required
def edit_product(request, product_id):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    product = Product.objects.filter(id=product_id, company=current_company).first()

    if product is None:
        return redirect("products")

    if request.method == "POST":

        name = request.POST.get("name")
        description = request.POST.get("description")
        price = request.POST.get("price")
        tax = request.POST.get("tax")

        if not name or not price:
            return render(
                request,
                "edit_product.html",
                {
                    "product": product,
                    "current_company": current_company,
                    "companies": companies,
                    "error": "Product name and price are required.",
                },
            )

        product.name = name
        product.description = description or None
        product.price = price
        product.tax = tax or 0

        product.save()

        return redirect("products")

    return render(
        request,
        "edit_product.html",
        {
            "product": product,
            "current_company": current_company,
            "companies": companies,
        },
    )


@login_required
def delete_product(request, product_id):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user, company_id=current_company_id
    ).first()

    if membership is None:
        return redirect("dashboard")

    product = Product.objects.filter(
        id=product_id, company_id=current_company_id
    ).first()

    if product is None:
        return redirect("products")

    if request.method == "POST":
        product.delete()
        return redirect("products")

    return redirect("products")


@login_required
def invoices(request):

    # =========================
    # GET USER COMPANIES
    # =========================

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    # =========================
    # GET CURRENT COMPANY
    # =========================

    current_company_id = request.session.get("current_company_id")

    current_company = None

    if current_company_id:
        current_company = next(
            (company for company in companies if company.id == current_company_id),
            None,
        )

    if current_company is None:
        return redirect("dashboard")

    # =========================
    # UPDATE OVERDUE INVOICES
    # =========================

    today = date.today()

    overdue_invoices = Invoice.objects.filter(
        company=current_company,
        status__in=["DRAFT", "SENT"],
        due_date__lt=today,
    )

    overdue_invoices.update(status="OVERDUE")

    # =========================
    # GET INVOICES
    # =========================

    invoices = (
        Invoice.objects.filter(company=current_company)
        .select_related("customer")
        .order_by("-created_at")
    )

    return render(
        request,
        "invoices.html",
        {
            "companies": companies,
            "current_company": current_company,
            "invoices": invoices,
        },
    )


@login_required
def create_invoice(request):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    customers = Customer.objects.filter(company=current_company).order_by("name")

    products = Product.objects.filter(company=current_company).order_by("name")

    if request.method == "POST":

        invoice_number = request.POST.get("invoice_number", "").strip()
        customer_id = request.POST.get("customer")
        issue_date = request.POST.get("issue_date")
        due_date = request.POST.get("due_date")
        discount_value = request.POST.get("discount", "0")
        notes = request.POST.get("notes", "").strip()

        if not invoice_number:
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Invoice number is required.",
                },
            )

        if not customer_id:
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Please select a customer.",
                },
            )

        try:
            customer = Customer.objects.get(id=customer_id, company=current_company)
        except Customer.DoesNotExist:
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Invalid customer.",
                },
            )

        try:
            discount = Decimal(discount_value or "0")

            if discount < 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError):
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Invalid discount amount.",
                },
            )

        product_ids = request.POST.getlist("product[]")
        quantities = request.POST.getlist("quantity[]")
        unit_prices = request.POST.getlist("unit_price[]")
        taxes = request.POST.getlist("tax[]")

        if not product_ids:
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Please add at least one invoice item.",
                },
            )

        if not (len(product_ids) == len(quantities) == len(unit_prices) == len(taxes)):
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Invalid invoice items.",
                },
            )

        try:

            subtotal = Decimal("0.00")
            total_tax = Decimal("0.00")

            invoice_items = []

            for i in range(len(product_ids)):

                product_id = product_ids[i]

                product = Product.objects.get(id=product_id, company=current_company)

                quantity = Decimal(quantities[i])
                unit_price = Decimal(unit_prices[i])
                tax_percent = Decimal(taxes[i])

                if quantity <= 0:
                    raise ValueError("Quantity must be greater than zero.")

                if unit_price < 0:
                    raise ValueError("Unit price cannot be negative.")

                if tax_percent < 0:
                    raise ValueError("Tax cannot be negative.")

                line_subtotal = quantity * unit_price
                line_tax = (line_subtotal * tax_percent) / Decimal("100")
                line_total = line_subtotal + line_tax

                subtotal += line_subtotal
                total_tax += line_tax

                invoice_items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "tax": tax_percent,
                        "line_total": line_total,
                    }
                )

            total = subtotal + total_tax - discount

            if total < 0:
                total = Decimal("0.00")

        except Product.DoesNotExist:
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Invalid product selected.",
                },
            )

        except (InvalidOperation, ValueError, ArithmeticError):
            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": "Please enter valid invoice item values.",
                },
            )

        try:

            with transaction.atomic():

                invoice = Invoice.objects.create(
                    company=current_company,
                    customer=customer,
                    invoice_number=invoice_number,
                    issue_date=issue_date,
                    due_date=due_date,
                    status="SENT",
                    subtotal=subtotal,
                    tax_amount=total_tax,
                    discount_amount=discount,
                    total=total,
                    notes=notes,
                )

                for item in invoice_items:

                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=item["product"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        tax=item["tax"],
                        line_total=item["line_total"],
                    )

        except Exception as e:

            if "unique" in str(e).lower():
                error = "Invoice number already exists for this company."
            else:
                error = f"Could not create invoice: {str(e)}"

            return render(
                request,
                "create_invoice.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "customers": customers,
                    "products": products,
                    "error": error,
                },
            )

        return redirect("invoices")

    return render(
        request,
        "create_invoice.html",
        {
            "current_company": current_company,
            "companies": companies,
            "customers": customers,
            "products": products,
        },
    )


@login_required
def payments(request):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    payments = (
        Payment.objects.filter(invoice__company=current_company)
        .select_related("invoice", "invoice__customer")
        .order_by("-payment_date", "-created_at")
    )

    total_received = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    today = date.today()

    this_month = payments.filter(
        payment_date__year=today.year, payment_date__month=today.month
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return render(
        request,
        "payments.html",
        {
            "payments": payments,
            "current_company": current_company,
            "companies": companies,
            "total_received": total_received,
            "this_month": this_month,
        },
    )


@login_required
def record_payment(request):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(
            user=request.user,
            company_id=current_company_id
        )
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = (
        Membership.objects
        .filter(user=request.user)
        .select_related("company")
    )

    companies = [
        membership.company
        for membership in memberships
    ]

    # =========================
    # GET ALL INVOICES
    # =========================

    invoices = (
        Invoice.objects
        .filter(company=current_company)
        .select_related("customer")
        .annotate(
            paid_amount=Sum("payments__amount")
        )
        .order_by("-created_at")
    )

    # =========================
    # GET INVOICE FROM URL
    # =========================

    selected_invoice_id = request.GET.get("invoice_id")

    selected_invoice = None

    if selected_invoice_id:

        selected_invoice = (
            Invoice.objects
            .filter(
                id=selected_invoice_id,
                company=current_company,
            )
            .select_related("customer")
            .first()
        )

    # =========================
    # POST
    # =========================

    if request.method == "POST":

        invoice_id = request.POST.get("invoice")
        amount_text = request.POST.get("amount")
        payment_method = request.POST.get("payment_method")
        payment_date = request.POST.get("payment_date")
        notes = request.POST.get("notes")

        # =========================
        # VALIDATE PAYMENT AMOUNT
        # =========================

        try:

            amount = Decimal(amount_text)

        except (InvalidOperation, TypeError):

            return render(
                request,
                "record_payment.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "invoices": invoices,
                    "selected_invoice": selected_invoice,
                    "selected_invoice_id": selected_invoice_id,
                    "error": "Enter a valid payment amount.",
                },
            )

        if amount <= 0:

            return render(
                request,
                "record_payment.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "invoices": invoices,
                    "selected_invoice": selected_invoice,
                    "selected_invoice_id": selected_invoice_id,
                    "error": "Payment amount must be greater than zero.",
                },
            )

        # =========================
        # VALIDATE PAYMENT DATE
        # =========================

        try:

            payment_date_value = date.fromisoformat(
                payment_date
            )

        except (ValueError, TypeError):

            return render(
                request,
                "record_payment.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "invoices": invoices,
                    "selected_invoice": selected_invoice,
                    "selected_invoice_id": selected_invoice_id,
                    "error": "Enter a valid payment date.",
                },
            )

        # =========================
        # TRANSACTION
        # =========================

        with transaction.atomic():

            invoice = (
                Invoice.objects
                .select_for_update()
                .filter(
                    id=invoice_id,
                    company=current_company,
                )
                .first()
            )

            # =========================
            # INVALID INVOICE
            # =========================

            if invoice is None:

                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "selected_invoice": selected_invoice,
                        "selected_invoice_id": selected_invoice_id,
                        "error": "Invalid invoice selected.",
                    },
                )

            # =========================
            # CANCELLED INVOICE
            # =========================

            if invoice.status == "CANCELLED":

                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "selected_invoice": selected_invoice,
                        "selected_invoice_id": selected_invoice_id,
                        "error": (
                            "Payment cannot be recorded "
                            "for a cancelled invoice."
                        ),
                    },
                )

            # =========================
            # CALCULATE ALREADY PAID
            # =========================

            paid_amount = (
                invoice.payments
                .aggregate(
                    total=Sum("amount")
                )["total"]
                or Decimal("0.00")
            )

            # =========================
            # CALCULATE REMAINING
            # =========================

            remaining_amount = (
                invoice.total - paid_amount
            )

            # =========================
            # ALREADY FULLY PAID
            # =========================

            if remaining_amount <= 0:

                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "selected_invoice": selected_invoice,
                        "selected_invoice_id": selected_invoice_id,
                        "error": (
                            "This invoice has already "
                            "been fully paid."
                        ),
                    },
                )

            # =========================
            # PREVENT OVERPAYMENT
            # =========================

            if amount > remaining_amount:

                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "selected_invoice": selected_invoice,
                        "selected_invoice_id": selected_invoice_id,
                        "error": (
                            f"Payment cannot exceed "
                            f"the remaining balance of "
                            f"₹{remaining_amount}."
                        ),
                    },
                )

            # =========================
            # CREATE PAYMENT
            # =========================

            Payment.objects.create(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date_value,
                notes=notes,
            )

            # =========================
            # UPDATE INVOICE STATUS
            # =========================

            new_paid_amount = (
                paid_amount + amount
            )

            if new_paid_amount >= invoice.total:

                invoice.status = "PAID"

            elif invoice.due_date < date.today():

                invoice.status = "OVERDUE"

            else:

                invoice.status = "SENT"

            invoice.save(
                update_fields=[
                    "status",
                    "updated_at"
                ]
            )

        # =========================
        # SUCCESS
        # =========================

        return redirect("payments")

    # =========================
    # GET
    # =========================

    return render(
        request,
        "record_payment.html",
        {
            "current_company": current_company,
            "companies": companies,
            "invoices": invoices,
            "selected_invoice": selected_invoice,
            "selected_invoice_id": selected_invoice_id,
        },
    )


@login_required
def invoice_details(request, invoice_id):

    current_company_id = request.session.get("current_company_id")

    if not current_company_id:
        return redirect("dashboard")

    membership = (
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    invoice = (
        Invoice.objects.select_related("customer")
        .filter(id=invoice_id, company=current_company)
        .first()
    )

    if invoice is None:
        return redirect("invoices")

    items = InvoiceItem.objects.filter(invoice=invoice).select_related("product")

    payments = Payment.objects.filter(invoice=invoice).order_by(
        "-payment_date", "-created_at"
    )

    paid_amount = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    remaining_amount = invoice.total - paid_amount

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    return render(
        request,
        "invoice_details.html",
        {
            "current_company": current_company,
            "companies": companies,
            "invoice": invoice,
            "items": items,
            "payments": payments,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
        },
    )


@login_required
def export_report(request):

    # ==========================================
    # USER'S COMPANIES
    # ==========================================

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    # ==========================================
    # CURRENT COMPANY
    # ==========================================

    current_company_id = request.session.get("current_company_id")

    current_company = None

    if current_company_id:

        current_company = next(
            (company for company in companies if company.id == current_company_id),
            None,
        )

    # If no valid company is selected,
    # fall back to the user's first company.

    if current_company is None and companies:

        current_company = companies[0]

        request.session["current_company_id"] = current_company.id

    # ==========================================
    # SAFETY CHECK
    # ==========================================

    if current_company is None:

        return HttpResponse(
            "No company found.",
            status=400,
        )

    # ==========================================
    # COMPANY INVOICES
    # ==========================================

    company_invoices = (
        Invoice.objects.filter(company=current_company)
        .select_related("customer")
        .order_by("-created_at")
    )

    # ==========================================
    # COMPANY PAYMENTS
    # ==========================================

    company_payments = (
        Payment.objects.filter(invoice__company=current_company)
        .select_related(
            "invoice",
            "invoice__customer",
        )
        .order_by(
            "-payment_date",
            "-created_at",
        )
    )

    # ==========================================
    # TOTAL REVENUE
    # ==========================================

    total_revenue = company_payments.aggregate(total=Sum("amount"))["total"] or Decimal(
        "0.00"
    )

    # ==========================================
    # PAID INVOICES
    # ==========================================

    paid_invoices_count = company_invoices.filter(status="PAID").count()

    # ==========================================
    # PENDING / OVERDUE
    # ==========================================

    pending_amount = Decimal("0.00")

    overdue_amount = Decimal("0.00")

    today = date.today()

    unpaid_invoices = company_invoices.exclude(
        status__in=[
            "PAID",
            "CANCELLED",
        ]
    )

    for invoice in unpaid_invoices:

        paid_amount = invoice.payments.aggregate(total=Sum("amount"))[
            "total"
        ] or Decimal("0.00")

        remaining_amount = invoice.total - paid_amount

        if remaining_amount > 0:

            pending_amount += remaining_amount

            if invoice.due_date < today:

                overdue_amount += remaining_amount

    # ==========================================
    # PDF RESPONSE
    # ==========================================

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = "attachment; " 'filename="invoiceflow_report.pdf"'

    # ==========================================
    # PDF DOCUMENT
    # ==========================================

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]

    heading_style = styles["Heading2"]

    normal_style = styles["Normal"]

    elements = []

    # ==========================================
    # REPORT HEADER
    # ==========================================

    elements.append(
        Paragraph(
            "InvoiceFlow",
            title_style,
        )
    )

    elements.append(
        Paragraph(
            "Financial Report",
            heading_style,
        )
    )

    elements.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    elements.append(
        Paragraph(
            f"<b>Company:</b> " f"{current_company.name}",
            normal_style,
        )
    )

    elements.append(
        Paragraph(
            f"<b>Generated:</b> " f"{today.strftime('%d %b %Y')}",
            normal_style,
        )
    )

    elements.append(
        Spacer(
            1,
            8 * mm,
        )
    )

    # ==========================================
    # SUMMARY
    # ==========================================

    elements.append(
        Paragraph(
            "Summary",
            heading_style,
        )
    )

    summary_data = [
        [
            "Metric",
            "Value",
        ],
        [
            "Total Revenue",
            f"₹{total_revenue:,.2f}",
        ],
        [
            "Paid Invoices",
            str(paid_invoices_count),
        ],
        [
            "Pending Amount",
            f"₹{pending_amount:,.2f}",
        ],
        [
            "Overdue Amount",
            f"₹{overdue_amount:,.2f}",
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            80 * mm,
            80 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elements.append(summary_table)

    elements.append(
        Spacer(
            1,
            10 * mm,
        )
    )

    # ==========================================
    # INVOICES
    # ==========================================

    elements.append(
        Paragraph(
            "Invoices",
            heading_style,
        )
    )

    invoice_data = [
        [
            "Invoice",
            "Customer",
            "Date",
            "Amount",
            "Status",
        ]
    ]

    for invoice in company_invoices:

        invoice_data.append(
            [
                invoice.invoice_number,
                invoice.customer.name,
                invoice.issue_date.strftime("%d %b %Y"),
                f"₹{invoice.total:,.2f}",
                invoice.get_status_display(),
            ]
        )

    if len(invoice_data) == 1:

        invoice_data.append(
            [
                "-",
                "No invoices",
                "-",
                "-",
                "-",
            ]
        )

    invoice_table = Table(
        invoice_data,
        repeatRows=1,
    )

    invoice_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    elements.append(invoice_table)

    elements.append(
        Spacer(
            1,
            10 * mm,
        )
    )

    # ==========================================
    # PAYMENTS
    # ==========================================

    elements.append(
        Paragraph(
            "Payments",
            heading_style,
        )
    )

    payment_data = [
        [
            "Invoice",
            "Customer",
            "Date",
            "Method",
            "Amount",
        ]
    ]

    for payment in company_payments:

        payment_data.append(
            [
                payment.invoice.invoice_number,
                payment.invoice.customer.name,
                payment.payment_date.strftime("%d %b %Y"),
                payment.get_payment_method_display(),
                f"₹{payment.amount:,.2f}",
            ]
        )

    if len(payment_data) == 1:

        payment_data.append(
            [
                "-",
                "-",
                "No payments",
                "-",
                "-",
            ]
        )

    payment_table = Table(
        payment_data,
        repeatRows=1,
    )

    payment_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    elements.append(payment_table)

    # ==========================================
    # BUILD PDF
    # ==========================================

    document.build(elements)

    return response


@login_required
def cancel_invoice(request, invoice_id):

    # ==========================================
    # ONLY POST REQUESTS ALLOWED
    # ==========================================

    if request.method != "POST":
        return redirect("invoice_details", invoice_id=invoice_id)

    # ==========================================
    # GET CURRENT COMPANY
    # ==========================================

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    current_company_id = request.session.get("current_company_id")

    current_company = None

    if current_company_id:

        current_company = next(
            (company for company in companies if company.id == current_company_id),
            None,
        )

    # ==========================================
    # NO COMPANY
    # ==========================================

    if current_company is None:

        return redirect("dashboard")

    # ==========================================
    # GET INVOICE
    # ==========================================

    invoice = Invoice.objects.filter(
        id=invoice_id,
        company=current_company,
    ).first()

    if invoice is None:

        return redirect("invoices")

    # ==========================================
    # BUSINESS RULES
    # ==========================================

    # Already paid invoices cannot be cancelled.

    if invoice.status == "PAID":

        return redirect(
            "invoice_details",
            invoice_id=invoice.id,
        )

    # Already cancelled invoices cannot be
    # cancelled again.

    if invoice.status == "CANCELLED":

        return redirect(
            "invoice_details",
            invoice_id=invoice.id,
        )

    # ==========================================
    # CANCEL INVOICE
    # ==========================================

    invoice.status = "CANCELLED"

    invoice.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    # ==========================================
    # RETURN TO DETAILS
    # ==========================================

    return redirect(
        "invoice_details",
        invoice_id=invoice.id,
    )
