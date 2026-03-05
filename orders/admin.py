from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "business", "buyer_name", "buyer_phone", "total", "created_at")
    search_fields = ("number", "buyer_name", "buyer_phone")
    list_filter = ("business", "created_at")
    inlines = [OrderItemInline]