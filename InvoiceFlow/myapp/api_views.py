from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import ProtectedError, Q, Sum
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Company, Membership, Customer, Product, Invoice, InvoiceItem, Payment
from .serializers import (
    UserSerializer,
    CompanySerializer,
    CustomerSerializer,
    ProductSerializer,
    InvoiceSerializer,
    InvoiceItemSerializer,
    PaymentSerializer,
)
from .views import get_user_company_context


def get_user_companies_with_role(user):
    """
    Helper to fetch and serialize all companies belonging to the user,
    including their membership role (OWNER, ADMIN, STAFF).
    """
    memberships = (
        Membership.objects.filter(user=user)
        .select_related("company")
        .order_by("created_at")
    )
    result = []
    for m in memberships:
        c_data = CompanySerializer(m.company).data
        c_data["role"] = m.role
        result.append(c_data)
    return result


@api_view(["GET"])
@permission_classes([AllowAny])
def api_health_check(request):
    """
    Health check endpoint to verify Django REST Framework and frontend connectivity.
    Does not interfere with any existing template views.
    """
    return Response(
        {
            "status": "ok",
            "message": "InvoiceFlow API is running",
            "version": "1.0",
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def api_csrf_token(request):
    """
    Sets the Django CSRF cookie and returns the token for client requests.
    """
    token = get_token(request)
    return Response({"csrftoken": token})


@api_view(["POST"])
@permission_classes([AllowAny])
def api_signup(request):
    """
    Register a new user account and log them in.
    Reuses existing validation and User model creation logic.
    """
    full_name = (request.data.get("full_name") or "").strip()
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password") or ""
    confirm_password = request.data.get("confirm_password") or ""

    if not full_name or not email or not password or not confirm_password:
        return Response(
            {"error": "Please fill in all required fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != confirm_password:
        return Response(
            {"error": "Passwords do not match."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    normalized_email = email.lower()
    username = normalized_email[:150]

    if (
        User.objects.filter(email__iexact=normalized_email).exists()
        or User.objects.filter(username__iexact=username).exists()
    ):
        return Response(
            {"error": "An account with this email already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username,
        email=normalized_email,
        password=password,
        first_name=full_name[:150],
    )

    authenticated_user = authenticate(request, username=username, password=password)
    if authenticated_user is not None and authenticated_user.is_active:
        login(request, authenticated_user)

    return Response(
        {
            "message": "Signup successful",
            "user": UserSerializer(user).data,
            "current_company": None,
            "companies": [],
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    """
    Authenticate a user using email and password, creating a Django session.
    Returns user details and company context (handles zero or multiple companies).
    """
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password") or ""

    if not email or not password:
        return Response(
            {"error": "Please enter your email and password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_obj = (
        User.objects.filter(email__iexact=email).first()
        or User.objects.filter(username__iexact=email).first()
    )

    if user_obj is None or not user_obj.is_active:
        return Response(
            {"error": "Invalid email or password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=user_obj.username, password=password)

    if user is not None and user.is_active:
        login(request, user)
        current_company, _ = get_user_company_context(request)
        companies = get_user_companies_with_role(user)
        current_company_data = None
        if current_company:
            current_membership = Membership.objects.filter(
                user=user, company=current_company
            ).first()
            current_company_data = CompanySerializer(current_company).data
            current_company_data["role"] = current_membership.role if current_membership else "STAFF"

        return Response(
            {
                "message": "Login successful",
                "user": UserSerializer(user).data,
                "current_company": current_company_data,
                "companies": companies,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {"error": "Invalid email or password."},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def api_logout(request):
    """
    Terminate the current Django session.
    """
    logout(request)
    return Response(
        {"message": "Logged out successfully"},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def api_current_user(request):
    """
    Check current authentication status and return user and company profile.
    Safely handles unauthenticated users, users with no companies, and multi-company users.
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "isAuthenticated": False,
                "user": None,
                "current_company": None,
                "companies": [],
            },
            status=status.HTTP_200_OK,
        )

    current_company, _ = get_user_company_context(request)
    companies = get_user_companies_with_role(request.user)
    current_company_data = None
    if current_company:
        current_membership = Membership.objects.filter(
            user=request.user, company=current_company
        ).first()
        current_company_data = CompanySerializer(current_company).data
        current_company_data["role"] = current_membership.role if current_membership else "STAFF"

    return Response(
        {
            "isAuthenticated": True,
            "user": UserSerializer(request.user).data,
            "current_company": current_company_data,
            "companies": companies,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_create_company(request):
    """
    Create a new company profile and set the user as OWNER.
    Uses transaction.atomic() to ensure consistency.
    """
    name = (request.data.get("name") or "").strip()
    email = (request.data.get("email") or "").strip()
    phone = (request.data.get("phone") or "").strip()
    address = (request.data.get("address") or "").strip()
    gst_number = (request.data.get("gst_number") or "").strip()

    if not name or not email or not phone or not address:
        return Response(
            {"error": "Please fill in all required fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        company = Company.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number or None,
        )
        Membership.objects.create(user=request.user, company=company, role="OWNER")

    request.session["current_company_id"] = company.id

    companies = get_user_companies_with_role(request.user)
    current_company_data = CompanySerializer(company).data
    current_company_data["role"] = "OWNER"

    return Response(
        {
            "message": "Company created successfully",
            "company": current_company_data,
            "current_company": current_company_data,
            "companies": companies,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_switch_company(request, company_id):
    """
    Switch the active company in the user's session.
    Verifies membership and returns 403 if unauthorized.
    """
    membership = Membership.objects.filter(
        user=request.user, company_id=company_id
    ).select_related("company").first()

    if membership is None:
        return Response(
            {"error": "You do not have access to this company."},
            status=status.HTTP_403_FORBIDDEN,
        )

    request.session["current_company_id"] = company_id
    companies = get_user_companies_with_role(request.user)
    current_company_data = CompanySerializer(membership.company).data
    current_company_data["role"] = membership.role

    return Response(
        {
            "message": "Switched company successfully",
            "current_company": current_company_data,
            "companies": companies,
        },
        status=status.HTTP_200_OK,
    )


# ==========================================
# PHASE 4: CUSTOMER MANAGEMENT APIS
# ==========================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_customers_list_create(request):
    """
    List, search, and create customers for the authenticated user's active company.
    Strictly isolated to current_company.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found. Please select or create a company first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "GET":
        search = (request.query_params.get("search") or request.query_params.get("q") or "").strip()
        customers = Customer.objects.filter(company=current_company)
        if search:
            customers = customers.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(gst_number__icontains=search)
            )
        customers = customers.order_by("-created_at")
        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "POST":
        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()
        phone = (request.data.get("phone") or "").strip()
        address = (request.data.get("address") or "").strip()
        gst_number = (request.data.get("gst_number") or "").strip()

        if not name or not email or not phone or not address:
            return Response(
                {"error": "Please fill in all required fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer.objects.create(
            company=current_company,
            name=name,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number or None,
        )

        return Response(
            {
                "message": "Customer created successfully",
                "customer": CustomerSerializer(customer).data,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def api_customer_detail(request, customer_id):
    """
    Retrieve, update, or delete a specific customer.
    Enforces active-company scoping and prevents cross-company access.
    Handles ProtectedError if customer is linked to existing invoices.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    customer = Customer.objects.filter(id=customer_id, company=current_company).first()
    if customer is None:
        return Response(
            {"error": "Customer not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(
            {"customer": CustomerSerializer(customer).data},
            status=status.HTTP_200_OK,
        )

    if request.method in ["PUT", "PATCH"]:
        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()
        phone = (request.data.get("phone") or "").strip()
        address = (request.data.get("address") or "").strip()
        gst_number = (request.data.get("gst_number") or "").strip()

        if not name or not email or not phone or not address:
            return Response(
                {"error": "Please fill in all required fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer.name = name
        customer.email = email
        customer.phone = phone
        customer.address = address
        customer.gst_number = gst_number or None
        customer.save()

        return Response(
            {
                "message": "Customer updated successfully",
                "customer": CustomerSerializer(customer).data,
            },
            status=status.HTTP_200_OK,
        )

    if request.method == "DELETE":
        try:
            customer.delete()
            return Response(
                {"message": "Customer deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except ProtectedError:
            return Response(
                {"error": "Cannot delete client because they are linked to existing invoices."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==========================================
# PHASE 5: PRODUCT MANAGEMENT APIS
# ==========================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_products_list_create(request):
    """
    List, search, and create products for the authenticated user's active company.
    Strictly isolated to current_company.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found. Please select or create a company first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "GET":
        search = (request.query_params.get("search") or request.query_params.get("q") or "").strip()
        products = Product.objects.filter(company=current_company)
        if search:
            products = products.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
            )
        products = products.order_by("-created_at")
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "POST":
        name = (request.data.get("name") or "").strip()
        description = (request.data.get("description") or "").strip()
        price_val = request.data.get("price")
        tax_val = request.data.get("tax")

        if not name or price_val is None or str(price_val).strip() == "":
            return Response(
                {"error": "Product name and price are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            price = Decimal(str(price_val).strip())
            tax = Decimal(str(tax_val).strip()) if (tax_val is not None and str(tax_val).strip() != "") else Decimal("0")
            if price < 0 or tax < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response(
                {"error": "Please enter valid numbers for price and tax."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = Product.objects.create(
            company=current_company,
            name=name,
            description=description or None,
            price=price,
            tax=tax,
        )

        return Response(
            {
                "message": "Product created successfully",
                "product": ProductSerializer(product).data,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def api_product_detail(request, product_id):
    """
    Retrieve, update, or delete a specific product.
    Enforces active-company scoping and prevents cross-company access.
    Handles ProtectedError if product is linked to existing invoice items.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product = Product.objects.filter(id=product_id, company=current_company).first()
    if product is None:
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(
            {"product": ProductSerializer(product).data},
            status=status.HTTP_200_OK,
        )

    if request.method in ["PUT", "PATCH"]:
        name = (request.data.get("name") or "").strip()
        description = (request.data.get("description") or "").strip()
        price_val = request.data.get("price")
        tax_val = request.data.get("tax")

        if not name or price_val is None or str(price_val).strip() == "":
            return Response(
                {"error": "Product name and price are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            price = Decimal(str(price_val).strip())
            tax = Decimal(str(tax_val).strip()) if (tax_val is not None and str(tax_val).strip() != "") else Decimal("0")
            if price < 0 or tax < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response(
                {"error": "Please enter valid numbers for price and tax."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product.name = name
        product.description = description or None
        product.price = price
        product.tax = tax
        product.save()

        return Response(
            {
                "message": "Product updated successfully",
                "product": ProductSerializer(product).data,
            },
            status=status.HTTP_200_OK,
        )

    if request.method == "DELETE":
        try:
            product.delete()
            return Response(
                {"message": "Product deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except ProtectedError:
            return Response(
                {"error": "Cannot delete product because it is linked to existing invoice items."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==========================================
# PHASE 6: INVOICE MANAGEMENT APIS
# ==========================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_invoices_list_create(request):
    """
    List, search, filter, and create invoices for the authenticated user's active company.
    Strictly isolated to current_company.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found. Please select or create a company first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "GET":
        today = date.today()
        # Update overdue invoices dynamically matching Django HTML behavior
        Invoice.objects.filter(
            company=current_company,
            status__in=["DRAFT", "SENT"],
            due_date__lt=today,
        ).update(status="OVERDUE")

        search = (request.query_params.get("search") or request.query_params.get("q") or "").strip()
        status_filter = (request.query_params.get("status") or "").strip()

        invoices = (
            Invoice.objects.filter(company=current_company)
            .select_related("customer")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        if search:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search)
                | Q(customer__name__icontains=search)
            )

        if status_filter and status_filter.upper() != "ALL":
            invoices = invoices.filter(status=status_filter.upper())

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "POST":
        invoice_number = (request.data.get("invoice_number") or "").strip()
        customer_id = request.data.get("customer")
        issue_date_str = str(request.data.get("issue_date") or "").strip()
        due_date_str = str(request.data.get("due_date") or "").strip()
        discount_val = request.data.get("discount", "0")
        notes = (request.data.get("notes") or "").strip()
        items_data = request.data.get("items") or []

        if not invoice_number:
            return Response(
                {"error": "Invoice number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Invoice.objects.filter(company=current_company, invoice_number__iexact=invoice_number).exists():
            return Response(
                {"error": "Invoice number already exists for this company."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not customer_id:
            return Response(
                {"error": "Please select a customer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer.objects.filter(id=customer_id, company=current_company).first()
        if not customer:
            return Response(
                {"error": "Invalid customer selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            issue_date = date.fromisoformat(issue_date_str)
            due_date = date.fromisoformat(due_date_str)
        except (ValueError, TypeError):
            return Response(
                {"error": "Please enter valid issue and due dates."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if due_date < issue_date:
            return Response(
                {"error": "Due date cannot be before the issue date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            discount = Decimal(str(discount_val or "0").strip())
            if discount < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response(
                {"error": "Invalid discount amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not items_data or len(items_data) == 0:
            return Response(
                {"error": "Please add at least one invoice item."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_items = []
        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")

        for item in items_data:
            prod_id = item.get("product")
            if not prod_id:
                return Response(
                    {"error": "Product is required for each line item."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            prod = Product.objects.filter(id=prod_id, company=current_company).first()
            if not prod:
                return Response(
                    {"error": "Invalid product selected."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                qty = Decimal(str(item.get("quantity", "1")).strip())
                price = Decimal(str(item.get("unit_price", prod.price)).strip())
                tax_rate = (
                    Decimal(str(item.get("tax", prod.tax)).strip())
                    if item.get("tax") is not None and str(item.get("tax")).strip() != ""
                    else Decimal("0.00")
                )

                if qty <= 0:
                    return Response(
                        {"error": "Quantity must be greater than zero."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if price < 0:
                    return Response(
                        {"error": "Unit price cannot be negative."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if tax_rate < 0:
                    return Response(
                        {"error": "Tax cannot be negative."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except (InvalidOperation, ValueError):
                return Response(
                    {"error": "Please enter valid numeric values for invoice items."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            line_subtotal = qty * price
            line_tax = (line_subtotal * tax_rate) / Decimal("100")
            line_total = line_subtotal + line_tax

            subtotal += line_subtotal
            total_tax += line_tax

            validated_items.append({
                "product": prod,
                "quantity": qty,
                "unit_price": price,
                "tax": tax_rate,
                "discount": Decimal("0.00"),
                "line_total": line_total,
            })

        total = subtotal + total_tax - discount
        if total < 0:
            total = Decimal("0.00")

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
                notes=notes or None,
            )

            for v_item in validated_items:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=v_item["product"],
                    quantity=v_item["quantity"],
                    unit_price=v_item["unit_price"],
                    tax=v_item["tax"],
                    discount=v_item["discount"],
                    line_total=v_item["line_total"],
                )

        return Response(
            {
                "message": "Invoice created successfully",
                "invoice": InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def api_invoice_detail(request, invoice_id):
    """
    Retrieve or update a specific invoice.
    Enforces active-company scoping, payment restrictions, and recalculates totals on the backend.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    invoice = (
        Invoice.objects.filter(id=invoice_id, company=current_company)
        .select_related("customer")
        .prefetch_related("items__product")
        .first()
    )

    if invoice is None:
        return Response(
            {"error": "Invoice not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        today = date.today()
        if invoice.status in ["DRAFT", "SENT"] and invoice.due_date < today:
            invoice.status = "OVERDUE"
            invoice.save(update_fields=["status"])

        payments = Payment.objects.filter(invoice=invoice).order_by("-payment_date", "-created_at")
        paid_amount = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        remaining_amount = max(invoice.total - paid_amount, Decimal("0.00"))

        return Response(
            {
                "invoice": InvoiceSerializer(invoice).data,
                "customer": CustomerSerializer(invoice.customer).data,
                "payments": PaymentSerializer(payments, many=True).data,
                "paid_amount": str(paid_amount),
                "remaining_amount": str(remaining_amount),
            },
            status=status.HTTP_200_OK,
        )

    if request.method in ["PUT", "PATCH"]:
        if invoice.status in ["PAID", "CANCELLED"]:
            return Response(
                {"error": f"Cannot edit an invoice that is already {invoice.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Payment.objects.filter(invoice=invoice).exists():
            return Response(
                {"error": "Cannot edit an invoice that has recorded payments."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice_number = (request.data.get("invoice_number") or "").strip()
        customer_id = request.data.get("customer")
        issue_date_str = str(request.data.get("issue_date") or "").strip()
        due_date_str = str(request.data.get("due_date") or "").strip()
        discount_val = request.data.get("discount", "0")
        notes = (request.data.get("notes") or "").strip()
        items_data = request.data.get("items") or []

        if not invoice_number:
            return Response(
                {"error": "Invoice number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            Invoice.objects.filter(company=current_company, invoice_number__iexact=invoice_number)
            .exclude(id=invoice.id)
            .exists()
        ):
            return Response(
                {"error": "Invoice number already exists for this company."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not customer_id:
            return Response(
                {"error": "Please select a customer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer.objects.filter(id=customer_id, company=current_company).first()
        if not customer:
            return Response(
                {"error": "Invalid customer selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            issue_date = date.fromisoformat(issue_date_str)
            due_date = date.fromisoformat(due_date_str)
        except (ValueError, TypeError):
            return Response(
                {"error": "Please enter valid issue and due dates."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if due_date < issue_date:
            return Response(
                {"error": "Due date cannot be before the issue date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            discount = Decimal(str(discount_val or "0").strip())
            if discount < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response(
                {"error": "Invalid discount amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not items_data or len(items_data) == 0:
            return Response(
                {"error": "Please add at least one invoice item."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_items = []
        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")

        for item in items_data:
            prod_id = item.get("product")
            if not prod_id:
                return Response(
                    {"error": "Product is required for each line item."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            prod = Product.objects.filter(id=prod_id, company=current_company).first()
            if not prod:
                return Response(
                    {"error": "Invalid product selected."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                qty = Decimal(str(item.get("quantity", "1")).strip())
                price = Decimal(str(item.get("unit_price", prod.price)).strip())
                tax_rate = (
                    Decimal(str(item.get("tax", prod.tax)).strip())
                    if item.get("tax") is not None and str(item.get("tax")).strip() != ""
                    else Decimal("0.00")
                )

                if qty <= 0:
                    return Response(
                        {"error": "Quantity must be greater than zero."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if price < 0:
                    return Response(
                        {"error": "Unit price cannot be negative."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if tax_rate < 0:
                    return Response(
                        {"error": "Tax cannot be negative."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except (InvalidOperation, ValueError):
                return Response(
                    {"error": "Please enter valid numeric values for invoice items."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            line_subtotal = qty * price
            line_tax = (line_subtotal * tax_rate) / Decimal("100")
            line_total = line_subtotal + line_tax

            subtotal += line_subtotal
            total_tax += line_tax

            validated_items.append({
                "product": prod,
                "quantity": qty,
                "unit_price": price,
                "tax": tax_rate,
                "discount": Decimal("0.00"),
                "line_total": line_total,
            })

        total = subtotal + total_tax - discount
        if total < 0:
            total = Decimal("0.00")

        # Determine new status based on due date
        today = date.today()
        new_status = "OVERDUE" if due_date < today else "SENT"

        with transaction.atomic():
            invoice.invoice_number = invoice_number
            invoice.customer = customer
            invoice.issue_date = issue_date
            invoice.due_date = due_date
            invoice.status = new_status
            invoice.subtotal = subtotal
            invoice.tax_amount = total_tax
            invoice.discount_amount = discount
            invoice.total = total
            invoice.notes = notes or None
            invoice.save()

            # Atomically replace items
            invoice.items.all().delete()
            for v_item in validated_items:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=v_item["product"],
                    quantity=v_item["quantity"],
                    unit_price=v_item["unit_price"],
                    tax=v_item["tax"],
                    discount=v_item["discount"],
                    line_total=v_item["line_total"],
                )

        return Response(
            {
                "message": "Invoice updated successfully",
                "invoice": InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_invoice_cancel(request, invoice_id):
    """
    Cancel an existing invoice.
    Enforces active-company scoping and blocks cancellation if PAID or already CANCELLED.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    invoice = Invoice.objects.filter(id=invoice_id, company=current_company).first()
    if invoice is None:
        return Response(
            {"error": "Invoice not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if invoice.status == "PAID":
        return Response(
            {"error": "Paid invoices cannot be cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if invoice.status == "CANCELLED":
        return Response(
            {"error": "Invoice is already cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    invoice.status = "CANCELLED"
    invoice.save(update_fields=["status"])

    return Response(
        {
            "message": "Invoice cancelled successfully",
            "invoice": InvoiceSerializer(invoice).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_payments_list_create(request):
    """
    List payments or record a new payment.
    Scoped strictly to the user's active company via invoice__company.
    Guarantees company isolation, atomic row locks with select_for_update,
    overpayment prevention, and automatic invoice status updates.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "GET":
        payments = (
            Payment.objects.filter(invoice__company=current_company)
            .select_related("invoice", "invoice__customer")
            .order_by("-payment_date", "-created_at")
        )

        search = (request.GET.get("search") or request.GET.get("q") or "").strip()
        if search:
            payments = payments.filter(
                Q(invoice__invoice_number__icontains=search)
                | Q(invoice__customer__name__icontains=search)
            )

        invoice_id = request.GET.get("invoice_id")
        if invoice_id:
            payments = payments.filter(invoice_id=invoice_id)

        method = request.GET.get("method")
        if method:
            payments = payments.filter(payment_method=method.strip().upper())

        # Active company payment metrics
        company_payments = Payment.objects.filter(invoice__company=current_company)
        total_received = company_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        today = date.today()
        this_month = company_payments.filter(
            payment_date__year=today.year, payment_date__month=today.month
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        payment_count = company_payments.count()

        return Response(
            {
                "payments": PaymentSerializer(payments, many=True).data,
                "stats": {
                    "total_received": str(total_received),
                    "this_month": str(this_month),
                    "payment_count": payment_count,
                },
            },
            status=status.HTTP_200_OK,
        )

    if request.method == "POST":
        invoice_id = request.data.get("invoice") or request.data.get("invoice_id")
        amount_val = request.data.get("amount")
        payment_method = str(request.data.get("payment_method") or "").strip().upper()
        payment_date_str = str(request.data.get("payment_date") or "").strip()
        notes = (request.data.get("notes") or "").strip()

        if not invoice_id:
            return Response(
                {"error": "Please select an invoice."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(amount_val).strip())
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"error": "Enter a valid payment amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount <= Decimal("0.00"):
            return Response(
                {"error": "Payment amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment_date_value = date.fromisoformat(payment_date_str)
        except (ValueError, TypeError):
            return Response(
                {"error": "Enter a valid payment date (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_methods = [choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES]
        if payment_method not in valid_methods:
            return Response(
                {"error": f"Invalid payment method. Choices are: {', '.join(valid_methods)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Pre-flight checks before acquiring database row lock
        invoice_check = Invoice.objects.filter(id=invoice_id, company=current_company).first()
        if invoice_check is None:
            return Response(
                {"error": "Invalid invoice selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invoice_check.status == "CANCELLED":
            return Response(
                {"error": "Payment cannot be recorded for a cancelled invoice."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            invoice = (
                Invoice.objects.select_for_update()
                .filter(id=invoice_id, company=current_company)
                .first()
            )
            if invoice is None:
                return Response(
                    {"error": "Invalid invoice selected."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            paid_amount = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            remaining_amount = invoice.total - paid_amount

            if remaining_amount <= Decimal("0.00"):
                return Response(
                    {"error": "This invoice has already been fully paid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if amount > remaining_amount:
                return Response(
                    {"error": f"Payment cannot exceed the remaining balance of ₹{remaining_amount}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment = Payment.objects.create(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date_value,
                notes=notes or None,
            )

            new_paid_amount = paid_amount + amount
            new_remaining_amount = max(invoice.total - new_paid_amount, Decimal("0.00"))

            if new_paid_amount >= invoice.total:
                invoice.status = "PAID"
            elif invoice.due_date < date.today():
                invoice.status = "OVERDUE"
            else:
                invoice.status = "SENT"
            invoice.save(update_fields=["status"])

        return Response(
            {
                "message": "Payment recorded successfully",
                "payment": PaymentSerializer(payment).data,
                "invoice_status": invoice.status,
                "paid_amount": str(new_paid_amount),
                "remaining_amount": str(new_remaining_amount),
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_payment_detail(request, payment_id):
    """
    Retrieve details of a single payment.
    Scoped strictly to the user's active company via invoice__company.
    Payments are immutable: no PUT/PATCH/DELETE endpoints.
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payment = (
        Payment.objects.filter(id=payment_id, invoice__company=current_company)
        .select_related("invoice", "invoice__customer")
        .first()
    )
    if payment is None:
        return Response(
            {"error": "Payment not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reports_summary(request):
    """
    Financial Reports and Analytics Endpoint.
    Strictly scoped to the user's active company.
    Provides:
      - Revenue Invoiced (filtered by issue_date)
      - Revenue Collected (filtered by payment_date)
      - Total Current Outstanding Balance (point-in-time)
      - Total Current Overdue Balance (point-in-time)
      - Invoice Status Breakdown (all 5 statuses: PAID, SENT, OVERDUE, DRAFT, CANCELLED)
      - Monthly Trend (Invoiced vs Collected for 6 months or range)
      - Top 5 Customers by invoiced amount (without join double-counting)
      - Payment Method Breakdown (CASH, UPI, CARD, BANK)
      - Collection efficiency percentage
    """
    current_company, _ = get_user_company_context(request)
    if current_company is None:
        return Response(
            {"error": "No active company profile found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    today = date.today()
    preset = (request.GET.get("preset") or "").strip().lower()
    start_date_str = (request.GET.get("start_date") or "").strip()
    end_date_str = (request.GET.get("end_date") or "").strip()

    start_date = None
    end_date = None

    if start_date_str or end_date_str:
        if start_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid start_date format. Expected YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid end_date format. Expected YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if start_date and end_date and start_date > end_date:
            return Response(
                {"error": "start_date cannot be after end_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    elif preset:
        if preset == "30d":
            start_date = today - timedelta(days=30)
            end_date = today
        elif preset == "this_month":
            start_date = date(today.year, today.month, 1)
            end_date = today
        elif preset == "6m":
            start_year = today.year
            start_month = today.month - 5
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            start_date = date(start_year, start_month, 1)
            end_date = today
        elif preset == "year":
            start_date = date(today.year, 1, 1)
            end_date = today
        elif preset == "all":
            start_date = None
            end_date = None
        else:
            return Response(
                {"error": f"Invalid preset '{preset}'. Valid presets: 30d, this_month, 6m, year, all."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        # Default to 6m
        start_year = today.year
        start_month = today.month - 5
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        start_date = date(start_year, start_month, 1)
        end_date = today

    # 1. Base querysets scoped to current_company
    all_invoices = Invoice.objects.filter(company=current_company)
    all_payments = Payment.objects.filter(invoice__company=current_company)

    # 2. Revenue Invoiced (filtered by issue_date, excluding CANCELLED)
    invoiced_qs = all_invoices.exclude(status="CANCELLED")
    if start_date:
        invoiced_qs = invoiced_qs.filter(issue_date__gte=start_date)
    if end_date:
        invoiced_qs = invoiced_qs.filter(issue_date__lte=end_date)

    total_invoiced = invoiced_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    # 3. Revenue Collected (filtered by payment_date)
    collected_qs = all_payments
    if start_date:
        collected_qs = collected_qs.filter(payment_date__gte=start_date)
    if end_date:
        collected_qs = collected_qs.filter(payment_date__lte=end_date)

    total_collected = collected_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # 4. Total Current Outstanding & Overdue Balances (point-in-time, actual balance of active invoices)
    active_unpaid_invoices = all_invoices.exclude(status__in=["PAID", "CANCELLED"])
    total_outstanding = Decimal("0.00")
    total_overdue = Decimal("0.00")

    for inv in active_unpaid_invoices:
        inv_paid = inv.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        inv_remaining = inv.total - inv_paid
        if inv_remaining > Decimal("0.00"):
            total_outstanding += inv_remaining
            if inv.due_date < today:
                total_overdue += inv_remaining

    # 5. Collection Efficiency Rate (guarded against division by zero)
    if total_invoiced > Decimal("0.00"):
        collection_rate = float(round((total_collected / total_invoiced) * Decimal("100.00"), 1))
    else:
        collection_rate = 0.0

    # 6. Invoice Status Breakdown (all 5 statuses: PAID, SENT, OVERDUE, DRAFT, CANCELLED)
    status_filter_qs = all_invoices
    if start_date:
        status_filter_qs = status_filter_qs.filter(issue_date__gte=start_date)
    if end_date:
        status_filter_qs = status_filter_qs.filter(issue_date__lte=end_date)

    status_data = {}
    for st_code, st_label in Invoice.STATUS_CHOICES:
        qs_st = status_filter_qs.filter(status=st_code)
        st_count = qs_st.count()
        st_amount = qs_st.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        status_data[st_code] = {
            "label": st_label,
            "count": st_count,
            "total_amount": str(st_amount),
        }

    total_invoices_count = status_filter_qs.count()

    # 7. Monthly Trend (6 months sequence up to today)
    months_list = []
    for i in range(5, -1, -1):
        m_year = today.year
        m_month = today.month - i
        while m_month <= 0:
            m_month += 12
            m_year -= 1
        m_start = date(m_year, m_month, 1)
        if m_month == 12:
            m_end = date(m_year, 12, 31)
        else:
            m_end = date(m_year, m_month + 1, 1) - timedelta(days=1)

        m_label = m_start.strftime("%b %Y")

        m_invoiced = all_invoices.exclude(status="CANCELLED").filter(
            issue_date__gte=m_start, issue_date__lte=m_end
        ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")

        m_collected = all_payments.filter(
            payment_date__gte=m_start, payment_date__lte=m_end
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        months_list.append({
            "month": m_label,
            "year": m_year,
            "month_num": m_month,
            "invoiced": str(m_invoiced),
            "collected": str(m_collected),
        })

    # 8. Top 5 Customers by invoiced amount (without join double-counting)
    customer_ids = (
        all_invoices.exclude(status="CANCELLED")
        .values("customer_id")
        .annotate(total_invoiced=Sum("total"))
        .order_by("-total_invoiced")[:5]
    )

    top_customers = []
    for c_entry in customer_ids:
        cid = c_entry["customer_id"]
        c_obj = Customer.objects.filter(id=cid, company=current_company).first()
        if c_obj:
            c_invoices = all_invoices.filter(customer=c_obj).exclude(status="CANCELLED")
            c_inv_count = c_invoices.count()
            c_total_invoiced = c_entry["total_invoiced"] or Decimal("0.00")
            c_total_collected = all_payments.filter(invoice__customer=c_obj).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")
            c_outstanding = max(c_total_invoiced - c_total_collected, Decimal("0.00"))

            top_customers.append({
                "id": c_obj.id,
                "name": c_obj.name,
                "invoice_count": c_inv_count,
                "total_invoiced": str(c_total_invoiced),
                "total_collected": str(c_total_collected),
                "outstanding": str(c_outstanding),
            })

    # 9. Payment Methods Breakdown (CASH, UPI, CARD, BANK)
    methods_breakdown = []
    total_method_amount = collected_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    for method_code, method_label in Payment.PAYMENT_METHOD_CHOICES:
        m_qs = collected_qs.filter(payment_method=method_code)
        m_count = m_qs.count()
        m_sum = m_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        if total_method_amount > Decimal("0.00"):
            m_pct = float(round((m_sum / total_method_amount) * Decimal("100.00"), 1))
        else:
            m_pct = 0.0

        methods_breakdown.append({
            "method": method_code,
            "display": method_label,
            "count": m_count,
            "amount": str(m_sum),
            "percentage": m_pct,
        })

    return Response(
        {
            "metrics": {
                "total_invoiced": str(total_invoiced),
                "total_collected": str(total_collected),
                "total_outstanding": str(total_outstanding),
                "overdue_amount": str(total_overdue),
                "collection_rate": collection_rate,
            },
            "invoice_counts": {
                "total": total_invoices_count,
                **status_data,
            },
            "monthly_trend": months_list,
            "top_customers": top_customers,
            "payment_methods": methods_breakdown,
            "date_range": {
                "preset": preset or "6m",
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        },
        status=status.HTTP_200_OK,
    )
