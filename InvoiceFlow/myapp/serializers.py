from rest_framework import serializers
from django.contrib.auth.models import User
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
        ]
        read_only_fields = ["id", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "invoice", "amount", "payment_method", "payment_date", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]

