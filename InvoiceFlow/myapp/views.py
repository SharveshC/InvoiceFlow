from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .models import Company, Membership, Customer, Product


def home(request):
    return render(request, "index.html")


def login_page(request):
    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = User.objects.get(
                email__iexact=email
            )
            username = user.username

        except User.DoesNotExist:
            username = None

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        return render(
            request,
            "login.html",
            {
                "error": "Invalid email or password."
            }
        )

    return render(request, "login.html")


def signup(request):
    if request.method == "POST":

        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(
                request,
                "signup.html",
                {
                    "error": "Passwords do not match."
                }
            )

        if User.objects.filter(
            email__iexact=email
        ).exists():
            return render(
                request,
                "signup.html",
                {
                    "error": "An account with this email already exists."
                }
            )

        username = email

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        user.first_name = full_name
        user.save()

        return redirect("login")

    return render(request, "signup.html")


@login_required
def dashboard(request):

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related("company")

    companies = [
        membership.company
        for membership in memberships
    ]

    current_company_id = request.session.get(
        "current_company_id"
    )

    current_company = None

    if current_company_id:
        current_company = next(
            (
                company
                for company in companies
                if company.id == current_company_id
            ),
            None
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
        }
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
                {
                    "error": "Please fill in all required fields."
                }
            )

        company = Company.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number or None
        )

        Membership.objects.create(
            user=request.user,
            company=company,
            role="OWNER"
        )

        request.session["current_company_id"] = company.id

        return redirect("dashboard")

    return render(
        request,
        "create_company.html"
    )


@login_required
def switch_company(request, company_id):

    membership = Membership.objects.filter(
        user=request.user,
        company_id=company_id
    ).first()

    if membership is None:
        return redirect("dashboard")

    request.session["current_company_id"] = company_id

    return redirect("dashboard")


@login_required
def clients(request):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).select_related("company").first()

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related("company")

    companies = [
        membership.company
        for membership in memberships
    ]

    customers = Customer.objects.filter(
        company=current_company
    ).order_by("-created_at")

    return render(
        request,
        "clients.html",
        {
            "customers": customers,
            "current_company": current_company,
            "companies": companies,
        }
    )


@login_required
def add_client(request):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).select_related("company").first()

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related("company")

    companies = [
        membership.company
        for membership in memberships
    ]

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
                    "error": "Please fill in all required fields."
                }
            )

        Customer.objects.create(
            company=current_company,
            name=name,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number or None
        )

        return redirect("clients")

    return render(
        request,
        "add_client.html",
        {
            "current_company": current_company,
            "companies": companies,
        }
    )
    
    
@login_required
def edit_client(request, client_id):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).select_related("company").first()

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related("company")

    companies = [
        membership.company
        for membership in memberships
    ]

    customer = Customer.objects.filter(
        id=client_id,
        company=current_company
    ).first()

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
                    "error": "Please fill in all required fields."
                }
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
        }
    )
    
@login_required
def delete_client(request, client_id):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).select_related("company").first()

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    customer = Customer.objects.filter(
        id=client_id,
        company=current_company
    ).first()

    if customer is None:
        return redirect("clients")

    if request.method == "POST":
        customer.delete()
        return redirect("clients")

    return redirect("clients")


@login_required
def products(request):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).select_related("company").first()

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related("company")

    companies = [
        membership.company
        for membership in memberships
    ]

    products = Product.objects.filter(
        company=current_company
    ).order_by("-created_at")

    return render(
        request,
        "products.html",
        {
            "products": products,
            "current_company": current_company,
            "companies": companies,
        }
    )
    
@login_required
def add_product(request):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).select_related("company").first()

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related("company")

    companies = [
        membership.company
        for membership in memberships
    ]

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
                    "error": "Product name and price are required."
                }
            )

        Product.objects.create(
            company=current_company,
            name=name,
            description=description or None,
            price=price,
            tax=tax or 0
        )

        return redirect("products")

    return render(
        request,
        "add_product.html",
        {
            "current_company": current_company,
            "companies": companies,
        }
    )
    

@login_required
def edit_product(request, product_id):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).select_related("company").first()

    if membership is None:
        return redirect("dashboard")

    current_company = membership.company

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related("company")

    companies = [
        membership.company
        for membership in memberships
    ]

    product = Product.objects.filter(
        id=product_id,
        company=current_company
    ).first()

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
                    "error": "Product name and price are required."
                }
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
        }
    )
    
@login_required
def delete_product(request, product_id):

    current_company_id = request.session.get(
        "current_company_id"
    )

    if not current_company_id:
        return redirect("dashboard")

    membership = Membership.objects.filter(
        user=request.user,
        company_id=current_company_id
    ).first()

    if membership is None:
        return redirect("dashboard")

    product = Product.objects.filter(
        id=product_id,
        company_id=current_company_id
    ).first()

    if product is None:
        return redirect("products")

    if request.method == "POST":
        product.delete()
        return redirect("products")

    return redirect("products")