from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from .models import Company, Customer, Invoice, InvoiceItem, Membership, Payment, Product


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


class ApiHealthCheckTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_api_health_check_endpoint(self):
        response = self.client.get(reverse("api_health_check"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("message"), "InvoiceFlow API is running")
        self.assertEqual(data.get("version"), "1.0")



class ApiAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testauth@example.com",
            email="testauth@example.com",
            password="SecurePassword123!",
            first_name="Test User",
        )
        self.company = Company.objects.create(
            name="Test Company",
            email="test@company.com",
            phone="9876543210",
            address="123 Test St",
        )
        self.membership = Membership.objects.create(
            user=self.user,
            company=self.company,
            role="OWNER",
        )

    def test_csrf_token_endpoint(self):
        response = self.client.get(reverse("api_csrf_token"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("csrftoken", data)
        self.assertTrue(len(data["csrftoken"]) > 0)

    def test_signup_success(self):
        response = self.client.post(
            reverse("api_signup"),
            {
                "full_name": "New User",
                "email": "newuser@example.com",
                "password": "NewUserPassword123!",
                "confirm_password": "NewUserPassword123!",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data.get("message"), "Signup successful")
        self.assertEqual(data["user"]["email"], "newuser@example.com")
        self.assertEqual(data["user"]["first_name"], "New User")
        self.assertNotIn("password", data["user"])
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_signup_duplicate_email(self):
        response = self.client.post(
            reverse("api_signup"),
            {
                "full_name": "Duplicate User",
                "email": "testauth@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("error"), "An account with this email already exists.")

    def test_signup_password_mismatch(self):
        response = self.client.post(
            reverse("api_signup"),
            {
                "full_name": "Mismatch User",
                "email": "mismatch@example.com",
                "password": "Password123!",
                "confirm_password": "DifferentPassword123!",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("error"), "Passwords do not match.")

    def test_login_success(self):
        response = self.client.post(
            reverse("api_login"),
            {
                "email": "testauth@example.com",
                "password": "SecurePassword123!",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("message"), "Login successful")
        self.assertEqual(data["user"]["email"], "testauth@example.com")
        self.assertNotIn("password", data["user"])
        self.assertIsNotNone(data["current_company"])
        self.assertEqual(data["current_company"]["name"], "Test Company")

    def test_login_invalid_password(self):
        response = self.client.post(
            reverse("api_login"),
            {
                "email": "testauth@example.com",
                "password": "WrongPassword!",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("error"), "Invalid email or password.")

    def test_login_nonexistent_user(self):
        response = self.client.post(
            reverse("api_login"),
            {
                "email": "unknown@example.com",
                "password": "SomePassword123!",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("error"), "Invalid email or password.")

    def test_current_user_unauthenticated(self):
        response = self.client.get(reverse("api_current_user"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data.get("isAuthenticated"))
        self.assertIsNone(data.get("user"))

    def test_current_user_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("api_current_user"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("isAuthenticated"))
        self.assertEqual(data["user"]["email"], "testauth@example.com")
        self.assertEqual(data["current_company"]["name"], "Test Company")

    def test_logout(self):
        self.client.force_login(self.user)
        logout_response = self.client.post(
            reverse("api_logout"),
            content_type="application/json",
        )
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(logout_response.json().get("message"), "Logged out successfully")

        user_response = self.client.get(reverse("api_current_user"))
        self.assertFalse(user_response.json().get("isAuthenticated"))

    def test_csrf_trusted_origin_allowed(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_res = csrf_client.get(reverse("api_csrf_token"))
        csrftoken = csrf_res.json()["csrftoken"]

        response = csrf_client.post(
            reverse("login"),
            {
                "email": "testauth@example.com",
                "password": "SecurePassword123!",
                "csrfmiddlewaretoken": csrftoken,
            },
            HTTP_ORIGIN="http://localhost:5173",
        )
        self.assertNotEqual(response.status_code, 403)

    def test_csrf_untrusted_origin_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_res = csrf_client.get(reverse("api_csrf_token"))
        csrftoken = csrf_res.json()["csrftoken"]

        response = csrf_client.post(
            reverse("login"),
            {
                "email": "testauth@example.com",
                "password": "SecurePassword123!",
                "csrfmiddlewaretoken": csrftoken,
            },
            HTTP_ORIGIN="http://malicious-site.com",
        )
        self.assertEqual(response.status_code, 403)


class ApiCompanyTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="SecurePassword123!",
            first_name="User One",
        )
        self.user2 = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="SecurePassword123!",
            first_name="User Two",
        )
        self.company1 = Company.objects.create(
            name="User1 Company A",
            email="compa@user1.com",
            phone="1111111111",
            address="111 Street A",
        )
        self.membership1 = Membership.objects.create(
            user=self.user1,
            company=self.company1,
            role="OWNER",
        )
        self.company2 = Company.objects.create(
            name="User1 Company B",
            email="compb@user1.com",
            phone="2222222222",
            address="222 Street B",
        )
        self.membership2 = Membership.objects.create(
            user=self.user1,
            company=self.company2,
            role="STAFF",
        )
        self.other_company = Company.objects.create(
            name="User2 Secret Company",
            email="secret@user2.com",
            phone="9999999999",
            address="999 Secret St",
        )
        self.other_membership = Membership.objects.create(
            user=self.user2,
            company=self.other_company,
            role="OWNER",
        )

    def test_create_company_success(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("api_create_company"),
            {
                "name": "New Venture Inc",
                "email": "contact@newventure.com",
                "phone": "5555555555",
                "address": "555 Tech Park",
                "gst_number": "GSTIN5555555",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data.get("message"), "Company created successfully")
        self.assertEqual(data["company"]["name"], "New Venture Inc")
        self.assertEqual(data["company"]["role"], "OWNER")
        self.assertEqual(data["current_company"]["name"], "New Venture Inc")
        created_company = Company.objects.get(name="New Venture Inc")
        self.assertEqual(self.client.session["current_company_id"], created_company.id)
        self.assertTrue(Membership.objects.filter(user=self.user1, company=created_company, role="OWNER").exists())

    def test_create_company_unauthenticated(self):
        response = self.client.post(
            reverse("api_create_company"),
            {
                "name": "Unauthorized Inc",
                "email": "test@unauth.com",
                "phone": "0000000000",
                "address": "Nowhere",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_create_company_missing_fields(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("api_create_company"),
            {
                "name": "",
                "email": "invalid@email.com",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("error"), "Please fill in all required fields.")

    def test_switch_company_success(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("api_switch_company", kwargs={"company_id": self.company2.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("message"), "Switched company successfully")
        self.assertEqual(data["current_company"]["id"], self.company2.id)
        self.assertEqual(data["current_company"]["role"], "STAFF")
        self.assertEqual(self.client.session["current_company_id"], self.company2.id)

    def test_switch_company_unauthorized_does_not_change_session(self):
        self.client.force_login(self.user1)
        session = self.client.session
        session["current_company_id"] = self.company1.id
        session.save()

        response = self.client.post(
            reverse("api_switch_company", kwargs={"company_id": self.other_company.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json().get("error"), "You do not have access to this company.")
        self.assertEqual(self.client.session["current_company_id"], self.company1.id)

    def test_switch_company_nonexistent(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("api_switch_company", kwargs={"company_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class ApiCustomerTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="custuser@example.com",
            email="custuser@example.com",
            password="SecurePassword123!",
            first_name="Cust User",
        )
        self.company = Company.objects.create(
            name="Alpha Corp",
            email="alpha@corp.com",
            phone="1111111111",
            address="111 Alpha Way",
        )
        self.membership = Membership.objects.create(
            user=self.user,
            company=self.company,
            role="OWNER",
        )
        # Another company and user
        self.other_user = User.objects.create_user(
            username="othercust@example.com",
            email="othercust@example.com",
            password="SecurePassword123!",
        )
        self.other_company = Company.objects.create(
            name="Beta Corp",
            email="beta@corp.com",
            phone="2222222222",
            address="222 Beta Way",
        )
        self.other_membership = Membership.objects.create(
            user=self.other_user,
            company=self.other_company,
            role="OWNER",
        )
        self.other_customer = Customer.objects.create(
            company=self.other_company,
            name="Beta Exclusive Client",
            email="beta@client.com",
            phone="9999999999",
            address="Beta Address",
        )

    def test_list_customers_empty(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("api_customers_list_create"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_customer_success(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("api_customers_list_create"),
            {
                "name": "Acme Client",
                "email": "client@acme.com",
                "phone": "9876543210",
                "address": "123 Business St",
                "gst_number": "GSTIN12345678",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data.get("message"), "Customer created successfully")
        self.assertEqual(data["customer"]["name"], "Acme Client")
        self.assertEqual(data["customer"]["company"], self.company.id)
        self.assertTrue(Customer.objects.filter(company=self.company, name="Acme Client").exists())

    def test_create_customer_missing_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("api_customers_list_create"),
            {
                "name": "Incomplete Client",
                "email": "",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("error"), "Please fill in all required fields.")

    def test_search_customers(self):
        self.client.force_login(self.user)
        Customer.objects.create(
            company=self.company,
            name="Alice Walker",
            email="alice@walker.com",
            phone="1234567890",
            address="Address A",
        )
        Customer.objects.create(
            company=self.company,
            name="Bob Smith",
            email="bob@smith.com",
            phone="0987654321",
            address="Address B",
        )

        res = self.client.get(reverse("api_customers_list_create") + "?search=Alice")
        self.assertEqual(res.status_code, 200)
        results = res.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alice Walker")

        res_email = self.client.get(reverse("api_customers_list_create") + "?search=smith.com")
        self.assertEqual(len(res_email.json()), 1)
        self.assertEqual(res_email.json()[0]["name"], "Bob Smith")

    def test_update_customer_success(self):
        self.client.force_login(self.user)
        cust = Customer.objects.create(
            company=self.company,
            name="Original Name",
            email="orig@email.com",
            phone="1111111111",
            address="Original Address",
        )

        response = self.client.put(
            reverse("api_customer_detail", kwargs={"customer_id": cust.id}),
            {
                "name": "Updated Name",
                "email": "updated@email.com",
                "phone": "2222222222",
                "address": "Updated Address",
                "gst_number": "GSTIN999",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        cust.refresh_from_db()
        self.assertEqual(cust.name, "Updated Name")
        self.assertEqual(cust.phone, "2222222222")
        self.assertEqual(cust.gst_number, "GSTIN999")

    def test_delete_customer_success(self):
        self.client.force_login(self.user)
        cust = Customer.objects.create(
            company=self.company,
            name="To Be Deleted",
            email="delete@email.com",
            phone="1111111111",
            address="Delete Address",
        )

        response = self.client.delete(reverse("api_customer_detail", kwargs={"customer_id": cust.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("message"), "Customer deleted successfully")
        self.assertFalse(Customer.objects.filter(id=cust.id).exists())

    def test_delete_customer_protected_error(self):
        self.client.force_login(self.user)
        cust = Customer.objects.create(
            company=self.company,
            name="Protected Client",
            email="protect@email.com",
            phone="1111111111",
            address="Address",
        )
        Invoice.objects.create(
            company=self.company,
            customer=cust,
            invoice_number="INV-TEST-001",
            issue_date=date.today(),
            due_date=date.today(),
            status="DRAFT",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("110.00"),
        )

        response = self.client.delete(reverse("api_customer_detail", kwargs={"customer_id": cust.id}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json().get("error"),
            "Cannot delete client because they are linked to existing invoices.",
        )
        self.assertTrue(Customer.objects.filter(id=cust.id).exists())

    def test_cross_company_isolation(self):
        self.client.force_login(self.user)
        res_get = self.client.get(
            reverse("api_customer_detail", kwargs={"customer_id": self.other_customer.id})
        )
        self.assertEqual(res_get.status_code, 404)

        res_put = self.client.put(
            reverse("api_customer_detail", kwargs={"customer_id": self.other_customer.id}),
            {
                "name": "Hacked Name",
                "email": "hacked@email.com",
                "phone": "0000000000",
                "address": "Nowhere",
            },
            content_type="application/json",
        )
        self.assertEqual(res_put.status_code, 404)

        res_del = self.client.delete(
            reverse("api_customer_detail", kwargs={"customer_id": self.other_customer.id})
        )
        self.assertEqual(res_del.status_code, 404)

        self.other_customer.refresh_from_db()
        self.assertEqual(self.other_customer.name, "Beta Exclusive Client")

    def test_unauthenticated_access(self):
        response = self.client.get(reverse("api_customers_list_create"))
        self.assertEqual(response.status_code, 403)


class ProductAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="produser@example.com",
            email="produser@example.com",
            password="SecurePassword123!",
            first_name="Prod Manager",
        )
        self.company = Company.objects.create(
            name="Alpha Corp",
            email="alpha@corp.com",
            phone="1111111111",
            address="111 Alpha Way",
        )
        self.membership = Membership.objects.create(
            user=self.user,
            company=self.company,
            role="OWNER",
        )

        # Another company and user for isolation tests
        self.other_user = User.objects.create_user(
            username="otherprod@example.com",
            email="otherprod@example.com",
            password="SecurePassword123!",
        )
        self.other_company = Company.objects.create(
            name="Beta Corp",
            email="beta@corp.com",
            phone="2222222222",
            address="222 Beta Way",
        )
        self.other_membership = Membership.objects.create(
            user=self.other_user,
            company=self.other_company,
            role="OWNER",
        )
        self.other_product = Product.objects.create(
            company=self.other_company,
            name="Beta Exclusive Widget",
            description="Beta only item",
            price=Decimal("499.00"),
            tax=Decimal("18.00"),
        )

    def test_list_products_empty(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("api_products_list_create"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_product_success(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("api_products_list_create"),
            {
                "name": "Consulting Service",
                "description": "Hourly strategic consulting",
                "price": "1500.00",
                "tax": "18.00",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data.get("message"), "Product created successfully")
        self.assertEqual(data["product"]["name"], "Consulting Service")
        self.assertEqual(data["product"]["company"], self.company.id)
        self.assertEqual(Decimal(str(data["product"]["price"])), Decimal("1500.00"))
        self.assertEqual(Decimal(str(data["product"]["tax"])), Decimal("18.00"))
        self.assertTrue(Product.objects.filter(company=self.company, name="Consulting Service").exists())

    def test_create_product_missing_name_or_price(self):
        self.client.force_login(self.user)
        # Missing price
        res1 = self.client.post(
            reverse("api_products_list_create"),
            {"name": "No Price Item"},
            content_type="application/json",
        )
        self.assertEqual(res1.status_code, 400)
        self.assertEqual(res1.json().get("error"), "Product name and price are required.")

        # Missing name
        res2 = self.client.post(
            reverse("api_products_list_create"),
            {"price": "100.00"},
            content_type="application/json",
        )
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.json().get("error"), "Product name and price are required.")

    def test_create_product_invalid_price_or_tax(self):
        self.client.force_login(self.user)
        # Negative price
        res_neg_price = self.client.post(
            reverse("api_products_list_create"),
            {"name": "Neg Item", "price": "-50.00"},
            content_type="application/json",
        )
        self.assertEqual(res_neg_price.status_code, 400)
        self.assertEqual(res_neg_price.json().get("error"), "Please enter valid numbers for price and tax.")

        # Negative tax
        res_neg_tax = self.client.post(
            reverse("api_products_list_create"),
            {"name": "Neg Tax Item", "price": "50.00", "tax": "-5"},
            content_type="application/json",
        )
        self.assertEqual(res_neg_tax.status_code, 400)
        self.assertEqual(res_neg_tax.json().get("error"), "Please enter valid numbers for price and tax.")

        # Non-numeric string
        res_alpha = self.client.post(
            reverse("api_products_list_create"),
            {"name": "Alpha Item", "price": "abc"},
            content_type="application/json",
        )
        self.assertEqual(res_alpha.status_code, 400)
        self.assertEqual(res_alpha.json().get("error"), "Please enter valid numbers for price and tax.")

    def test_search_products(self):
        self.client.force_login(self.user)
        Product.objects.create(
            company=self.company,
            name="Web Hosting Plan",
            description="Annual cloud server hosting",
            price=Decimal("12000.00"),
            tax=Decimal("18.00"),
        )
        Product.objects.create(
            company=self.company,
            name="Domain Registration",
            description="Annual .com domain address",
            price=Decimal("1000.00"),
            tax=Decimal("18.00"),
        )

        # Search by name
        res_name = self.client.get(reverse("api_products_list_create") + "?search=Hosting")
        self.assertEqual(res_name.status_code, 200)
        self.assertEqual(len(res_name.json()), 1)
        self.assertEqual(res_name.json()[0]["name"], "Web Hosting Plan")

        # Search by description
        res_desc = self.client.get(reverse("api_products_list_create") + "?search=cloud")
        self.assertEqual(res_desc.status_code, 200)
        self.assertEqual(len(res_desc.json()), 1)
        self.assertEqual(res_desc.json()[0]["name"], "Web Hosting Plan")

    def test_get_product_detail(self):
        self.client.force_login(self.user)
        prod = Product.objects.create(
            company=self.company,
            name="Single Item",
            description="Detail test",
            price=Decimal("250.00"),
            tax=Decimal("5.00"),
        )
        res = self.client.get(reverse("api_product_detail", kwargs={"product_id": prod.id}))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["product"]["name"], "Single Item")

    def test_update_product_success(self):
        self.client.force_login(self.user)
        prod = Product.objects.create(
            company=self.company,
            name="Old Product",
            description="Old description",
            price=Decimal("100.00"),
            tax=Decimal("5.00"),
        )

        response = self.client.put(
            reverse("api_product_detail", kwargs={"product_id": prod.id}),
            {
                "name": "New Product Name",
                "description": "Updated description",
                "price": "299.99",
                "tax": "12.00",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        prod.refresh_from_db()
        self.assertEqual(prod.name, "New Product Name")
        self.assertEqual(prod.description, "Updated description")
        self.assertEqual(prod.price, Decimal("299.99"))
        self.assertEqual(prod.tax, Decimal("12.00"))

    def test_delete_product_success(self):
        self.client.force_login(self.user)
        prod = Product.objects.create(
            company=self.company,
            name="Product To Delete",
            price=Decimal("50.00"),
        )

        response = self.client.delete(reverse("api_product_detail", kwargs={"product_id": prod.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("message"), "Product deleted successfully")
        self.assertFalse(Product.objects.filter(id=prod.id).exists())

    def test_delete_product_protected_error(self):
        self.client.force_login(self.user)
        prod = Product.objects.create(
            company=self.company,
            name="Protected Product",
            price=Decimal("100.00"),
        )
        cust = Customer.objects.create(
            company=self.company,
            name="Client A",
            email="clienta@test.com",
            phone="1234567890",
            address="Street 1",
        )
        inv = Invoice.objects.create(
            company=self.company,
            customer=cust,
            invoice_number="INV-PROD-001",
            issue_date=date.today(),
            due_date=date.today(),
            status="DRAFT",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("110.00"),
        )
        InvoiceItem.objects.create(
            invoice=inv,
            product=prod,
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            tax=Decimal("10.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("110.00"),
        )

        response = self.client.delete(reverse("api_product_detail", kwargs={"product_id": prod.id}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json().get("error"),
            "Cannot delete product because it is linked to existing invoice items.",
        )
        self.assertTrue(Product.objects.filter(id=prod.id).exists())

    def test_cross_company_isolation(self):
        self.client.force_login(self.user)
        # Attempt to GET other company's product
        res_get = self.client.get(
            reverse("api_product_detail", kwargs={"product_id": self.other_product.id})
        )
        self.assertEqual(res_get.status_code, 404)

        # Attempt to PUT other company's product
        res_put = self.client.put(
            reverse("api_product_detail", kwargs={"product_id": self.other_product.id}),
            {
                "name": "Hacked Name",
                "price": "1.00",
            },
            content_type="application/json",
        )
        self.assertEqual(res_put.status_code, 404)

        # Attempt to DELETE other company's product
        res_del = self.client.delete(
            reverse("api_product_detail", kwargs={"product_id": self.other_product.id})
        )
        self.assertEqual(res_del.status_code, 404)

        self.other_product.refresh_from_db()
        self.assertEqual(self.other_product.name, "Beta Exclusive Widget")

    def test_unauthenticated_access(self):
        response = self.client.get(reverse("api_products_list_create"))
        self.assertEqual(response.status_code, 403)


class InvoiceAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="invuser@example.com",
            email="invuser@example.com",
            password="SecurePassword123!",
            first_name="Invoice Manager",
        )
        self.company = Company.objects.create(
            name="Alpha Corp",
            email="alpha@corp.com",
            phone="1111111111",
            address="111 Alpha Way",
        )
        self.membership = Membership.objects.create(
            user=self.user,
            company=self.company,
            role="OWNER",
        )
        self.customer = Customer.objects.create(
            company=self.company,
            name="Acme Client",
            email="acme@client.com",
            phone="9876543210",
            address="123 Acme St",
            gst_number="GSTIN12345",
        )
        self.product1 = Product.objects.create(
            company=self.company,
            name="Web Consulting",
            description="Hourly consulting",
            price=Decimal("1000.00"),
            tax=Decimal("18.00"),
        )
        self.product2 = Product.objects.create(
            company=self.company,
            name="Server Maintenance",
            description="Monthly server care",
            price=Decimal("500.00"),
            tax=Decimal("5.00"),
        )

        # Another company and user for isolation tests
        self.other_user = User.objects.create_user(
            username="otherinv@example.com",
            email="otherinv@example.com",
            password="SecurePassword123!",
        )
        self.other_company = Company.objects.create(
            name="Beta Corp",
            email="beta@corp.com",
            phone="2222222222",
            address="222 Beta Way",
        )
        self.other_membership = Membership.objects.create(
            user=self.other_user,
            company=self.other_company,
            role="OWNER",
        )
        self.other_customer = Customer.objects.create(
            company=self.other_company,
            name="Beta Exclusive Customer",
            email="beta@customer.com",
            phone="9999999999",
            address="Beta Address",
        )
        self.other_product = Product.objects.create(
            company=self.other_company,
            name="Beta Exclusive Item",
            price=Decimal("2000.00"),
            tax=Decimal("18.00"),
        )
        self.other_invoice = Invoice.objects.create(
            company=self.other_company,
            customer=self.other_customer,
            invoice_number="INV-BETA-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status="SENT",
            subtotal=Decimal("2000.00"),
            tax_amount=Decimal("360.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("2360.00"),
        )
        InvoiceItem.objects.create(
            invoice=self.other_invoice,
            product=self.other_product,
            quantity=Decimal("1.00"),
            unit_price=Decimal("2000.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("2360.00"),
        )

    def test_list_invoices_empty(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("api_invoices_list_create"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_invoice_success_and_calculations(self):
        self.client.force_login(self.user)
        today = date.today()
        due = today + timedelta(days=15)

        payload = {
            "invoice_number": "INV-2026-001",
            "customer": self.customer.id,
            "issue_date": str(today),
            "due_date": str(due),
            "discount": "100.00",
            "notes": "Thank you for your business.",
            "items": [
                {
                    "product": self.product1.id,
                    "quantity": "2.00",
                    "unit_price": "1000.00",
                    "tax": "18.00",
                },
                {
                    "product": self.product2.id,
                    "quantity": "1.00",
                    "unit_price": "500.00",
                    "tax": "5.00",
                },
            ],
        }

        response = self.client.post(
            reverse("api_invoices_list_create"),
            payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data.get("message"), "Invoice created successfully")

        # Verify DB records and backend decimal calculations
        inv = Invoice.objects.get(company=self.company, invoice_number="INV-2026-001")
        self.assertEqual(inv.status, "SENT")
        self.assertEqual(inv.subtotal, Decimal("2500.00"))      # 2*1000 + 1*500
        self.assertEqual(inv.tax_amount, Decimal("385.00"))    # (2000*18)/100 = 360, (500*5)/100 = 25 -> 385
        self.assertEqual(inv.discount_amount, Decimal("100.00"))
        self.assertEqual(inv.total, Decimal("2785.00"))         # 2500 + 385 - 100 = 2785.00
        self.assertEqual(inv.items.count(), 2)

        # Check line totals
        item1 = inv.items.get(product=self.product1)
        self.assertEqual(item1.quantity, Decimal("2.00"))
        self.assertEqual(item1.line_total, Decimal("2360.00"))  # 2000 + 360

        item2 = inv.items.get(product=self.product2)
        self.assertEqual(item2.quantity, Decimal("1.00"))
        self.assertEqual(item2.line_total, Decimal("525.00"))   # 500 + 25

    def test_create_invoice_duplicate_number(self):
        self.client.force_login(self.user)
        today = date.today()
        payload = {
            "invoice_number": "INV-DUP-001",
            "customer": self.customer.id,
            "issue_date": str(today),
            "due_date": str(today + timedelta(days=7)),
            "items": [{"product": self.product1.id, "quantity": "1"}],
        }
        res1 = self.client.post(reverse("api_invoices_list_create"), payload, content_type="application/json")
        self.assertEqual(res1.status_code, 201)

        # Second creation with same number
        res2 = self.client.post(reverse("api_invoices_list_create"), payload, content_type="application/json")
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.json().get("error"), "Invoice number already exists for this company.")

    def test_create_invoice_invalid_dates(self):
        self.client.force_login(self.user)
        today = date.today()
        # Due date before issue date
        payload = {
            "invoice_number": "INV-DATE-ERR",
            "customer": self.customer.id,
            "issue_date": str(today),
            "due_date": str(today - timedelta(days=1)),
            "items": [{"product": self.product1.id, "quantity": "1"}],
        }
        res = self.client.post(reverse("api_invoices_list_create"), payload, content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json().get("error"), "Due date cannot be before the issue date.")

    def test_create_invoice_cross_company_customer_or_product(self):
        self.client.force_login(self.user)
        today = date.today()
        # Invalid customer (belongs to other company)
        res_cust = self.client.post(
            reverse("api_invoices_list_create"),
            {
                "invoice_number": "INV-CROSS-CUST",
                "customer": self.other_customer.id,
                "issue_date": str(today),
                "due_date": str(today + timedelta(days=7)),
                "items": [{"product": self.product1.id, "quantity": "1"}],
            },
            content_type="application/json",
        )
        self.assertEqual(res_cust.status_code, 400)
        self.assertEqual(res_cust.json().get("error"), "Invalid customer selected.")

        # Invalid product (belongs to other company)
        res_prod = self.client.post(
            reverse("api_invoices_list_create"),
            {
                "invoice_number": "INV-CROSS-PROD",
                "customer": self.customer.id,
                "issue_date": str(today),
                "due_date": str(today + timedelta(days=7)),
                "items": [{"product": self.other_product.id, "quantity": "1"}],
            },
            content_type="application/json",
        )
        self.assertEqual(res_prod.status_code, 400)
        self.assertEqual(res_prod.json().get("error"), "Invalid product selected.")

    def test_create_invoice_invalid_quantities_and_discount(self):
        self.client.force_login(self.user)
        today = date.today()
        # Zero quantity
        res_zero = self.client.post(
            reverse("api_invoices_list_create"),
            {
                "invoice_number": "INV-ZERO-QTY",
                "customer": self.customer.id,
                "issue_date": str(today),
                "due_date": str(today + timedelta(days=7)),
                "items": [{"product": self.product1.id, "quantity": "0"}],
            },
            content_type="application/json",
        )
        self.assertEqual(res_zero.status_code, 400)
        self.assertEqual(res_zero.json().get("error"), "Quantity must be greater than zero.")

        # Negative discount
        res_neg_disc = self.client.post(
            reverse("api_invoices_list_create"),
            {
                "invoice_number": "INV-NEG-DISC",
                "customer": self.customer.id,
                "issue_date": str(today),
                "due_date": str(today + timedelta(days=7)),
                "discount": "-50.00",
                "items": [{"product": self.product1.id, "quantity": "1"}],
            },
            content_type="application/json",
        )
        self.assertEqual(res_neg_disc.status_code, 400)
        self.assertEqual(res_neg_disc.json().get("error"), "Invalid discount amount.")

    def test_get_invoice_detail_with_payments(self):
        self.client.force_login(self.user)
        today = date.today()
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-DETAIL-001",
            issue_date=today,
            due_date=today + timedelta(days=30),
            status="SENT",
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("180.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("1180.00"),
        )
        InvoiceItem.objects.create(
            invoice=inv,
            product=self.product1,
            quantity=Decimal("1.00"),
            unit_price=Decimal("1000.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1180.00"),
        )
        Payment.objects.create(
            invoice=inv,
            amount=Decimal("500.00"),
            payment_method="BANK",
            payment_date=today,
        )

        res = self.client.get(reverse("api_invoice_detail", kwargs={"invoice_id": inv.id}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["invoice"]["invoice_number"], "INV-DETAIL-001")
        self.assertEqual(data["customer"]["name"], "Acme Client")
        self.assertEqual(len(data["payments"]), 1)
        self.assertEqual(Decimal(str(data["paid_amount"])), Decimal("500.00"))
        self.assertEqual(Decimal(str(data["remaining_amount"])), Decimal("680.00"))

    def test_overdue_status_transition(self):
        self.client.force_login(self.user)
        yesterday = date.today() - timedelta(days=1)
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-OVERDUE-001",
            issue_date=yesterday - timedelta(days=15),
            due_date=yesterday,
            status="SENT",
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )

        # Listing triggers overdue update
        res = self.client.get(reverse("api_invoices_list_create"))
        self.assertEqual(res.status_code, 200)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "OVERDUE")

    def test_update_invoice_success(self):
        self.client.force_login(self.user)
        today = date.today()
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-EDIT-001",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            subtotal=Decimal("500.00"),
            total=Decimal("500.00"),
        )
        InvoiceItem.objects.create(
            invoice=inv,
            product=self.product2,
            quantity=Decimal("1.00"),
            unit_price=Decimal("500.00"),
            tax=Decimal("0.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("500.00"),
        )

        # Update invoice to have product1 instead
        response = self.client.put(
            reverse("api_invoice_detail", kwargs={"invoice_id": inv.id}),
            {
                "invoice_number": "INV-EDIT-UPDATED",
                "customer": self.customer.id,
                "issue_date": str(today),
                "due_date": str(today + timedelta(days=20)),
                "discount": "50.00",
                "notes": "Updated note",
                "items": [
                    {
                        "product": self.product1.id,
                        "quantity": "3.00",
                        "unit_price": "1000.00",
                        "tax": "18.00",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        inv.refresh_from_db()
        self.assertEqual(inv.invoice_number, "INV-EDIT-UPDATED")
        self.assertEqual(inv.subtotal, Decimal("3000.00"))      # 3 * 1000
        self.assertEqual(inv.tax_amount, Decimal("540.00"))    # (3000 * 18)/100
        self.assertEqual(inv.discount_amount, Decimal("50.00"))
        self.assertEqual(inv.total, Decimal("3490.00"))         # 3000 + 540 - 50 = 3490.00
        self.assertEqual(inv.items.count(), 1)
        self.assertEqual(inv.items.first().product, self.product1)

    def test_update_invoice_blocked_for_paid_cancelled_and_payment_linked(self):
        self.client.force_login(self.user)
        today = date.today()

        # 1. Paid invoice
        paid_inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-PAID-001",
            issue_date=today,
            due_date=today + timedelta(days=7),
            status="PAID",
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        res_paid = self.client.put(
            reverse("api_invoice_detail", kwargs={"invoice_id": paid_inv.id}),
            {"invoice_number": "INV-PAID-001", "customer": self.customer.id, "items": [{"product": self.product1.id, "quantity": "1"}]},
            content_type="application/json",
        )
        self.assertEqual(res_paid.status_code, 400)
        self.assertIn("already paid", res_paid.json().get("error", "").lower())

        # 2. Cancelled invoice
        canc_inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-CANC-001",
            issue_date=today,
            due_date=today + timedelta(days=7),
            status="CANCELLED",
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        res_canc = self.client.put(
            reverse("api_invoice_detail", kwargs={"invoice_id": canc_inv.id}),
            {"invoice_number": "INV-CANC-001", "customer": self.customer.id, "items": [{"product": self.product1.id, "quantity": "1"}]},
            content_type="application/json",
        )
        self.assertEqual(res_canc.status_code, 400)
        self.assertIn("already cancelled", res_canc.json().get("error", "").lower())

        # 3. Payment-linked invoice
        sent_inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-PARTIAL-001",
            issue_date=today,
            due_date=today + timedelta(days=7),
            status="SENT",
            subtotal=Decimal("200.00"),
            total=Decimal("200.00"),
        )
        Payment.objects.create(
            invoice=sent_inv,
            amount=Decimal("50.00"),
            payment_method="CASH",
            payment_date=today,
        )
        res_partial = self.client.put(
            reverse("api_invoice_detail", kwargs={"invoice_id": sent_inv.id}),
            {"invoice_number": "INV-PARTIAL-001", "customer": self.customer.id, "items": [{"product": self.product1.id, "quantity": "1"}]},
            content_type="application/json",
        )
        self.assertEqual(res_partial.status_code, 400)
        self.assertIn("recorded payments", res_partial.json().get("error", "").lower())

    def test_cancel_invoice_success_and_restrictions(self):
        self.client.force_login(self.user)
        today = date.today()
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-TO-CANCEL",
            issue_date=today,
            due_date=today + timedelta(days=7),
            status="SENT",
            total=Decimal("100.00"),
        )

        # Cancel SENT invoice -> Success
        res = self.client.post(reverse("api_invoice_cancel", kwargs={"invoice_id": inv.id}))
        self.assertEqual(res.status_code, 200)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "CANCELLED")

        # Cancel already cancelled -> 400
        res_already = self.client.post(reverse("api_invoice_cancel", kwargs={"invoice_id": inv.id}))
        self.assertEqual(res_already.status_code, 400)
        self.assertEqual(res_already.json().get("error"), "Invoice is already cancelled.")

        # Cancel PAID invoice -> 400
        paid_inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-PAID-NOCANC",
            issue_date=today,
            due_date=today + timedelta(days=7),
            status="PAID",
            total=Decimal("100.00"),
        )
        res_paid = self.client.post(reverse("api_invoice_cancel", kwargs={"invoice_id": paid_inv.id}))
        self.assertEqual(res_paid.status_code, 400)
        self.assertEqual(res_paid.json().get("error"), "Paid invoices cannot be cancelled.")

    def test_search_and_filter_invoices(self):
        self.client.force_login(self.user)
        today = date.today()
        Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-SEARCH-A1",
            issue_date=today,
            due_date=today + timedelta(days=7),
            status="SENT",
            total=Decimal("100.00"),
        )
        Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-SEARCH-B2",
            issue_date=today,
            due_date=today + timedelta(days=7),
            status="CANCELLED",
            total=Decimal("200.00"),
        )

        # Search by invoice number
        res_num = self.client.get(reverse("api_invoices_list_create") + "?search=A1")
        self.assertEqual(res_num.status_code, 200)
        self.assertEqual(len(res_num.json()), 1)
        self.assertEqual(res_num.json()[0]["invoice_number"], "INV-SEARCH-A1")

        # Filter by status
        res_status = self.client.get(reverse("api_invoices_list_create") + "?status=CANCELLED")
        self.assertEqual(res_status.status_code, 200)
        self.assertEqual(len(res_status.json()), 1)
        self.assertEqual(res_status.json()[0]["invoice_number"], "INV-SEARCH-B2")

    def test_cross_company_isolation(self):
        self.client.force_login(self.user)
        # GET other company invoice -> 404
        res_get = self.client.get(reverse("api_invoice_detail", kwargs={"invoice_id": self.other_invoice.id}))
        self.assertEqual(res_get.status_code, 404)

        # PUT other company invoice -> 404
        res_put = self.client.put(
            reverse("api_invoice_detail", kwargs={"invoice_id": self.other_invoice.id}),
            {"invoice_number": "INV-HACK", "customer": self.customer.id, "items": [{"product": self.product1.id, "quantity": "1"}]},
            content_type="application/json",
        )
        self.assertEqual(res_put.status_code, 404)

        # CANCEL other company invoice -> 404
        res_cancel = self.client.post(reverse("api_invoice_cancel", kwargs={"invoice_id": self.other_invoice.id}))
        self.assertEqual(res_cancel.status_code, 404)

        self.other_invoice.refresh_from_db()
        self.assertEqual(self.other_invoice.invoice_number, "INV-BETA-001")
        self.assertEqual(self.other_invoice.status, "SENT")

    def test_pdf_download_routes(self):
        self.client.force_login(self.user)
        today = date.today()
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-PDF-001",
            issue_date=today,
            due_date=today + timedelta(days=14),
            status="SENT",
            subtotal=Decimal("1000.00"),
            total=Decimal("1000.00"),
        )
        InvoiceItem.objects.create(
            invoice=inv,
            product=self.product1,
            quantity=Decimal("1.00"),
            unit_price=Decimal("1000.00"),
            tax=Decimal("0.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000.00"),
        )

        # Test original route: /invoices/<id>/pdf/
        res_orig = self.client.get(reverse("generate_invoice_pdf", kwargs={"invoice_id": inv.id}))
        self.assertEqual(res_orig.status_code, 200)
        self.assertEqual(res_orig["Content-Type"], "application/pdf")
        self.assertIn("INV-PDF-001.pdf", res_orig["Content-Disposition"])

        # Test API alias route: /api/invoices/<id>/pdf/
        res_api = self.client.get(reverse("api_invoice_pdf", kwargs={"invoice_id": inv.id}))
        self.assertEqual(res_api.status_code, 200)
        self.assertEqual(res_api["Content-Type"], "application/pdf")
        self.assertIn("INV-PDF-001.pdf", res_api["Content-Disposition"])

    def test_unauthenticated_access(self):
        response = self.client.get(reverse("api_invoices_list_create"))
        self.assertEqual(response.status_code, 403)


class PaymentAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="payuser@example.com",
            email="payuser@example.com",
            password="SecurePassword123!",
            first_name="Payment Manager",
        )
        self.company = Company.objects.create(
            name="Alpha Corp",
            email="alpha@corp.com",
            phone="1111111111",
            address="111 Alpha Way",
        )
        self.membership = Membership.objects.create(
            user=self.user,
            company=self.company,
            role="OWNER",
        )

        self.customer = Customer.objects.create(
            company=self.company,
            name="Alpha Customer",
            email="cust@alpha.com",
            phone="9998887771",
            address="1 Alpha Customer Road",
        )

        today = date.today()
        self.invoice = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-ALPHA-100",
            issue_date=today,
            due_date=today + timedelta(days=15),
            status="SENT",
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("500.00"),
        )

        # Other company for cross-company tests
        self.other_user = User.objects.create_user(
            username="otherpayuser@example.com",
            email="otherpayuser@example.com",
            password="SecurePassword123!",
            first_name="Other Manager",
        )
        self.other_company = Company.objects.create(
            name="Beta Corp",
            email="beta@corp.com",
            phone="2222222222",
            address="222 Beta Ave",
        )
        self.other_membership = Membership.objects.create(
            user=self.other_user,
            company=self.other_company,
            role="OWNER",
        )
        self.other_customer = Customer.objects.create(
            company=self.other_company,
            name="Beta Customer",
            email="cust@beta.com",
            phone="8887776662",
            address="2 Beta Customer Road",
        )
        self.other_invoice = Invoice.objects.create(
            company=self.other_company,
            customer=self.other_customer,
            invoice_number="INV-BETA-200",
            issue_date=today,
            due_date=today + timedelta(days=15),
            status="SENT",
            subtotal=Decimal("300.00"),
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("300.00"),
        )

    def test_get_payments_empty_and_stats(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse("api_payments_list_create"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["payments"], [])
        self.assertEqual(data["stats"]["total_received"], "0.00")
        self.assertEqual(data["stats"]["this_month"], "0.00")
        self.assertEqual(data["stats"]["payment_count"], 0)

    def test_record_payment_valid_partial(self):
        self.client.force_login(self.user)
        today = date.today()
        payload = {
            "invoice": self.invoice.id,
            "amount": "150.00",
            "payment_method": "UPI",
            "payment_date": today.isoformat(),
            "notes": "Partial UPI payment",
        }
        res = self.client.post(
            reverse("api_payments_list_create"),
            payload,
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["message"], "Payment recorded successfully")
        self.assertEqual(data["payment"]["invoice_number"], "INV-ALPHA-100")
        self.assertEqual(data["payment"]["customer_name"], "Alpha Customer")
        self.assertEqual(data["payment"]["payment_method_display"], "UPI")
        self.assertEqual(data["payment"]["amount"], "150.00")
        self.assertEqual(data["paid_amount"], "150.00")
        self.assertEqual(data["remaining_amount"], "350.00")
        self.assertEqual(data["invoice_status"], "SENT")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "SENT")

    def test_record_payment_full_transitions_to_paid(self):
        self.client.force_login(self.user)
        today = date.today()
        payload = {
            "invoice": self.invoice.id,
            "amount": "500.00",
            "payment_method": "BANK",
            "payment_date": today.isoformat(),
            "notes": "Full settlement via bank transfer",
        }
        res = self.client.post(
            reverse("api_payments_list_create"),
            payload,
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["paid_amount"], "500.00")
        self.assertEqual(data["remaining_amount"], "0.00")
        self.assertEqual(data["invoice_status"], "PAID")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")

    def test_record_multiple_partial_payments(self):
        self.client.force_login(self.user)
        today = date.today()

        # 1st payment: 200
        res1 = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": self.invoice.id,
                "amount": "200.00",
                "payment_method": "CASH",
                "payment_date": today.isoformat(),
            },
            content_type="application/json",
        )
        self.assertEqual(res1.status_code, 201)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "SENT")

        # 2nd payment: 300 (completes 500)
        res2 = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": self.invoice.id,
                "amount": "300.00",
                "payment_method": "CARD",
                "payment_date": today.isoformat(),
            },
            content_type="application/json",
        )
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.json()["remaining_amount"], "0.00")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")

    def test_prevent_overpayment(self):
        self.client.force_login(self.user)
        today = date.today()
        # Invoice total is 500.00; attempt to pay 500.01
        res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": self.invoice.id,
                "amount": "500.01",
                "payment_method": "CASH",
                "payment_date": today.isoformat(),
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot exceed the remaining balance", res.json().get("error", ""))

    def test_payment_on_already_paid_invoice(self):
        self.client.force_login(self.user)
        today = date.today()
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("500.00"),
            payment_method="CASH",
            payment_date=today,
        )
        self.invoice.status = "PAID"
        self.invoice.save()

        res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": self.invoice.id,
                "amount": "10.00",
                "payment_method": "CASH",
                "payment_date": today.isoformat(),
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("already been fully paid", res.json().get("error", ""))

    def test_payment_on_cancelled_invoice(self):
        self.client.force_login(self.user)
        today = date.today()
        self.invoice.status = "CANCELLED"
        self.invoice.save()

        res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": self.invoice.id,
                "amount": "100.00",
                "payment_method": "CASH",
                "payment_date": today.isoformat(),
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("cancelled invoice", res.json().get("error", "").lower())

    def test_invalid_amount_validation(self):
        self.client.force_login(self.user)
        today = date.today()

        # Negative amount
        res_neg = self.client.post(
            reverse("api_payments_list_create"),
            {"invoice": self.invoice.id, "amount": "-50.00", "payment_method": "CASH", "payment_date": today.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(res_neg.status_code, 400)
        self.assertIn("greater than zero", res_neg.json().get("error", ""))

        # Zero amount
        res_zero = self.client.post(
            reverse("api_payments_list_create"),
            {"invoice": self.invoice.id, "amount": "0.00", "payment_method": "CASH", "payment_date": today.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(res_zero.status_code, 400)
        self.assertIn("greater than zero", res_zero.json().get("error", ""))

        # Non-numeric
        res_nan = self.client.post(
            reverse("api_payments_list_create"),
            {"invoice": self.invoice.id, "amount": "abc", "payment_method": "CASH", "payment_date": today.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(res_nan.status_code, 400)
        self.assertIn("valid payment amount", res_nan.json().get("error", ""))

    def test_invalid_payment_date(self):
        self.client.force_login(self.user)
        res = self.client.post(
            reverse("api_payments_list_create"),
            {"invoice": self.invoice.id, "amount": "100.00", "payment_method": "CASH", "payment_date": "not-a-date"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("valid payment date", res.json().get("error", "").lower())

    def test_invalid_payment_method(self):
        self.client.force_login(self.user)
        today = date.today()
        res = self.client.post(
            reverse("api_payments_list_create"),
            {"invoice": self.invoice.id, "amount": "100.00", "payment_method": "CRYPTO", "payment_date": today.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid payment method", res.json().get("error", ""))

    def test_overdue_invoice_status_transition(self):
        self.client.force_login(self.user)
        # Set invoice due_date to yesterday
        yesterday = date.today() - timedelta(days=1)
        self.invoice.due_date = yesterday
        self.invoice.save()

        # Make partial payment (e.g. 100 of 500)
        res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": self.invoice.id,
                "amount": "100.00",
                "payment_method": "CASH",
                "payment_date": date.today().isoformat(),
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["invoice_status"], "OVERDUE")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "OVERDUE")

    def test_cross_company_isolation(self):
        self.client.force_login(self.user)
        today = date.today()

        # Cannot record payment against another company's invoice
        res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": self.other_invoice.id,
                "amount": "100.00",
                "payment_method": "CASH",
                "payment_date": today.isoformat(),
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json().get("error"), "Invalid invoice selected.")

        # Create payment under other company
        other_payment = Payment.objects.create(
            invoice=self.other_invoice,
            amount=Decimal("100.00"),
            payment_method="UPI",
            payment_date=today,
        )

        # GET payment detail of other company -> 404
        res_detail = self.client.get(
            reverse("api_payment_detail", kwargs={"payment_id": other_payment.id})
        )
        self.assertEqual(res_detail.status_code, 404)

        # Other company payments do not appear in Alpha's list
        res_list = self.client.get(reverse("api_payments_list_create"))
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()["payments"]), 0)
        self.assertEqual(res_list.json()["stats"]["payment_count"], 0)

    def test_search_and_filter_payments(self):
        self.client.force_login(self.user)
        today = date.today()
        p1 = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("100.00"),
            payment_method="UPI",
            payment_date=today,
        )
        # Create second invoice and payment
        inv2 = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="INV-ALPHA-200",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("400.00"),
        )
        p2 = Payment.objects.create(
            invoice=inv2,
            amount=Decimal("200.00"),
            payment_method="CASH",
            payment_date=today,
        )

        # Search by invoice number
        res_search = self.client.get(reverse("api_payments_list_create") + "?search=ALPHA-200")
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual(len(res_search.json()["payments"]), 1)
        self.assertEqual(res_search.json()["payments"][0]["id"], p2.id)

        # Filter by payment method
        res_method = self.client.get(reverse("api_payments_list_create") + "?method=UPI")
        self.assertEqual(res_method.status_code, 200)
        self.assertEqual(len(res_method.json()["payments"]), 1)
        self.assertEqual(res_method.json()["payments"][0]["id"], p1.id)

        # Filter by invoice_id
        res_inv = self.client.get(reverse("api_payments_list_create") + f"?invoice_id={self.invoice.id}")
        self.assertEqual(res_inv.status_code, 200)
        self.assertEqual(len(res_inv.json()["payments"]), 1)
        self.assertEqual(res_inv.json()["payments"][0]["id"], p1.id)

    def test_payment_detail_and_immutability(self):
        self.client.force_login(self.user)
        today = date.today()
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("100.00"),
            payment_method="UPI",
            payment_date=today,
        )

        # GET detail -> 200
        res_get = self.client.get(
            reverse("api_payment_detail", kwargs={"payment_id": payment.id})
        )
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["amount"], "100.00")
        self.assertEqual(res_get.json()["payment_method"], "UPI")

        # Immutability: PUT, PATCH, DELETE must return 405 Method Not Allowed
        res_put = self.client.put(
            reverse("api_payment_detail", kwargs={"payment_id": payment.id}),
            {"amount": "200.00"},
            content_type="application/json",
        )
        self.assertEqual(res_put.status_code, 405)

        res_patch = self.client.patch(
            reverse("api_payment_detail", kwargs={"payment_id": payment.id}),
            {"amount": "200.00"},
            content_type="application/json",
        )
        self.assertEqual(res_patch.status_code, 405)

        res_delete = self.client.delete(
            reverse("api_payment_detail", kwargs={"payment_id": payment.id})
        )
        self.assertEqual(res_delete.status_code, 405)

    def test_unauthenticated_access(self):
        res_list = self.client.get(reverse("api_payments_list_create"))
        self.assertEqual(res_list.status_code, 403)

        res_post = self.client.post(
            reverse("api_payments_list_create"),
            {"invoice": 1, "amount": "10.00"},
            content_type="application/json",
        )
        self.assertEqual(res_post.status_code, 403)

        res_detail = self.client.get(reverse("api_payment_detail", kwargs={"payment_id": 1}))
        self.assertEqual(res_detail.status_code, 403)






class ReportsAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="repuser@example.com",
            email="repuser@example.com",
            password="SecurePassword123!",
            first_name="Report Manager",
        )
        self.company = Company.objects.create(
            name="Alpha Corp",
            email="alpha@corp.com",
            phone="1111111111",
            address="111 Alpha Way",
        )
        self.membership = Membership.objects.create(
            user=self.user,
            company=self.company,
            role="OWNER",
        )

        self.customer1 = Customer.objects.create(
            company=self.company,
            name="Customer One",
            email="c1@alpha.com",
            phone="9998887771",
        )
        self.customer2 = Customer.objects.create(
            company=self.company,
            name="Customer Two",
            email="c2@alpha.com",
            phone="9998887772",
        )

        # Other company for isolation tests
        self.other_user = User.objects.create_user(
            username="otherrep@example.com",
            email="otherrep@example.com",
            password="SecurePassword123!",
            first_name="Other Manager",
        )
        self.other_company = Company.objects.create(
            name="Beta Corp",
            email="beta@corp.com",
            phone="2222222222",
            address="222 Beta Ave",
        )
        self.other_membership = Membership.objects.create(
            user=self.other_user,
            company=self.other_company,
            role="OWNER",
        )
        self.other_customer = Customer.objects.create(
            company=self.other_company,
            name="Beta Customer",
            email="c@beta.com",
            phone="8887776662",
        )

    def test_reports_summary_empty_company(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["metrics"]["total_invoiced"], "0.00")
        self.assertEqual(data["metrics"]["total_collected"], "0.00")
        self.assertEqual(data["metrics"]["total_outstanding"], "0.00")
        self.assertEqual(data["metrics"]["overdue_amount"], "0.00")
        self.assertEqual(data["metrics"]["collection_rate"], 0.0)
        self.assertEqual(data["top_customers"], [])
        self.assertEqual(len(data["monthly_trend"]), 6)
        # All 5 statuses present with 0 count
        for st in ["PAID", "SENT", "OVERDUE", "DRAFT", "CANCELLED"]:
            self.assertEqual(data["invoice_counts"][st]["count"], 0)

    def test_reports_revenue_invoiced_vs_collected_distinction(self):
        self.client.force_login(self.user)
        today = date.today()
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-REV-01",
            issue_date=today,
            due_date=today + timedelta(days=15),
            status="SENT",
            subtotal=Decimal("1000.00"),
            total=Decimal("1000.00"),
        )
        Payment.objects.create(
            invoice=inv,
            amount=Decimal("400.00"),
            payment_method="UPI",
            payment_date=today,
        )

        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Invoiced is 1000, collected is 400 - NEVER confused!
        self.assertEqual(data["metrics"]["total_invoiced"], "1000.00")
        self.assertEqual(data["metrics"]["total_collected"], "400.00")
        self.assertEqual(data["metrics"]["total_outstanding"], "600.00")
        self.assertEqual(data["metrics"]["overdue_amount"], "0.00")
        self.assertEqual(data["metrics"]["collection_rate"], 40.0)

    def test_reports_outstanding_and_overdue_calculations(self):
        self.client.force_login(self.user)
        today = date.today()

        # Invoice 1: future due date, partially paid
        inv1 = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-CALC-1",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("1000.00"),
        )
        Payment.objects.create(
            invoice=inv1,
            amount=Decimal("300.00"),
            payment_method="CASH",
            payment_date=today,
        )

        # Invoice 2: overdue due date, partially paid
        inv2 = Invoice.objects.create(
            company=self.company,
            customer=self.customer2,
            invoice_number="INV-CALC-2",
            issue_date=today - timedelta(days=30),
            due_date=today - timedelta(days=5),
            status="OVERDUE",
            total=Decimal("500.00"),
        )
        Payment.objects.create(
            invoice=inv2,
            amount=Decimal("100.00"),
            payment_method="BANK",
            payment_date=today,
        )

        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # inv1 remaining = 700 (not overdue)
        # inv2 remaining = 400 (overdue)
        # Total outstanding = 1100.00
        # Total overdue = 400.00
        self.assertEqual(data["metrics"]["total_outstanding"], "1100.00")
        self.assertEqual(data["metrics"]["overdue_amount"], "400.00")

    def test_reports_cancelled_invoice_exclusion(self):
        self.client.force_login(self.user)
        today = date.today()
        Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-CANCELLED-1",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="CANCELLED",
            total=Decimal("5000.00"),
        )

        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Cancelled invoice not counted in invoiced or outstanding
        self.assertEqual(data["metrics"]["total_invoiced"], "0.00")
        self.assertEqual(data["metrics"]["total_outstanding"], "0.00")
        self.assertEqual(data["invoice_counts"]["CANCELLED"]["count"], 1)

    def test_reports_all_five_invoice_statuses(self):
        self.client.force_login(self.user)
        today = date.today()
        statuses = ["PAID", "SENT", "OVERDUE", "DRAFT", "CANCELLED"]
        for idx, st in enumerate(statuses):
            Invoice.objects.create(
                company=self.company,
                customer=self.customer1,
                invoice_number=f"INV-ST-{idx}",
                issue_date=today,
                due_date=today + timedelta(days=5),
                status=st,
                total=Decimal("100.00"),
            )

        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for st in statuses:
            self.assertEqual(data["invoice_counts"][st]["count"], 1)
            self.assertEqual(data["invoice_counts"][st]["total_amount"], "100.00")

    def test_reports_date_filtering_presets_and_custom(self):
        self.client.force_login(self.user)
        today = date.today()

        # Invoiced 45 days ago
        inv_old = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-OLD-1",
            issue_date=today - timedelta(days=45),
            due_date=today - timedelta(days=30),
            status="SENT",
            total=Decimal("500.00"),
        )
        # Payment 45 days ago
        Payment.objects.create(
            invoice=inv_old,
            amount=Decimal("200.00"),
            payment_method="CASH",
            payment_date=today - timedelta(days=45),
        )

        # Invoiced today
        inv_new = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-NEW-1",
            issue_date=today,
            due_date=today + timedelta(days=15),
            status="SENT",
            total=Decimal("1000.00"),
        )
        # Payment today
        Payment.objects.create(
            invoice=inv_new,
            amount=Decimal("300.00"),
            payment_method="UPI",
            payment_date=today,
        )

        # 1. Preset 30d: only includes items within last 30 days
        res_30d = self.client.get(reverse("api_reports_summary") + "?preset=30d")
        self.assertEqual(res_30d.status_code, 200)
        data_30d = res_30d.json()
        self.assertEqual(data_30d["metrics"]["total_invoiced"], "1000.00")
        self.assertEqual(data_30d["metrics"]["total_collected"], "300.00")
        # Point-in-time outstanding balance is still actual full active balance (300 + 700 = 1000)
        self.assertEqual(data_30d["metrics"]["total_outstanding"], "1000.00")

        # 2. Preset all: includes all items
        res_all = self.client.get(reverse("api_reports_summary") + "?preset=all")
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.json()
        self.assertEqual(data_all["metrics"]["total_invoiced"], "1500.00")
        self.assertEqual(data_all["metrics"]["total_collected"], "500.00")

        # 3. Custom date range
        custom_start = (today - timedelta(days=10)).isoformat()
        custom_end = today.isoformat()
        res_custom = self.client.get(
            reverse("api_reports_summary") + f"?start_date={custom_start}&end_date={custom_end}"
        )
        self.assertEqual(res_custom.status_code, 200)
        self.assertEqual(res_custom.json()["metrics"]["total_invoiced"], "1000.00")

    def test_reports_invalid_date_parameters(self):
        self.client.force_login(self.user)
        # Invalid start_date format
        res1 = self.client.get(reverse("api_reports_summary") + "?start_date=2026-13-45")
        self.assertEqual(res1.status_code, 400)
        self.assertIn("Invalid start_date format", res1.json().get("error", ""))

        # start_date > end_date
        res2 = self.client.get(reverse("api_reports_summary") + "?start_date=2026-11-10&end_date=2026-11-01")
        self.assertEqual(res2.status_code, 400)
        self.assertIn("start_date cannot be after end_date", res2.json().get("error", ""))

        # Invalid preset
        res3 = self.client.get(reverse("api_reports_summary") + "?preset=random_preset")
        self.assertEqual(res3.status_code, 400)
        self.assertIn("Invalid preset", res3.json().get("error", ""))

    def test_reports_top_customers_no_join_double_counting(self):
        self.client.force_login(self.user)
        today = date.today()

        # Customer 1 has 2 invoices of 1000 each = 2000 total invoiced
        inv1 = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-C1-A",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("1000.00"),
        )
        inv2 = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-C1-B",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("1000.00"),
        )
        # 2 payments on inv1, 1 payment on inv2
        Payment.objects.create(invoice=inv1, amount=Decimal("200.00"), payment_method="CASH", payment_date=today)
        Payment.objects.create(invoice=inv1, amount=Decimal("300.00"), payment_method="CASH", payment_date=today)
        Payment.objects.create(invoice=inv2, amount=Decimal("400.00"), payment_method="CASH", payment_date=today)

        # Customer 2 has 1 invoice of 800
        inv3 = Invoice.objects.create(
            company=self.company,
            customer=self.customer2,
            invoice_number="INV-C2-A",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("800.00"),
        )
        Payment.objects.create(invoice=inv3, amount=Decimal("500.00"), payment_method="UPI", payment_date=today)

        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        top = data["top_customers"]
        self.assertEqual(len(top), 2)
        # Customer 1 ranked #1
        self.assertEqual(top[0]["name"], "Customer One")
        self.assertEqual(top[0]["total_invoiced"], "2000.00")
        self.assertEqual(top[0]["total_collected"], "900.00")
        self.assertEqual(top[0]["outstanding"], "1100.00")

        # Customer 2 ranked #2
        self.assertEqual(top[1]["name"], "Customer Two")
        self.assertEqual(top[1]["total_invoiced"], "800.00")
        self.assertEqual(top[1]["total_collected"], "500.00")
        self.assertEqual(top[1]["outstanding"], "300.00")

    def test_reports_payment_methods_breakdown(self):
        self.client.force_login(self.user)
        today = date.today()
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-METHODS",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("2000.00"),
        )
        Payment.objects.create(invoice=inv, amount=Decimal("600.00"), payment_method="UPI", payment_date=today)
        Payment.objects.create(invoice=inv, amount=Decimal("400.00"), payment_method="CARD", payment_date=today)

        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        methods = {m["method"]: m for m in data["payment_methods"]}
        self.assertEqual(methods["UPI"]["amount"], "600.00")
        self.assertEqual(methods["UPI"]["percentage"], 60.0)
        self.assertEqual(methods["CARD"]["amount"], "400.00")
        self.assertEqual(methods["CARD"]["percentage"], 40.0)
        self.assertEqual(methods["CASH"]["amount"], "0.00")
        self.assertEqual(methods["CASH"]["percentage"], 0.0)

    def test_reports_cross_company_isolation(self):
        self.client.force_login(self.user)
        today = date.today()
        # Create other company invoice and payment
        other_inv = Invoice.objects.create(
            company=self.other_company,
            customer=self.other_customer,
            invoice_number="INV-BETA-REPORT",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("9999.00"),
        )
        Payment.objects.create(
            invoice=other_inv,
            amount=Decimal("9999.00"),
            payment_method="BANK",
            payment_date=today,
        )

        res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Alpha Corp should see 0
        self.assertEqual(data["metrics"]["total_invoiced"], "0.00")
        self.assertEqual(data["metrics"]["total_collected"], "0.00")
        self.assertEqual(data["top_customers"], [])

    def test_reports_export_pdf_endpoint(self):
        self.client.force_login(self.user)
        today = date.today()
        inv = Invoice.objects.create(
            company=self.company,
            customer=self.customer1,
            invoice_number="INV-PDF-REP",
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="SENT",
            total=Decimal("500.00"),
        )
        Payment.objects.create(
            invoice=inv,
            amount=Decimal("200.00"),
            payment_method="CASH",
            payment_date=today,
        )

        res = self.client.get(reverse("api_export_report"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertIn("invoiceflow_report.pdf", res["Content-Disposition"])

    def test_reports_unauthenticated_access(self):
        res_summary = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(res_summary.status_code, 403)

        res_pdf = self.client.get(reverse("api_export_report"))
        # @login_required redirects unauthenticated to login
        self.assertEqual(res_pdf.status_code, 302)


class FullBusinessLifecycleAndIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_complete_business_lifecycle(self):
        """
        End-to-End full business lifecycle test:
        1. Register user
        2. Authenticate user
        3. Create company profile
        4. Create customer
        5. Create products
        6. Create invoice with multiple items & verify subtotal, tax, discount, total
        7. Record partial payment & verify remaining balance and status (SENT)
        8. Record final payment & verify status transition to PAID
        9. Attempt overpayment & verify rejection (400)
        10. Fetch Reports summary & verify invoiced, collected, outstanding & customer figures
        11. Verify invoice PDF generation
        12. Verify financial report PDF generation
        """
        # 1. Register user
        signup_res = self.client.post(
            reverse("api_signup"),
            {
                "full_name": "Integration User",
                "email": "e2e_user@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
            },
            content_type="application/json",
        )
        self.assertEqual(signup_res.status_code, 201)

        # 2. Authenticate
        login_res = self.client.post(
            reverse("api_login"),
            {
                "email": "e2e_user@example.com",
                "password": "StrongPassword123!",
            },
            content_type="application/json",
        )
        self.assertEqual(login_res.status_code, 200)

        # 3. Create company
        company_res = self.client.post(
            reverse("api_create_company"),
            {
                "name": "Integration Tech Ltd",
                "email": "contact@integtech.com",
                "phone": "+91 9876543210",
                "address": "123 Tech Park, Bangalore",
                "gst_number": "29ABCDE1234F1Z5",
            },
            content_type="application/json",
        )
        self.assertEqual(company_res.status_code, 201)
        company_id = company_res.json()["company"]["id"]

        # Verify active company
        user_res = self.client.get(reverse("api_current_user"))
        self.assertEqual(user_res.json()["current_company"]["id"], company_id)

        # 4. Create customer
        cust_res = self.client.post(
            reverse("api_customers_list_create"),
            {
                "name": "Global Solutions Inc",
                "email": "billing@globalsol.com",
                "phone": "+91 9123456789",
                "address": "456 Enterprise Way",
                "gst_number": "29XYZAB5678C1Z2",
            },
            content_type="application/json",
        )
        self.assertEqual(cust_res.status_code, 201)
        customer_id = cust_res.json()["customer"]["id"]

        # 5. Create products
        # Product 1: 100 base + 10% tax
        p1_res = self.client.post(
            reverse("api_products_list_create"),
            {
                "name": "Web Hosting",
                "description": "Annual cloud hosting",
                "price": "100.00",
                "tax": "10.00",
            },
            content_type="application/json",
        )
        self.assertEqual(p1_res.status_code, 201)
        p1_id = p1_res.json()["product"]["id"]

        # Product 2: 200 base + 5% tax
        p2_res = self.client.post(
            reverse("api_products_list_create"),
            {
                "name": "Domain SSL",
                "description": "Wildcard certificate",
                "price": "200.00",
                "tax": "5.00",
            },
            content_type="application/json",
        )
        self.assertEqual(p2_res.status_code, 201)
        p2_id = p2_res.json()["product"]["id"]

        # 6. Create multi-item invoice
        # Item 1: 2 * 100 = 200 subtotal, 20 tax, line_total = 220
        # Item 2: 1 * 200 = 200 subtotal, 10 tax, line_total = 210
        # Subtotal = 400.00, Tax = 30.00, Overall Discount = 30.00
        # Total = 400.00 + 30.00 - 30.00 = 400.00
        today = date.today()
        due = today + timedelta(days=15)
        inv_payload = {
            "invoice_number": "INV-E2E-001",
            "customer": customer_id,
            "issue_date": str(today),
            "due_date": str(due),
            "discount": "30.00",
            "notes": "E2E Lifecycle Invoice",
            "items": [
                {"product": p1_id, "quantity": 2, "tax": "10.00", "discount": 0},
                {"product": p2_id, "quantity": 1, "tax": "5.00", "discount": 0},
            ],
        }
        inv_res = self.client.post(
            reverse("api_invoices_list_create"),
            inv_payload,
            content_type="application/json",
        )
        self.assertEqual(inv_res.status_code, 201)
        inv_data = inv_res.json()["invoice"]
        invoice_id = inv_data["id"]

        self.assertEqual(Decimal(str(inv_data["subtotal"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(inv_data["tax_amount"])), Decimal("30.00"))
        self.assertEqual(Decimal(str(inv_data["discount_amount"])), Decimal("30.00"))
        self.assertEqual(Decimal(str(inv_data["total"])), Decimal("400.00"))
        self.assertEqual(inv_data["status"], "SENT")
        self.assertEqual(Decimal(str(inv_data["paid_amount"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(inv_data["remaining_amount"])), Decimal("400.00"))

        # 7. Record partial payment
        pay1_res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": invoice_id,
                "amount": "150.00",
                "payment_method": "UPI",
                "payment_date": str(today),
                "notes": "First milestone payment",
            },
            content_type="application/json",
        )
        self.assertEqual(pay1_res.status_code, 201)

        # 8. Verify remaining balance and status
        inv_detail1 = self.client.get(reverse("api_invoice_detail", args=[invoice_id])).json()["invoice"]
        self.assertEqual(Decimal(str(inv_detail1["paid_amount"])), Decimal("150.00"))
        self.assertEqual(Decimal(str(inv_detail1["remaining_amount"])), Decimal("250.00"))
        # Per existing business rule, partially paid invoices maintain SENT until due date
        self.assertEqual(inv_detail1["status"], "SENT")

        # 9. Record final payment
        pay2_res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": invoice_id,
                "amount": "250.00",
                "payment_method": "BANK",
                "payment_date": str(today),
                "notes": "Final settlement",
            },
            content_type="application/json",
        )
        self.assertEqual(pay2_res.status_code, 201)

        # 10. Verify invoice becomes PAID
        inv_detail2 = self.client.get(reverse("api_invoice_detail", args=[invoice_id])).json()["invoice"]
        self.assertEqual(Decimal(str(inv_detail2["paid_amount"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(inv_detail2["remaining_amount"])), Decimal("0.00"))
        self.assertEqual(inv_detail2["status"], "PAID")

        # 11. Attempt overpayment & verify rejection
        overpay_res = self.client.post(
            reverse("api_payments_list_create"),
            {
                "invoice": invoice_id,
                "amount": "50.00",
                "payment_method": "CASH",
                "payment_date": str(today),
            },
            content_type="application/json",
        )
        self.assertEqual(overpay_res.status_code, 400)
        self.assertIn("fully paid", overpay_res.json().get("error", "").lower())

        # 12 & 13. Fetch Reports summary
        rep_res = self.client.get(reverse("api_reports_summary"))
        self.assertEqual(rep_res.status_code, 200)
        rep_data = rep_res.json()

        self.assertEqual(Decimal(str(rep_data["metrics"]["total_invoiced"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(rep_data["metrics"]["total_collected"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(rep_data["metrics"]["total_outstanding"])), Decimal("0.00"))
        self.assertEqual(rep_data["invoice_counts"]["PAID"]["count"], 1)
        self.assertEqual(len(rep_data["top_customers"]), 1)
        self.assertEqual(rep_data["top_customers"][0]["name"], "Global Solutions Inc")
        self.assertEqual(Decimal(str(rep_data["top_customers"][0]["total_invoiced"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(rep_data["top_customers"][0]["total_collected"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(rep_data["top_customers"][0]["outstanding"])), Decimal("0.00"))

        # 14. Verify invoice PDF generation
        pdf_res = self.client.get(reverse("api_invoice_pdf", args=[invoice_id]))
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res["Content-Type"], "application/pdf")
        self.assertTrue(len(pdf_res.content) > 100)

        # 15. Verify financial report PDF generation
        rep_pdf_res = self.client.get(reverse("api_export_report"))
        self.assertEqual(rep_pdf_res.status_code, 200)
        self.assertEqual(rep_pdf_res["Content-Type"], "application/pdf")
        self.assertTrue(len(rep_pdf_res.content) > 100)

    def test_multi_company_isolation_integration(self):
        """
        Verify complete multi-company tenant data isolation:
        - User B cannot see, edit, or delete User A's customers, products, invoices, or payments.
        - Forged invoice IDs in payment creation are rejected.
        - Reports reflect only active company data.
        - Switching active company context prevents previous company data leakage.
        """
        # User A and Company A
        user_a = User.objects.create_user("usera_iso", "usera_iso@example.com", "Password123!")
        comp_a = Company.objects.create(name="Company A Iso", email="a@comp.com", phone="111", address="Addr A")
        Membership.objects.create(user=user_a, company=comp_a, role="OWNER")

        cust_a = Customer.objects.create(company=comp_a, name="Customer A", email="cust_a@comp.com", phone="111", address="A")
        prod_a = Product.objects.create(company=comp_a, name="Product A", price=Decimal("100.00"), tax=Decimal("0.00"))
        inv_a = Invoice.objects.create(
            company=comp_a, customer=cust_a, invoice_number="INV-A-100",
            issue_date=date.today(), due_date=date.today() + timedelta(days=7),
            total=Decimal("100.00"), status="SENT"
        )
        InvoiceItem.objects.create(invoice=inv_a, product=prod_a, quantity=1, unit_price=Decimal("100.00"), line_total=Decimal("100.00"))
        Payment.objects.create(invoice=inv_a, amount=Decimal("50.00"), payment_method="CASH", payment_date=date.today())

        # User B and Company B
        user_b = User.objects.create_user("userb_iso", "userb_iso@example.com", "Password123!")
        comp_b = Company.objects.create(name="Company B Iso", email="b@comp.com", phone="222", address="Addr B")
        Membership.objects.create(user=user_b, company=comp_b, role="OWNER")

        self.client.force_login(user_b)
        session = self.client.session
        session["current_company_id"] = comp_b.id
        session.save()

        # User B should NOT see Company A's data in lists
        custs_b = self.client.get(reverse("api_customers_list_create")).json()
        self.assertEqual(len(custs_b), 0)

        prods_b = self.client.get(reverse("api_products_list_create")).json()
        self.assertEqual(len(prods_b), 0)

        invs_b = self.client.get(reverse("api_invoices_list_create")).json()
        self.assertEqual(len(invs_b), 0)

        pays_b = self.client.get(reverse("api_payments_list_create")).json()
        self.assertEqual(len(pays_b["payments"]), 0)

        # Direct access with forged IDs -> 404
        self.assertEqual(self.client.get(reverse("api_customer_detail", args=[cust_a.id])).status_code, 404)
        self.assertEqual(
            self.client.put(
                reverse("api_customer_detail", args=[cust_a.id]),
                {"name": "Hacked", "email": "h@h.com", "phone": "1", "address": "1"},
                content_type="application/json",
            ).status_code,
            404,
        )
        self.assertEqual(self.client.delete(reverse("api_customer_detail", args=[cust_a.id])).status_code, 404)

        self.assertEqual(self.client.get(reverse("api_product_detail", args=[prod_a.id])).status_code, 404)
        self.assertEqual(self.client.delete(reverse("api_product_detail", args=[prod_a.id])).status_code, 404)

        self.assertEqual(self.client.get(reverse("api_invoice_detail", args=[inv_a.id])).status_code, 404)

        # Forged payment against Company A's invoice -> 400 (Invalid invoice selected)
        pay_hack_res = self.client.post(
            reverse("api_payments_list_create"),
            {"invoice": inv_a.id, "amount": "20.00", "payment_method": "UPI", "payment_date": str(date.today())},
            content_type="application/json",
        )
        self.assertEqual(pay_hack_res.status_code, 400)
        self.assertIn("Invalid invoice selected", pay_hack_res.json().get("error", ""))

        # Reports for User B reflect 0 invoiced / collected
        rep_b = self.client.get(reverse("api_reports_summary")).json()
        self.assertEqual(rep_b["metrics"]["total_invoiced"], "0.00")
        self.assertEqual(rep_b["metrics"]["total_collected"], "0.00")

        # Company switching test: User A with two companies
        comp_a2 = Company.objects.create(name="Company A2 Iso", email="a2@comp.com", phone="333", address="Addr A2")
        Membership.objects.create(user=user_a, company=comp_a2, role="OWNER")

        self.client.force_login(user_a)
        session = self.client.session
        session["current_company_id"] = comp_a2.id
        session.save()

        # Under Company A2, User A sees 0 customers (Company A's customers are isolated)
        custs_a2 = self.client.get(reverse("api_customers_list_create")).json()
        self.assertEqual(len(custs_a2), 0)

    def test_authentication_and_unauthorized_access(self):
        """
        Verify unauthenticated API requests are rejected across endpoints,
        and session invalidation immediately revokes data access.
        """
        # 1. Unauthenticated requests rejected
        unauth_endpoints = [
            ("GET", reverse("api_customers_list_create")),
            ("GET", reverse("api_products_list_create")),
            ("GET", reverse("api_invoices_list_create")),
            ("GET", reverse("api_payments_list_create")),
            ("GET", reverse("api_reports_summary")),
            ("POST", reverse("api_switch_company", args=[1])),
            ("POST", reverse("api_create_company")),
        ]
        for method, url in unauth_endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, {}, content_type="application/json")
            self.assertEqual(res.status_code, 403, f"Expected 403 for unauth {method} {url}, got {res.status_code}")

        # 2. Session invalidation on logout
        user = User.objects.create_user("tempuser_iso", "temp_iso@example.com", "Password123!")
        comp = Company.objects.create(name="Temp Co Iso", email="temp@co.com", phone="123", address="Temp")
        Membership.objects.create(user=user, company=comp, role="OWNER")

        self.client.force_login(user)
        session = self.client.session
        session["current_company_id"] = comp.id
        session.save()

        # Authenticated access succeeds
        self.assertEqual(self.client.get(reverse("api_customers_list_create")).status_code, 200)

        # Logout invalidates session
        logout_res = self.client.post(reverse("api_logout"), content_type="application/json")
        self.assertEqual(logout_res.status_code, 200)

        # Subsequent access fails with 403
        self.assertEqual(self.client.get(reverse("api_customers_list_create")).status_code, 403)
