from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from .models import Company, Customer, Invoice, InvoiceItem, Membership, Product


class InvoiceFlowBugFixTests(TestCase):

    def setUp(self):
        self.client = Client()

        # User without company
        self.user_no_company = User.objects.create_user(
            username="nocompany@example.com",
            email="nocompany@example.com",
            password="password123",
        )

        # User with company
        self.user_with_company = User.objects.create_user(
            username="hascompany@example.com",
            email="hascompany@example.com",
            password="password123",
        )
        self.company = Company.objects.create(
            name="Acme Corp",
            email="info@acme.com",
            phone="1234567890",
            address="123 Street",
        )
        self.membership = Membership.objects.create(
            user=self.user_with_company,
            company=self.company,
            role="OWNER",
        )

    def test_user_without_company_onboarding_dashboard(self):
        self.client.force_login(self.user_no_company)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Welcome to InvoiceFlow! To get started, please create your company profile.",
        )
        self.assertContains(response, reverse("create_company"))

    def test_user_without_company_redirects_to_create_company(self):
        self.client.force_login(self.user_no_company)
        routes = [
            "invoices",
            "create_invoice",
            "clients",
            "add_client",
            "products",
            "add_product",
            "payments",
            "record_payment",
            "export_report",
        ]
        create_company_url = reverse("create_company")
        for route in routes:
            response = self.client.get(reverse(route))
            self.assertEqual(
                response.status_code,
                302,
                f"Expected {route} to redirect, got {response.status_code}",
            )
            self.assertRedirects(response, create_company_url)

    def test_user_with_company_access_and_no_onboarding_banner(self):
        self.client.force_login(self.user_with_company)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            "Welcome to InvoiceFlow! To get started, please create your company profile.",
        )
        self.assertContains(response, "Acme Corp")

        # Invoices and products work for user with company
        self.assertEqual(self.client.get(reverse("invoices")).status_code, 200)
        self.assertEqual(self.client.get(reverse("products")).status_code, 200)
        self.assertEqual(self.client.get(reverse("clients")).status_code, 200)

    def test_session_resolution_fallback_and_tampered_id(self):
        self.client.force_login(self.user_with_company)
        session = self.client.session
        session["current_company_id"] = 99999  # Tampered / invalid ID
        session.save()

        response = self.client.get(reverse("invoices"))
        self.assertEqual(response.status_code, 200)
        # Should have fallen back to user's company
        self.assertEqual(self.client.session["current_company_id"], self.company.id)

    def test_protected_client_deletion_handling(self):
        self.client.force_login(self.user_with_company)
        customer = Customer.objects.create(
            company=self.company,
            name="John Doe",
            email="john@example.com",
            phone="1111111111",
            address="Addr",
        )
        Invoice.objects.create(
            company=self.company,
            customer=customer,
            invoice_number="INV-101",
            issue_date=date.today(),
            due_date=date.today(),
        )

        response = self.client.post(reverse("delete_client", args=[customer.id]))
        self.assertRedirects(response, reverse("clients"))
        # Verify customer was NOT deleted
        self.assertTrue(Customer.objects.filter(id=customer.id).exists())
        # Verify message
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Cannot delete client because they are linked" in str(m) for m in messages_list)
        )

    def test_protected_product_deletion_handling(self):
        self.client.force_login(self.user_with_company)
        customer = Customer.objects.create(
            company=self.company,
            name="Jane Doe",
            email="jane@example.com",
            phone="2222222222",
            address="Addr",
        )
        product = Product.objects.create(
            company=self.company,
            name="Service A",
            price=Decimal("100.00"),
            tax=Decimal("18.00"),
        )
        invoice = Invoice.objects.create(
            company=self.company,
            customer=customer,
            invoice_number="INV-102",
            issue_date=date.today(),
            due_date=date.today(),
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            line_total=Decimal("100.00"),
        )

        response = self.client.post(reverse("delete_product", args=[product.id]))
        self.assertRedirects(response, reverse("products"))
        # Verify product was NOT deleted
        self.assertTrue(Product.objects.filter(id=product.id).exists())
        # Verify message
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Cannot delete product because it is linked" in str(m) for m in messages_list)
        )


class AuthenticationAndOnboardingTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            password="SecurePassword123!",
            first_name="Existing User",
        )

    def test_signup_success_auto_login_and_dashboard_redirect(self):
        signup_data = {
            "full_name": "New Developer",
            "email": "newdev@example.com",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "terms": "on",
        }
        response = self.client.post(reverse("signup"), signup_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

        # Verify user created in database
        new_user = User.objects.filter(email="newdev@example.com").first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.first_name, "New Developer")
        self.assertEqual(new_user.username, "newdev@example.com")

        # Verify user is automatically logged in via session
        self.assertEqual(int(self.client.session["_auth_user_id"]), new_user.id)

        # Follow to dashboard and verify onboarding prompt for user with no company
        dash_response = self.client.get(reverse("dashboard"))
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(
            dash_response,
            "Welcome to InvoiceFlow! To get started, please create your company profile.",
        )
        self.assertContains(dash_response, reverse("create_company"))

    def test_signup_mismatched_passwords(self):
        signup_data = {
            "full_name": "Mismatch Tester",
            "email": "mismatch@example.com",
            "password": "Password1!",
            "confirm_password": "Password2!",
            "terms": "on",
        }
        response = self.client.post(reverse("signup"), signup_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match.")
        self.assertFalse(User.objects.filter(email="mismatch@example.com").exists())

    def test_signup_missing_fields(self):
        response = self.client.post(
            reverse("signup"),
            {"full_name": "No Password", "email": "nopass@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please fill in all required fields.")
        self.assertFalse(User.objects.filter(email="nopass@example.com").exists())

    def test_signup_duplicate_email_case_insensitive(self):
        signup_data = {
            "full_name": "Duplicate Tester",
            "email": "EXISTING@EXAMPLE.COM",
            "password": "AnotherPassword123!",
            "confirm_password": "AnotherPassword123!",
            "terms": "on",
        }
        response = self.client.post(reverse("signup"), signup_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")

    def test_login_success_and_redirect(self):
        response = self.client.post(
            reverse("login"),
            {"email": "existing@example.com", "password": "SecurePassword123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_login_case_insensitive_and_trimmed_email(self):
        response = self.client.post(
            reverse("login"),
            {"email": "  EXISTING@EXAMPLE.COM  ", "password": "SecurePassword123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_login_invalid_password(self):
        response = self.client.post(
            reverse("login"),
            {"email": "existing@example.com", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_unknown_email(self):
        response = self.client.post(
            reverse("login"),
            {"email": "nobody@example.com", "password": "SomePassword123!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            reverse("login"),
            {"email": "existing@example.com", "password": "SecurePassword123!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_redirected_from_auth_pages(self):
        self.client.force_login(self.user)
        login_res = self.client.get(reverse("login"))
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse("dashboard"))

        signup_res = self.client.get(reverse("signup"))
        self.assertEqual(signup_res.status_code, 302)
        self.assertRedirects(signup_res, reverse("dashboard"))

    def test_logout_clears_session(self):
        self.client.force_login(self.user)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

        # Dashboard requires login
        dash_res = self.client.get(reverse("dashboard"))
        self.assertEqual(dash_res.status_code, 302)
        self.assertIn(reverse("login"), dash_res.url)

    def test_complete_onboarding_creates_owner_membership(self):
        # Sign up new user
        signup_data = {
            "full_name": "Founder Bob",
            "email": "bob@startup.io",
            "password": "Password1234!",
            "confirm_password": "Password1234!",
            "terms": "on",
        }
        self.client.post(reverse("signup"), signup_data)
        bob = User.objects.get(email="bob@startup.io")

        # Bob creates a company
        create_res = self.client.post(
            reverse("create_company"),
            {
                "name": "Bob Enterprises",
                "email": "contact@bob.io",
                "phone": "9876543210",
                "address": "456 Innovation Way",
                "gst_number": "GSTIN987654321",
            },
        )
        self.assertEqual(create_res.status_code, 302)
        self.assertRedirects(create_res, reverse("dashboard"))

        company = Company.objects.get(name="Bob Enterprises")
        membership = Membership.objects.get(user=bob, company=company)
        self.assertEqual(membership.role, "OWNER")
        self.assertEqual(self.client.session["current_company_id"], company.id)

        # Dashboard now displays company name and no longer shows onboarding banner
        dash_res = self.client.get(reverse("dashboard"))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "Bob Enterprises")
        self.assertNotContains(
            dash_res,
            "Welcome to InvoiceFlow! To get started, please create your company profile.",
        )

