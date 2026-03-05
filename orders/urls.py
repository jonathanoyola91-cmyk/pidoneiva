from django.urls import path
from . import views

urlpatterns = [
    path("negocio/<slug:slug>/cart/update-json/<int:item_id>/", views.cart_update_json, name="cart_update_json"),
    
]