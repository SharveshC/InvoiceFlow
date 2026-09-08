from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def home(request):
    return render (request,'index.html')

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
            return redirect("home")

        return render(request, "login.html", {
            "error": "Invalid email or password."
        })
        
    return render(request,'login.html')

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
    
    return render(request,'signup.html')