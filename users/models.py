from django.db import models
from django.contrib.auth.models import User


class AccessRequest(models.Model):
    class RequestType(models.TextChoices):
        RESTAURANT = "RESTAURANT", "Restaurante"
        COMMERCE = "COMMERCE", "Comercio"

    created_at = models.DateTimeField(auto_now_add=True)

    name = models.CharField(max_length=120)
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    zone = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=160, blank=True)

    contact_name = models.CharField(max_length=120, blank=True)
    whatsapp = models.CharField(max_length=30)
    email = models.EmailField(blank=True)

    notes = models.TextField(blank=True)

    is_processed = models.BooleanField(default=False)

    created_username = models.CharField(max_length=150, blank=True)
    temp_password = models.CharField(max_length=50, blank=True)
    created_business_slug = models.CharField(max_length=140, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_request_type_display()})"


class AppCustomer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="app_customer",
    )
    phone = models.CharField("Celular", max_length=20, unique=True)
    full_name = models.CharField("Nombre completo", max_length=120)
    default_address = models.CharField("Dirección principal", max_length=220, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name