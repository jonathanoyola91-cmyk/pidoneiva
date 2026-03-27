from datetime import timedelta

from django.contrib import admin, messages
from django.utils import timezone

from .models import Business, BusinessGallery, BusinessRating


def add_one_month(dt):
    return dt + timedelta(days=30)


# =========================
# 📸 GALERÍA INLINE
# =========================
class BusinessGalleryInline(admin.TabularInline):
    model = BusinessGallery
    extra = 1
    fields = ("image", "title", "order", "is_active")
    ordering = ("order",)


# =========================
# ⭐ CALIFICACIONES INLINE
# =========================
class BusinessRatingInline(admin.TabularInline):
    model = BusinessRating
    extra = 0
    readonly_fields = ("user", "stars", "comment", "created_at")
    can_delete = True
    show_change_link = False


# =========================
# 🏪 BUSINESS ADMIN
# =========================
@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    def promo(self, obj):
        if hasattr(obj, "promo_active"):
            return bool(getattr(obj, "promo_active"))
        title = getattr(obj, "promo_title", "") or ""
        text = getattr(obj, "promo_text", "") or ""
        return bool(title.strip() or text.strip())

    promo.boolean = True
    promo.short_description = "Promo"

    def average_rating(self, obj):
        if hasattr(obj, "average_rating"):
            value = obj.average_rating
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = None
            return value
        return None

    average_rating.short_description = "Calificación"
    average_rating.admin_order_field = "average_rating"

    list_display = (
        "name",
        "business_type",
        "zone",
        "is_active",
        "is_approved",
        "plan",
        "average_rating",
        "visits_count",
    )

    list_filter = (
        "business_type",
        "zone",
        "is_active",
        "is_approved",
        "plan",
    )

    search_fields = ("name", "address", "phone", "whatsapp", "tags")
    prepopulated_fields = {"slug": ("name",)}

    readonly_fields = tuple(
        field
        for field in (
            "visits_count",
            "whatsapp_clicks",
            "last_visited_at",
            "last_whatsapp_click_at",
        )
        if hasattr(Business, field) or field in [f.name for f in Business._meta.get_fields()]
    )

    inlines = [
        BusinessGalleryInline,
        BusinessRatingInline,
    ]

    fieldsets = tuple(
        section for section in [
            ("Información básica", {
                "fields": tuple(
                    f for f in (
                        "owner",
                        "name",
                        "slug",
                        "business_type",
                        "menu_mode",
                        "service_mode",
                        "zone",
                        "address",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Ubicación", {
                "fields": tuple(
                    f for f in (
                        "maps_url",
                        "map_embed_url",
                        "latitude",
                        "longitude",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Contacto", {
                "fields": tuple(
                    f for f in (
                        "phone",
                        "whatsapp",
                        "instagram",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Horarios", {
                "fields": tuple(
                    f for f in (
                        "schedule_mon",
                        "schedule_tue",
                        "schedule_wed",
                        "schedule_thu",
                        "schedule_fri",
                        "schedule_sat",
                        "schedule_sun",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Operación", {
                "fields": tuple(
                    f for f in (
                        "is_accepting_orders",
                        "show_closed_in_list",
                        "delivery_fee",
                        "nequi_number",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Contenido", {
                "fields": tuple(
                    f for f in (
                        "description",
                        "logo",
                        "cover_image",
                        "tags",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Estado", {
                "fields": tuple(
                    f for f in (
                        "is_active",
                        "is_approved",
                        "review_requested",
                        "review_requested_at",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Plan", {
                "fields": tuple(
                    f for f in (
                        "plan",
                        "plan_active",
                        "trial_ends_at",
                        "grace_ends_at",
                        "paid_until",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Métricas", {
                "fields": tuple(
                    f for f in (
                        "visits_count",
                        "whatsapp_clicks",
                        "last_visited_at",
                        "last_whatsapp_click_at",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),

            ("Promoción", {
                "fields": tuple(
                    f for f in (
                        "promo_active",
                        "promo_title",
                        "promo_text",
                    )
                    if f in [x.name for x in Business._meta.get_fields()]
                )
            }),
        ]
        if section[1]["fields"]
    )

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
        update_data = {"is_approved": True}
        if "review_requested" in [f.name for f in Business._meta.get_fields()]:
            update_data["review_requested"] = False
        updated = queryset.update(**update_data)
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
            if hasattr(b, "grace_ends_at"):
                b.grace_ends_at = None
            base = b.paid_until if (getattr(b, "paid_until", None) and b.paid_until > now) else now
            b.paid_until = add_one_month(base)
            b.save()
        messages.success(request, "Plan Básico activado/renovado por 1 mes.")

    @admin.action(description="Cobro recibido: Activar Estándar (1 mes)")
    def pay_standard_1m(self, request, queryset):
        now = timezone.now()
        for b in queryset:
            b.plan = "STANDARD"
            b.plan_active = True
            if hasattr(b, "grace_ends_at"):
                b.grace_ends_at = None
            base = b.paid_until if (getattr(b, "paid_until", None) and b.paid_until > now) else now
            b.paid_until = add_one_month(base)
            b.save()
        messages.success(request, "Plan Estándar activado/renovado por 1 mes.")

    @admin.action(description="Cobro recibido: Activar Premium (1 mes)")
    def pay_premium_1m(self, request, queryset):
        now = timezone.now()
        for b in queryset:
            b.plan = "PREMIUM"
            b.plan_active = True
            if hasattr(b, "grace_ends_at"):
                b.grace_ends_at = None
            base = b.paid_until if (getattr(b, "paid_until", None) and b.paid_until > now) else now
            b.paid_until = add_one_month(base)
            b.save()
        messages.success(request, "Plan Premium activado/renovado por 1 mes.")

    # ==================================================
    # DEBUG temporal: verificar subida a Storage (R2/S3)
    # ==================================================
    def save_model(self, request, obj, form, change):
        print("ADMIN DEBUG FILES:", list(request.FILES.keys()))
        r = super().save_model(request, obj, form, change)

        if hasattr(obj, "cover_image") and obj.cover_image:
            try:
                exists = obj.cover_image.storage.exists(obj.cover_image.name)
            except Exception as e:
                print("ADMIN DEBUG exists() ERROR:", repr(e))
                exists = None
            print("ADMIN DEBUG cover name:", obj.cover_image.name)
            print("ADMIN DEBUG cover exists in storage?:", exists)

        if hasattr(obj, "logo") and obj.logo:
            try:
                exists = obj.logo.storage.exists(obj.logo.name)
            except Exception as e:
                print("ADMIN DEBUG logo exists() ERROR:", repr(e))
                exists = None
            print("ADMIN DEBUG logo name:", obj.logo.name)
            print("ADMIN DEBUG logo exists in storage?:", exists)

        return r


# =========================
# ⭐ ADMIN DE CALIFICACIONES
# =========================
@admin.register(BusinessRating)
class BusinessRatingAdmin(admin.ModelAdmin):
    list_display = ("business", "user", "stars", "created_at")
    list_filter = ("stars", "created_at")
    search_fields = ("business__name", "user__username", "comment")


# =========================
# 📸 ADMIN DE GALERÍA
# =========================
@admin.register(BusinessGallery)
class BusinessGalleryAdmin(admin.ModelAdmin):
    list_display = ("business", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("business__name",)