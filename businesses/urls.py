from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("negocio/<slug:slug>/", views.business_detail, name="business_detail"),

    path("w/<slug:slug>/", views.whatsapp_redirect, name="whatsapp_redirect"),
    path("w/item/<int:item_id>/", views.whatsapp_item_redirect, name="whatsapp_item_redirect"),

    path("cart/<slug:slug>/add/<int:item_id>/", views.cart_add, name="cart_add"),
    path("cart/<slug:slug>/update/<int:item_id>/", views.cart_update, name="cart_update"),
    path("cart/<slug:slug>/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),
    path("cart/<slug:slug>/clear/", views.cart_clear, name="cart_clear"),
    path("cart/<slug:slug>/buyer/", views.cart_set_buyer, name="cart_set_buyer"),
    path("cart/<slug:slug>/whatsapp/", views.cart_whatsapp, name="cart_whatsapp"),
    path("negocio/<slug:slug>/check-customer-phone/", views.check_customer_phone, name="check_customer_phone"),
]