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

