from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from businesses.models import Business
from menu.models import MenuCategory, MenuItem
from orders.models import Order, CustomerProfile
from orders.utils import normalize_phone

from .serializers import (
    AppCustomerSerializer,
    BusinessSerializer,
    CreateOrderSerializer,
    LoginCustomerSerializer,
    MenuCategorySerializer,
    MenuItemSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    PaymentOptionsSerializer,
    RegisterCustomerSerializer,
)


@api_view(["GET"])
def businesses_list(request):
    businesses = Business.objects.filter(is_active=True, is_approved=True)
    serializer = BusinessSerializer(businesses, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
def business_categories(request, slug):
    business = get_object_or_404(
        Business,
        slug=slug,
        is_active=True,
        is_approved=True
    )
    categories = MenuCategory.objects.filter(business=business).order_by("order", "name")
    serializer = MenuCategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def business_items(request, slug):
    business = get_object_or_404(
        Business,
        slug=slug,
        is_active=True,
        is_approved=True
    )

    items = (
        MenuItem.objects
        .filter(business=business, is_available=True)
        .select_related("category")
        .order_by("order", "name")
    )

    serializer = MenuItemSerializer(items, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
def business_detail(request, slug):
    business = get_object_or_404(
        Business,
        slug=slug,
        is_active=True,
        is_approved=True
    )

    categories = MenuCategory.objects.filter(business=business).order_by("order", "name")
    items = (
        MenuItem.objects
        .filter(business=business, is_available=True)
        .select_related("category")
        .order_by("order", "name")
    )

    data = {
        "business": BusinessSerializer(business, context={"request": request}).data,
        "categories": MenuCategorySerializer(categories, many=True).data,
        "items": MenuItemSerializer(items, many=True, context={"request": request}).data,
    }

    return Response(data)


@api_view(["POST"])
def register_customer(request):
    serializer = RegisterCustomerSerializer(data=request.data)

    if serializer.is_valid():
        app_customer = serializer.save()
        login(request, app_customer.user)
        return Response(
            {
                "ok": True,
                "customer": AppCustomerSerializer(app_customer).data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "ok": False,
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
def login_customer(request):
    serializer = LoginCustomerSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data["user"]
        app_customer = serializer.validated_data["app_customer"]
        login(request, user)

        return Response(
            {
                "ok": True,
                "customer": AppCustomerSerializer(app_customer).data,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "ok": False,
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
def logout_customer(request):
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    if not hasattr(request.user, "app_customer"):
        return Response(
            {"ok": False, "error": "El usuario no tiene perfil de cliente."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        "ok": True,
        "customer": AppCustomerSerializer(request.user.app_customer).data,
    })


@api_view(["POST"])
def create_order(request):
    serializer = CreateOrderSerializer(data=request.data, context={"request": request})

    if serializer.is_valid():
        order = serializer.save()
        return Response(
            {
                "ok": True,
                "order_id": order.id,
                "order_number": order.number,
                "total": order.total,
                "payment_method": order.payment_method,
                "status": order.status,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "ok": False,
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
def payment_options(request):
    serializer = PaymentOptionsSerializer(data=request.data)

    if serializer.is_valid():
        customer_phone = serializer.validated_data["customer_phone"]

        customer = CustomerProfile.objects.filter(phone=customer_phone).first()

        if not customer:
            is_first_order = True
            can_pay_cash = False
        else:
            is_first_order = customer.successful_orders == 0
            can_pay_cash = customer.can_pay_cash()

        allowed_payment_methods = [Order.PAYMENT_TRANSFER]
        if can_pay_cash:
            allowed_payment_methods.append(Order.PAYMENT_CASH)

        return Response(
            {
                "ok": True,
                "is_first_order": is_first_order,
                "can_pay_cash": can_pay_cash,
                "allowed_payment_methods": allowed_payment_methods,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "ok": False,
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET"])
def orders_by_phone(request):
    phone = normalize_phone(request.GET.get("phone"))

    if not phone:
        return Response(
            {"ok": False, "error": "Debes enviar el parámetro phone."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    orders = (
        Order.objects
        .filter(buyer_phone=phone)
        .select_related("business")
        .order_by("-created_at")
    )

    serializer = OrderListSerializer(orders, many=True)
    return Response({
        "ok": True,
        "results": serializer.data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_orders(request):
    if not hasattr(request.user, "app_customer"):
        return Response(
            {"ok": False, "error": "El usuario no tiene perfil de cliente."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    orders = (
        Order.objects
        .filter(app_customer=request.user.app_customer)
        .select_related("business")
        .order_by("-created_at")
    )

    serializer = OrderListSerializer(orders, many=True)
    return Response({
        "ok": True,
        "results": serializer.data,
    })


@api_view(["GET"])
def order_detail_api(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("business").prefetch_related("items"),
        id=order_id,
    )

    serializer = OrderDetailSerializer(order)
    return Response({
        "ok": True,
        "order": serializer.data,
    })