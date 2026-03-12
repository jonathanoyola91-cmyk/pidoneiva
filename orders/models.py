from django.db import models
from django.utils import timezone


class CustomerProfile(models.Model):
    phone = models.CharField("Celular", max_length=20, unique=True)
    name = models.CharField("Nombre", max_length=120, blank=True)

    successful_orders = models.PositiveIntegerField(default=0)
    failed_orders = models.PositiveIntegerField(default=0)

    # Si quieres bloquear efectivo manualmente a un cliente
    is_blocked_cash = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_pay_cash(self):
        return self.successful_orders >= 1 and not self.is_blocked_cash

    def __str__(self):
        return f"{self.phone} - {self.name or 'Sin nombre'}"


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAKE = "fake"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_CONFIRMED, "Confirmado"),
        (STATUS_DELIVERED, "Entregado"),
        (STATUS_CANCELLED, "Cancelado"),
        (STATUS_FAKE, "Falso"),
    ]

    PAYMENT_TRANSFER = "transfer"
    PAYMENT_CASH = "cash"

    PAYMENT_CHOICES = [
        (PAYMENT_TRANSFER, "Transferencia"),
        (PAYMENT_CASH, "Efectivo"),
    ]

    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    created_at = models.DateTimeField(default=timezone.now)

    buyer_name = models.CharField(max_length=120)
    buyer_phone = models.CharField(max_length=40)
    buyer_address = models.CharField(max_length=220)
    buyer_notes = models.TextField(blank=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default=PAYMENT_TRANSFER,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    total = models.IntegerField(default=0)
    number = models.CharField(max_length=20, unique=True, blank=True)

    def __str__(self):
        return self.number or f"Order {self.id}"

    @property
    def is_first_order_customer(self):
        if not self.customer:
            return True
        return self.customer.successful_orders == 0

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating and not self.number:
            self.number = f"PN-NEI-{self.pk:06d}"
            super().save(update_fields=["number"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)

    # snapshot del producto al comprar
    name = models.CharField(max_length=200)
    qty = models.PositiveIntegerField(default=1)
    price = models.IntegerField(default=0)  # pesos
    subtotal = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        self.subtotal = int(self.qty) * int(self.price)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.qty}x {self.name}"