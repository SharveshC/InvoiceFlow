from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    gst_number = models.CharField(max_length=15, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Membership(models.Model):

    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Admin"),
        ("STAFF", "Staff"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="memberships"
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="STAFF")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"], name="unique_user_company"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.company.name}"


class Customer(models.Model):

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="customers"
    )

    name = models.CharField(max_length=200)

    email = models.EmailField()

    phone = models.CharField(max_length=20)

    address = models.TextField()

    gst_number = models.CharField(max_length=15, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Product(models.Model):

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="products"
    )

    name = models.CharField(max_length=200)

    description = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("CANCELLED", "Cancelled"),
    ]

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="invoices"
    )

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="invoices"
    )

    invoice_number = models.CharField(max_length=50)

    issue_date = models.DateField()

    due_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "invoice_number"],
                name="unique_invoice_number_per_company",
            )
        ]

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="invoice_items"
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.name}"
