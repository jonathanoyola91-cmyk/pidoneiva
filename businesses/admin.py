from datetime import timedelta

from django.contrib import admin, messages
from django.utils import timezone

from .models import Business


def add_one_month(dt):
    return dt + timedelta(days=30)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    def promo(self, obj):
        # Si existe promo_active úsalo
        if hasattr(obj, "promo_active"):
            return bool(getattr(obj, "promo_active"))
        # Si NO existe, intenta inferir promo por título/texto (ajusta si quieres)
        title = getattr(obj, "promo_title", "") or ""
        text = getattr(obj, "promo_text", "") or ""
        return bool(title.strip() or text.strip())

    promo.boolean = True
    promo.short_description = "Promo"

    list_display = (
        "name",
        "business_type",
        "zone",
        "plan",
        "promo",          # ✅ no depende de que exista promo_active
        "visits_count",
        "is_approved",
        "is_active",
        "review_requested",
        "owner",
        "tags",
        "plan_active",
        "trial_ends_at",
        "paid_until",
        "whatsapp_clicks",
        "last_visited_at",
        "last_whatsapp_click_at",
    )

    list_filter = (
        "business_type",
        "zone",
        "plan",
        # ✅ solo filtra por promo_active si realmente existe como Field
        *(( "promo_active", ) if "promo_active" in [f.name for f in Business._meta.get_fields()] else ()),
        "is_approved",
        "is_active",
        "review_requested",
        "plan_active",
    )

    search_fields = ("name", "zone", "address", "tags")
    prepopulated_fields = {"slug": ("name",)}

    # ✅ fields: solo incluimos los campos que existan (evita reventar si faltan)
    base_fields = (
        "owner", "name", "slug",
        "business_type", "menu_mode",
        "zone", "address",
        "maps_url", "map_embed_url",
        "phone", "whatsapp", "instagram",
        "is_accepting_orders", "show_closed_in_list",
        "schedule_mon", "schedule_tue", "schedule_wed", "schedule_thu", "schedule_fri", "schedule_sat", "schedule_sun",
        "description",
        "tags",
        "logo",
        "cover_image",  # ✅ nuevo
        "promo_active", "promo_title", "promo_text",
        "plan", "trial_ends_at", "grace_ends_at", "paid_until", "plan_active",
        "is_approved", "is_active",
    )
    fields = tuple(f for f in base_fields if f in [x.name for x in Business._meta.get_fields()])

    actions = [
        "publish_businesses",
        "activate_basic",
        "activate_standard",
        "activate_premium",
        "pay_basic_1m",
        "pay_standard_1m",
        "pay_premium_1m",
    ]

    @admin.action(description="Publicar negocios seleccionados")
    def publish_businesses(self, request, queryset):
        updated = queryset.update(is_approved=True, review_requested=False)
        messages.success(request, f"{updated} negocio(s) publicados correctamente.")

    @admin.action(description="Activar Plan Básico")
    def activate_basic(self, request, queryset):
        updated = queryset.update(plan="BASIC", plan_active=True)
        messages.success(request, f"{updated} negocio(s) actualizados a Plan Básico.")

    @admin.action(description="Activar Plan Estándar")
    def activate_standard(self, request, queryset):
        updated = queryset.update(plan="STANDARD", plan_active=True)
        messages.success(request, f"{updated} negocio(s) actualizados a Plan Estándar.")

    @admin.action(description="Activar Plan Premium")
    def activate_premium(self, request, queryset):
        updated = queryset.update(plan="PREMIUM", plan_active=True)
        messages.success(request, f"{updated} negocio(s) actualizados a Plan Premium.")

    @admin.action(description="Cobro recibido: Activar Básico (1 mes)")
    def pay_basic_1m(self, request, queryset):
        now = timezone.now()
        for b in queryset:
            b.plan = "BASIC"
            b.plan_active = True
            b.grace_ends_at = None
            base = b.paid_until if (b.paid_until and b.paid_until > now) else now
            b.paid_until = add_one_month(base)
            b.save()
        messages.success(request, "Plan Básico activado/renovado por 1 mes.")

    @admin.action(description="Cobro recibido: Activar Estándar (1 mes)")
    def pay_standard_1m(self, request, queryset):
        now = timezone.now()
        for b in queryset:
            b.plan = "STANDARD"
            b.plan_active = True
            b.grace_ends_at = None
            base = b.paid_until if (b.paid_until and b.paid_until > now) else now
            b.paid_until = add_one_month(base)
            b.save()
        messages.success(request, "Plan Estándar activado/renovado por 1 mes.")

    @admin.action(description="Cobro recibido: Activar Premium (1 mes)")
    def pay_premium_1m(self, request, queryset):
        now = timezone.now()
        for b in queryset:
            b.plan = "PREMIUM"
            b.plan_active = True
            b.grace_ends_at = None
            base = b.paid_until if (b.paid_until and b.paid_until > now) else now
            b.paid_until = add_one_month(base)
            b.save()
        messages.success(request, "Plan Premium activado/renovado por 1 mes.")