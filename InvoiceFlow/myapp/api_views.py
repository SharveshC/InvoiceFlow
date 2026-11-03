from decimal import Decimal, InvalidOperation
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Company, Membership, Customer, Product
from .serializers import UserSerializer, CompanySerializer, CustomerSerializer, ProductSerializer
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
