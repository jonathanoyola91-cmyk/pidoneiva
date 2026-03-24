from django.contrib import admin
from .models import Order, OrderItem, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "phone",
        "name",
        "successful_orders",
        "failed_orders",
        "is_blocked_cash",
        "created_at",
    )
    search_fields = ("phone", "name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "business", "buyer_name", "buyer_phone", "total", "created_at")
    search_fields = ("number", "buyer_name", "buyer_phone")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "qty", "price")