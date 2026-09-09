from decimal import Decimal, InvalidOperation
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect

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


@login_required
def dashboard(request):

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    current_company_id = request.session.get("current_company_id")

    current_company = None

    if current_company_id:
        current_company = next(
            (company for company in companies if company.id == current_company_id), None
        )

    if current_company is None and companies:
        current_company = companies[0]
        request.session["current_company_id"] = current_company.id

    return render(
        request,
        "after_login.html",
        {
            "companies": companies,
            "current_company": current_company,
        },
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

    invoices = (
        Invoice.objects.filter(company=current_company)
        .select_related("customer")
        .order_by("-created_at")
    )

    return render(
        request,
        "invoices.html",
        {
            "invoices": invoices,
            "current_company": current_company,
            "companies": companies,
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
        Membership.objects.filter(user=request.user, company_id=current_company_id)
        .select_related("company")
        .first()
    )

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(user=request.user).select_related("company")

    companies = [membership.company for membership in memberships]

    invoices = (
        Invoice.objects.filter(company=current_company)
        .select_related("customer")
        .order_by("-created_at")
    )

    if request.method == "POST":

        invoice_id = request.POST.get("invoice")
        amount_text = request.POST.get("amount")
        payment_method = request.POST.get("payment_method")
        payment_date = request.POST.get("payment_date")
        notes = request.POST.get("notes")

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
                    "error": "Payment amount must be greater than zero.",
                },
            )

        try:
            payment_date_value = date.fromisoformat(payment_date)
        except (ValueError, TypeError):
            return render(
                request,
                "record_payment.html",
                {
                    "current_company": current_company,
                    "companies": companies,
                    "invoices": invoices,
                    "error": "Enter a valid payment date.",
                },
            )

        with transaction.atomic():

            invoice = (
                Invoice.objects.select_for_update()
                .filter(id=invoice_id, company=current_company)
                .first()
            )

            if invoice is None:
                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "error": "Invalid invoice selected.",
                    },
                )

            if invoice.status == "CANCELLED":
                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "error": "Payment cannot be recorded for a cancelled invoice.",
                    },
                )

            paid_amount = invoice.payments.aggregate(total=Sum("amount"))[
                "total"
            ] or Decimal("0.00")

            remaining_amount = invoice.total - paid_amount

            if remaining_amount <= 0:
                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "error": "This invoice has already been fully paid.",
                    },
                )

            if amount > remaining_amount:
                return render(
                    request,
                    "record_payment.html",
                    {
                        "current_company": current_company,
                        "companies": companies,
                        "invoices": invoices,
                        "error": f"Payment cannot exceed the remaining balance of ₹{remaining_amount}.",
                    },
                )

            Payment.objects.create(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date_value,
                notes=notes,
            )

            new_paid_amount = paid_amount + amount

            if new_paid_amount >= invoice.total:
                invoice.status = "PAID"
            elif invoice.due_date < date.today():
                invoice.status = "OVERDUE"
            else:
                invoice.status = "SENT"

            invoice.save(update_fields=["status", "updated_at"])

        return redirect("payments")

    return render(
        request,
        "record_payment.html",
        {
            "current_company": current_company,
            "companies": companies,
            "invoices": invoices,
        },
    )
