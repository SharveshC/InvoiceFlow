from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Company, Membership


# HOME
def home(request):
    return render(request, 'index.html')


# LOGIN
def login_page(request):
    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = User.objects.get(email__iexact=email)
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

        return render(request, "login.html", {
            "error": "Invalid email or password."
        })

    return render(request, 'login.html')


# SIGNUP
def signup(request):
    if request.method == "POST":

        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "signup.html", {
                "error": "Passwords do not match."
            })

        if User.objects.filter(email__iexact=email).exists():
            return render(request, "signup.html", {
                "error": "An account with this email already exists."
            })

        username = email

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        user.first_name = full_name
        user.save()

        return redirect("login")

    return render(request, 'signup.html')


# DASHBOARD
@login_required
def dashboard(request):

    memberships = Membership.objects.filter(
        user=request.user
    ).select_related('company')

    companies = [membership.company for membership in memberships]

    current_company_id = request.session.get(
        "current_company_id"
    )

    current_company = None

    # Try to get previously selected company
    if current_company_id:

        current_company = next(
            (
                company
                for company in companies
                if company.id == current_company_id
            ),
            None
        )

    # If no company is selected, use the first company
    if current_company is None and companies:

        current_company = companies[0]

        request.session["current_company_id"] = current_company.id

    return render(
        request,
        'after_login.html',
        {
            "companies": companies,
            "current_company": current_company,
        }
    )


# LOGOUT
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")

    return redirect("home")


# CREATE COMPANY
@login_required
def create_company(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        gst_number = request.POST.get("gst_number")

        # Basic validation
        if not name or not email or not phone or not address:
            return render(request, "create_company.html", {
                "error": "Please fill in all required fields."
            })

        # Create company
        company = Company.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number or None
        )

        # Create membership
        Membership.objects.create(
            user=request.user,
            company=company,
            role="OWNER"
        )

        # Make newly created company the current company
        request.session["current_company_id"] = company.id

        # Go back to dashboard
        return redirect("dashboard")

    return render(request, "create_company.html")