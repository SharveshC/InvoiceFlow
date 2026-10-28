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

