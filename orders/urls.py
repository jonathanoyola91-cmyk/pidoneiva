from django.urls import path
from . import views

urlpatterns = [
    path("<slug:slug>/send-whatsapp/", views.send_whatsapp_order, name="send_whatsapp_order"),
]