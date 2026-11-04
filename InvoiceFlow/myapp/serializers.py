from decimal import Decimal
from django.contrib.auth.models import User
from django.db.models import Sum
from rest_framework import serializers
from .models import Company, Membership, Customer, Product, Invoice, InvoiceItem, Payment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name"]
        read_only_fields = ["id"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "email", "phone", "address", "gst_number", "created_at"]
        read_only_fields = ["id", "created_at"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "company", "name", "email", "phone", "address", "gst_number", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "company", "name", "description", "price", "tax", "created_at"]
        read_only_fields = ["id", "created_at"]


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ["id", "product", "product_name", "quantity", "unit_price", "tax", "discount", "line_total"]
        read_only_fields = ["id"]


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "company",
            "customer",
            "customer_name",
            "invoice_number",
            "issue_date",
            "due_date",
            "status",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total",
            "notes",
            "created_at",
            "items",
            "paid_amount",
            "remaining_amount",
        ]
        read_only_fields = ["id", "created_at"]

    def _get_paid_sum(self, obj):
        if hasattr(obj, "annotated_paid_amount") and obj.annotated_paid_amount is not None:
            return Decimal(str(obj.annotated_paid_amount))
        if hasattr(obj, "_cached_paid_amount"):
            return obj._cached_paid_amount
        if hasattr(obj, "_prefetched_objects_cache") and "payments" in obj._prefetched_objects_cache:
            paid = sum((p.amount for p in obj.payments.all()), Decimal("0.00"))
        else:
            paid = obj.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        obj._cached_paid_amount = paid
        return paid

    def get_paid_amount(self, obj):
        paid = self._get_paid_sum(obj)
        return str(paid)

    def get_remaining_amount(self, obj):
        paid = self._get_paid_sum(obj)
        return str(max(obj.total - paid, Decimal("0.00")))


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    customer_name = serializers.CharField(source="invoice.customer.name", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "customer_name",
            "amount",
            "payment_method",
            "payment_method_display",
            "payment_date",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

