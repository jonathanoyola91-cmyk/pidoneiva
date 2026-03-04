from django.db import models
from django.utils import timezone

class Order(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    buyer_name = models.CharField(max_length=120)
    buyer_phone = models.CharField(max_length=40)
    buyer_address = models.CharField(max_length=220)
    buyer_notes = models.TextField(blank=True)

    total = models.IntegerField(default=0)

    number = models.CharField(max_length=20, unique=True, blank=True)

    def __str__(self):
        return self.number or f"Order {self.id}"

    # ✅ AQUÍ VA EL CÓDIGO
    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating and not self.number:
            self.number = f"PN-NEI-{self.pk:06d}"
            super().save(update_fields=["number"])