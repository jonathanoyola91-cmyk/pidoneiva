from django.db import models


class AccessRequest(models.Model):
    class RequestType(models.TextChoices):
        RESTAURANT = "RESTAURANT", "Restaurante"
        COMMERCE = "COMMERCE", "Comercio"

    created_at = models.DateTimeField(auto_now_add=True)

    name = models.CharField(max_length=120)  # nombre del negocio
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    zone = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=160, blank=True)

    contact_name = models.CharField(max_length=120, blank=True)
    whatsapp = models.CharField(max_length=30)  # 573001112233
    email = models.EmailField(blank=True)

    notes = models.TextField(blank=True)

    is_processed = models.BooleanField(default=False)

    created_username = models.CharField(max_length=150, blank=True)
    temp_password = models.CharField(max_length=50, blank=True)
    created_business_slug = models.CharField(max_length=140, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_request_type_display()})"