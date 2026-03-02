# users/admin.py

from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

from businesses.models import Business
from .models import AccessRequest


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "request_type", "zone", "whatsapp", "is_processed", "created_at")
    list_filter = ("request_type", "is_processed", "zone")
    search_fields = ("name", "whatsapp", "email")
    actions = ["approve_and_create_access"]

    # A) readonly_fields y fields
    readonly_fields = ("whatsapp_message",)

    fields = (
        "name", "request_type", "zone", "address",
        "contact_name", "whatsapp", "email", "notes",
        "is_processed",
        "created_username", "temp_password", "created_business_slug",
        "whatsapp_message",
    )

    # B) método whatsapp_message
    def whatsapp_message(self, obj):
        if not obj.is_processed or not obj.created_username:
            return "Aún no se ha aprobado esta solicitud."

        login_url = "http://127.0.0.1:8001/accounts/login/"  # en local
        dashboard_url = "http://127.0.0.1:8001/dashboard/"

        msg = (
            f"✅ *PidoNeiva* - Acceso activado\n\n"
            f"🏪 Negocio: {obj.name}\n"
            f"👤 Usuario: {obj.created_username}\n"
        )

        if obj.temp_password:
            msg += f"🔑 Contraseña temporal: {obj.temp_password}\n"

        msg += (
            f"\n🔗 Ingreso: {login_url}\n"
            f"📌 Panel: {dashboard_url}\n\n"
            f"⚠️ Recomendación: cambia tu contraseña al ingresar."
        )
        return msg

    whatsapp_message.short_description = "Mensaje para WhatsApp"

    @admin.action(description="Aprobar y crear acceso (usuario + negocio)")
    def approve_and_create_access(self, request, queryset):
        """
        Mantiene tu lógica actual:
        - Si ya está procesada, se salta (no vuelve a resetear password).
        - Sigue guardando created_username/temp_password/created_business_slug.
        - Conserva el conteo de procesadas/saltadas.

        Pero incorpora lo que te pidieron:
        - Normaliza whatsapp seguro (ar.whatsapp o "")
        - Username puede venir de ar.created_username si existe
        - Usa get_or_create para User y Business
        - Siempre setea password (solo para las que se procesan en esta corrida)
        """
        created = 0
        skipped = 0

        for ar in queryset:
            if ar.is_processed:
                skipped += 1
                continue

            # Normalizar whatsapp a solo dígitos
            clean_whatsapp = "".join(ch for ch in (ar.whatsapp or "") if ch.isdigit())
            if not clean_whatsapp:
                messages.error(request, f"Solicitud '{ar.name}': WhatsApp inválido.")
                continue

            username = ar.created_username.strip() if ar.created_username else f"pn_{clean_whatsapp}"
            temp_password = get_random_string(10)

            # Crear o recuperar usuario
            user, created_user = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": ar.email or "",
                    "first_name": (ar.contact_name or "")[:150],
                },
            )

            # IMPORTANTÍSIMO: siempre setear password (así nunca falla el login)
            # (pero solo para solicitudes que se están aprobando ahora)
            user.set_password(temp_password)
            user.is_active = True
            user.save()

            # Crear o recuperar negocio
            business, created_business = Business.objects.get_or_create(
                owner=user,
                defaults={
                    "name": ar.name,
                    "business_type": ar.request_type,
                    "menu_mode": "BOTH",
                    "zone": ar.zone,
                    "address": ar.address,
                    "whatsapp": clean_whatsapp,
                    "is_approved": False,
                    "is_active": True,
                },
            )

            # Guardar datos en la solicitud
            ar.is_processed = True
            ar.created_username = username
            ar.temp_password = temp_password
            ar.created_business_slug = business.slug
            ar.save()

            created += 1

            messages.success(
                request,
                f"Acceso listo: {ar.name} | Usuario: {username} | Clave temporal: {temp_password}"
            )

        messages.info(request, f"Procesadas: {created}. Saltadas: {skipped}.")