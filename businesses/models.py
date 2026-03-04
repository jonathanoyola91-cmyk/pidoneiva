from datetime import time, timedelta
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
    """
    Suma 'days' días hábiles a partir de dt.
    lunes=0 ... domingo=6
    """
    current = dt
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # 0-4 son hábiles
            added += 1
    return current


# ✅ ZONAS ESTÁNDAR (lista fija)
ZONE_CHOICES = [
    ("SUR", "Sur"),
    ("NORTE", "Norte"),
    ("ORIENTE", "Oriente"),
    ("CENTRO", "Centro"),
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="businesses"
    )

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    business_type = models.CharField(
        max_length=20, choices=BusinessType.choices, default=BusinessType.RESTAURANT
    )
    menu_mode = models.CharField(
        max_length=10, choices=MenuMode.choices, default=MenuMode.BOTH
    )

    # ✅ ZONA con lista fija
    zone = models.CharField(
        max_length=20,
        choices=ZONE_CHOICES,
        blank=True,
        null=True,
    )

    address = models.CharField(max_length=160, blank=True)

    # Ubicación (Google Maps)
    maps_url = models.URLField(
        blank=True,
        default="",
        help_text="Pega aquí el enlace de Google Maps (Compartir → Copiar enlace)"
    )

    map_embed_url = models.URLField(
        blank=True,
        default="",
        help_text="Opcional: enlace de insertar mapa (Compartir → Insertar un mapa)"
    )

    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    instagram = models.CharField(max_length=80, blank=True)

    # Horario (MVP)
    is_accepting_orders = models.BooleanField(default=True)  # “Estoy recibiendo pedidos”
    show_closed_in_list = models.BooleanField(default=False)  # si True, aparecerá aunque esté cerrado (opcional)

    # Horarios por día (0=Lunes ... 6=Domingo)
    # Formato "HH:MM-HH:MM". Ej: "11:00-22:00"
    schedule_mon = models.CharField(max_length=20, blank=True, default="")
    schedule_tue = models.CharField(max_length=20, blank=True, default="")
    schedule_wed = models.CharField(max_length=20, blank=True, default="")
    schedule_thu = models.CharField(max_length=20, blank=True, default="")
    schedule_fri = models.CharField(max_length=20, blank=True, default="")
    schedule_sat = models.CharField(max_length=20, blank=True, default="")
    schedule_sun = models.CharField(max_length=20, blank=True, default="")

    description = models.TextField(blank=True)
    # ✅ NUEVO: tiempo promedio de preparación (en minutos)
    avg_prep_time = models.PositiveIntegerField(
        default=25,
        help_text="Tiempo promedio de preparación en minutos"
    )    

    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    cover_image = models.ImageField(
    upload_to="covers/",
    blank=True,
    null=True,
    help_text="Foto de portada para el directorio (recomendado 1200x600)."
) 

    tags = models.CharField( 
    "Etiquetas (tags)",
    max_length=250,
    blank=True,
    default="",
    help_text="Separa por coma. Ej: pizza, hamburguesa, café, droguería, mercado",
)
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

    # ✅ NUEVO: 5 días hábiles de gracia (después de vencer prueba o pago)
    grace_ends_at = models.DateTimeField(blank=True, null=True)

    # ✅ NUEVO: hasta cuándo está pagado (renovación mensual)
    paid_until = models.DateTimeField(blank=True, null=True)

    # switch manual por si quieres “pausar”
    plan_active = models.BooleanField(default=True)

    # ✅ NUEVO: métricas
    visits_count = models.PositiveIntegerField(default=0)
    whatsapp_clicks = models.PositiveIntegerField(default=0)
    last_visited_at = models.DateTimeField(blank=True, null=True)
    last_whatsapp_click_at = models.DateTimeField(blank=True, null=True)

    # ✅ NUEVO: PROMOCIÓN (solo UI; no afecta carrito/menú/lógica existente)
    promo_active = models.BooleanField(
        default=False,
        help_text="Activa/desactiva la promoción que se mostrará en el detalle del negocio."
    )
    promo_title = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Título corto de la promo. Ej: 2x1 en hamburguesas"
    )
    promo_text = models.TextField(
        blank=True,
        default="",
        help_text="Texto opcional de la promo. Ej: Válido hasta las 8pm"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_plan_valid(self):
        """
        Decide si el negocio se debe mostrar.
        Mantiene compatibilidad con tu uso actual: `if b.is_plan_valid` (sin paréntesis).
        """
        now = timezone.now()

        if not self.plan_active:
            return False

        # Si está pagado
        if self.paid_until and now <= self.paid_until:
            return True

        # Si está en prueba (FREE)
        if self.plan == self.PlanType.FREE and self.trial_ends_at and now <= self.trial_ends_at:
            return True

        # Si está en periodo de gracia (5 días hábiles)
        if self.grace_ends_at and now <= self.grace_ends_at:
            return True

        return False

    def start_grace_if_needed(self):
        """
        Inicia gracia de 5 días hábiles si ya venció prueba/pago y no hay gracia activa.
        """
        now = timezone.now()

        # Si ya está pagado o aún en prueba, no hacemos nada
        if (self.paid_until and now <= self.paid_until) or (
            self.plan == self.PlanType.FREE and self.trial_ends_at and now <= self.trial_ends_at
        ):
            return

        # Si no tiene gracia activa, iniciarla por 5 días hábiles
        if not self.grace_ends_at or now > self.grace_ends_at:
            self.grace_ends_at = add_business_days(now, 5)
            self.save(update_fields=["grace_ends_at"])

    def days_remaining(self):
        """
        Días restantes de la prueba FREE.
        Si no es FREE o no hay trial_ends_at, retorna 0.
        """
        if self.plan != self.PlanType.FREE or not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - timezone.now()
        return max(delta.days, 0)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 2
            while Business.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug

        # ✅ Asignar prueba automáticamente si no existe (mantiene tu lógica actual)
        if not self.trial_ends_at and self.plan == self.PlanType.FREE:
            self.trial_ends_at = timezone.now() + timedelta(days=15)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    # ---- Métodos de horario (debajo de __str__) ----
    def _get_schedule_for_weekday(self, weekday: int) -> str:
        # weekday: 0=Lunes ... 6=Domingo
        return [
            self.schedule_mon,
            self.schedule_tue,
            self.schedule_wed,
            self.schedule_thu,
            self.schedule_fri,
            self.schedule_sat,
            self.schedule_sun,
        ][weekday] or ""

    def _parse_range(self, s: str):
        """
        Recibe "HH:MM-HH:MM" y devuelve (start_time, end_time) como datetime.time.
        Si está vacío o inválido, retorna None.
        """
        s = (s or "").strip()
        if not s or "-" not in s:
            return None
        a, b = s.split("-", 1)
        a = a.strip()
        b = b.strip()
        try:
            sh, sm = [int(x) for x in a.split(":")]
            eh, em = [int(x) for x in b.split(":")]
            return time(sh, sm), time(eh, em)
        except Exception:
            return None

    @property
    def is_open_now(self) -> bool:
        """
        Abierto si:
        - is_accepting_orders True
        - y horario del día contiene rango válido
        - y ahora está dentro del rango
        Soporta rangos que cruzan medianoche (ej 18:00-02:00)
        """
        if not self.is_accepting_orders:
            return False

        now = timezone.localtime(timezone.now())
        weekday = now.weekday()  # 0..6
        schedule = self._get_schedule_for_weekday(weekday)
        parsed = self._parse_range(schedule)
        if not parsed:
            return False

        start, end = parsed
        current_t = now.time()

        # Rango normal (ej 11:00-22:00)
        if start < end:
            return start <= current_t <= end

        # Rango cruza medianoche (ej 18:00-02:00)
        return current_t >= start or current_t <= end

    def open_status_label(self) -> str:
        return "Abierto" if self.is_open_now else "Cerrado"