from datetime import datetime, time, timedelta
from decimal import Decimal
import calendar

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def add_one_month(dt):
    year = dt.year
    month = dt.month + 1
    if month == 13:
        month = 1
        year += 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def add_business_days(dt, days: int):
    current = dt
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


# ✅ ZONAS ESTÁNDAR
ZONE_CHOICES = [
    ("SUR", "Sur"),
    ("NORTE", "Norte"),
    ("ORIENTE", "Oriente"),
    ("CENTRO", "Centro"),
]


# =========================
# ✅ MODALIDAD DE SERVICIO
# =========================
SERVICE_MODE_DELIVERY = "DELIVERY"
SERVICE_MODE_PICKUP = "PICKUP"
SERVICE_MODE_BOTH = "BOTH"

SERVICE_MODE_CHOICES = [
    (SERVICE_MODE_DELIVERY, "Solo domicilio"),
    (SERVICE_MODE_PICKUP, "Solo recoger en el punto"),
    (SERVICE_MODE_BOTH, "Domicilio y recoger en el punto"),
]


class Business(models.Model):
    class BusinessType(models.TextChoices):
        RESTAURANT = "RESTAURANT", "Restaurante"
        COMMERCE = "COMMERCE", "Comercio"

    class MenuMode(models.TextChoices):
        PDF = "PDF", "Menú PDF"
        CARDS = "CARDS", "Menú por productos"
        BOTH = "BOTH", "Ambos"

    class PlanType(models.TextChoices):
        FREE = "FREE", "Prueba 15 días"
        BASIC = "BASIC", "Plan Básico (PDF)"
        STANDARD = "STANDARD", "Plan Estándar (Productos)"
        PREMIUM = "PREMIUM", "Plan Premium (Destacado)"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
    )

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    business_type = models.CharField(
        max_length=20,
        choices=BusinessType.choices,
        default=BusinessType.RESTAURANT,
    )
    menu_mode = models.CharField(
        max_length=10,
        choices=MenuMode.choices,
        default=MenuMode.BOTH,
    )

    service_mode = models.CharField(
        max_length=20,
        choices=SERVICE_MODE_CHOICES,
        default=SERVICE_MODE_BOTH,
        verbose_name="Modalidad de entrega",
        help_text="Define si el negocio vende por domicilio, recogida en punto o ambas opciones.",
    )

    zone = models.CharField(
        max_length=20,
        choices=ZONE_CHOICES,
        blank=True,
        null=True,
    )

    address = models.CharField(max_length=160, blank=True)

    maps_url = models.URLField(
        blank=True,
        default="",
        help_text="Pega aquí el enlace de Google Maps (Compartir → Copiar enlace)",
    )

    map_embed_url = models.URLField(
        blank=True,
        default="",
        help_text="Opcional: enlace de insertar mapa",
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    instagram = models.CharField(max_length=80, blank=True)

    is_accepting_orders = models.BooleanField(default=True)
    show_closed_in_list = models.BooleanField(default=False)

    schedule_mon = models.CharField(max_length=20, blank=True, default="")
    schedule_tue = models.CharField(max_length=20, blank=True, default="")
    schedule_wed = models.CharField(max_length=20, blank=True, default="")
    schedule_thu = models.CharField(max_length=20, blank=True, default="")
    schedule_fri = models.CharField(max_length=20, blank=True, default="")
    schedule_sat = models.CharField(max_length=20, blank=True, default="")
    schedule_sun = models.CharField(max_length=20, blank=True, default="")

    description = models.TextField(blank=True)

    avg_prep_time = models.PositiveIntegerField(default=25)

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    nequi_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)

    tags = models.CharField(max_length=250, blank=True, default="")

    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    review_requested = models.BooleanField(default=False)
    review_requested_at = models.DateTimeField(blank=True, null=True)

    plan = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.FREE,
    )

    trial_ends_at = models.DateTimeField(blank=True, null=True)
    grace_ends_at = models.DateTimeField(blank=True, null=True)
    paid_until = models.DateTimeField(blank=True, null=True)

    plan_active = models.BooleanField(default=True)

    visits_count = models.PositiveIntegerField(default=0)
    whatsapp_clicks = models.PositiveIntegerField(default=0)
    last_visited_at = models.DateTimeField(blank=True, null=True)
    last_whatsapp_click_at = models.DateTimeField(blank=True, null=True)

    promo_active = models.BooleanField(default=False)
    promo_title = models.CharField(max_length=120, blank=True, default="")
    promo_text = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Negocio"
        verbose_name_plural = "Negocios"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:120] or "negocio"
            slug = base_slug
            i = 2
            while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix = f"-{i}"
                slug = f"{base_slug[:140 - len(suffix)]}{suffix}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_tags_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    def request_review(self):
        self.review_requested = True
        self.review_requested_at = timezone.now()
        self.save(update_fields=["review_requested", "review_requested_at"])

    def activate_free_trial(self):
        now = timezone.now()
        self.plan = self.PlanType.FREE
        self.plan_active = True
        self.trial_ends_at = add_business_days(now, 15)
        self.save(update_fields=["plan", "plan_active", "trial_ends_at"])

    def activate_paid_plan(self, plan_type=None, months=1):
        now = timezone.now()
        base_date = self.paid_until if self.paid_until and self.paid_until > now else now

        if plan_type:
            self.plan = plan_type

        self.plan_active = True
        new_paid_until = base_date
        for _ in range(months):
            new_paid_until = add_one_month(new_paid_until)

        self.paid_until = new_paid_until
        self.save(update_fields=["plan", "plan_active", "paid_until"])

    @property
    def has_active_trial(self):
        return bool(self.trial_ends_at and self.trial_ends_at >= timezone.now())

    @property
    def has_active_paid_plan(self):
        return bool(self.plan_active and self.paid_until and self.paid_until >= timezone.now())

    @property
    def has_active_plan(self):
        return self.has_active_trial or self.has_active_paid_plan

    def register_visit(self):
        self.visits_count = (self.visits_count or 0) + 1
        self.last_visited_at = timezone.now()
        self.save(update_fields=["visits_count", "last_visited_at"])

    def register_whatsapp_click(self):
        self.whatsapp_clicks = (self.whatsapp_clicks or 0) + 1
        self.last_whatsapp_click_at = timezone.now()
        self.save(update_fields=["whatsapp_clicks", "last_whatsapp_click_at"])

    def _parse_schedule_range(self, value: str):
        value = (value or "").strip()
        if not value or "-" not in value:
            return None, None

        start_str, end_str = value.split("-", 1)
        start_str = start_str.strip()
        end_str = end_str.strip()

        try:
            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()
            return start, end
        except ValueError:
            return None, None

    def _parse_range(self, value: str):
        return self._parse_schedule_range(value)

    def _get_schedule_for_weekday(self, weekday: int):
        mapping = {
            0: self.schedule_mon,
            1: self.schedule_tue,
            2: self.schedule_wed,
            3: self.schedule_thu,
            4: self.schedule_fri,
            5: self.schedule_sat,
            6: self.schedule_sun,
        }
        return mapping.get(weekday, "")

    @property
    def opening_hours(self):
        now = timezone.localtime()
        return self._get_schedule_for_weekday(now.weekday())

    @property
    def opening_time(self):
        schedule = self.opening_hours
        start, _ = self._parse_schedule_range(schedule)
        return start

    @property
    def closing_time(self):
        schedule = self.opening_hours
        _, end = self._parse_schedule_range(schedule)
        return end

    @property
    def is_open_now(self):
        if not self.is_active or not self.is_approved or not self.is_accepting_orders:
            return False

        now = timezone.localtime()
        schedule = self._get_schedule_for_weekday(now.weekday())
        start, end = self._parse_schedule_range(schedule)

        if not start or not end:
            return False

        current_time = now.time()

        if start <= end:
            return start <= current_time <= end

        return current_time >= start or current_time <= end

    @property
    def service_mode_label(self):
        return dict(SERVICE_MODE_CHOICES).get(self.service_mode, "")

    @property
    def allows_delivery(self):
        return self.service_mode in {SERVICE_MODE_DELIVERY, SERVICE_MODE_BOTH}

    @property
    def allows_pickup(self):
        return self.service_mode in {SERVICE_MODE_PICKUP, SERVICE_MODE_BOTH}