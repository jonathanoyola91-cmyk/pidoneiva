from django.urls import path
from . import views

urlpatterns = [
    path(
        "negocio/<slug:slug>/cart/update-json/<int:item_id>/",
        views.cart_update_json,
        name="cart_update_json"
    ),
    path(
        "cart/active/",
        views.go_to_active_cart,
        name="go_to_active_cart"
    ),
    path(
        "cart/clear-and-switch/<slug:slug>/",
        views.cart_clear_and_switch,
        name="cart_clear_and_switch"
    ),
]