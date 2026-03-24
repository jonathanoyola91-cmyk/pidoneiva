from django.urls import path
from . import views

urlpatterns = [
    path("businesses/", views.businesses_list, name="api_businesses_list"),
    path("businesses/<slug:slug>/detail/", views.business_detail, name="api_business_detail"),
    path("businesses/<slug:slug>/categories/", views.business_categories, name="api_business_categories"),
    path("businesses/<slug:slug>/items/", views.business_items, name="api_business_items"),

    path("auth/register/", views.register_customer, name="api_register_customer"),
    path("auth/login/", views.login_customer, name="api_login_customer"),
    path("auth/logout/", views.logout_customer, name="api_logout_customer"),
    path("me/", views.me, name="api_me"),

    path("orders/", views.create_order, name="api_create_order"),
    path("orders/payment-options/", views.payment_options, name="api_payment_options"),
    path("orders/by-phone/", views.orders_by_phone, name="api_orders_by_phone"),
    path("my/orders/", views.my_orders, name="api_my_orders"),
    path("orders/<int:order_id>/", views.order_detail_api, name="api_order_detail"),
]