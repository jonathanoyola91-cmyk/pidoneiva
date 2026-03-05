from urllib.parse import quote
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.db.models import Q, Case, When, IntegerField, Value
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Business
from menu.models import MenuCategory, MenuFile, MenuItem


# =====================================================
# Helpers - Buyer (por negocio)
# =====================================================

def _buyer_key(slug: str) -> str:
    return f"buyer_{slug}"


def _get_buyer(request, slug: str) -> dict:
    return request.session.get(_buyer_key(slug), {}) or {}


def _save_buyer(request, slug: str, buyer: dict):
    request.session[_buyer_key(slug)] = buyer
    request.session.modified = True


# =====================================================
# Helpers - Cart (por negocio)
# =====================================================

def _cart_key(slug: str) -> str:
    return f"cart_{slug}"


def _get_cart(request, slug: str) -> dict:
    return request.session.get(_cart_key(slug), {}) or {}


def _save_cart(request, slug: str, cart: dict):
    request.session[_cart_key(slug)] = cart
    request.session.modified = True


def _clear_cart(request, slug: str):
    request.session.pop(_cart_key(slug), None)
    request.session.pop(_buyer_key(slug), None)

    if request.session.get("active_cart_business") == slug:
        request.session.pop("active_cart_business", None)

    request.session.modified = True


def _is_pdf_only(business: Business) -> bool:
    """
    BASIC o menu_mode=PDF => solo PDF + WhatsApp directo.
    """
    menu_mode = str(getattr(business, "menu_mode", "") or "").upper()
    plan = str(getattr(business, "plan", "") or "").upper()
    return (menu_mode == "PDF") or (plan == "BASIC")


def _is_open_now(business: Business, now=None) -> bool:
    """
    Si tu Business ya trae método is_open_now, se usa.
    Si no existe, no filtra (True) para no romper.
    """
    now = now or timezone.localtime()
    if hasattr(business, "is_open_now") and callable(getattr(business, "is_open_now")):
        try:
            return bool(business.is_open_now(now=now))
        except TypeError:
            return bool(business.is_open_now())
    return True

def _next_close_time(business, now):
    """
    Devuelve un datetime (timezone-aware) con la hora a la que CIERRA hoy
    si está abierto en este momento. Si no puede calcular, devuelve None.

    ⚠️ Debes adaptar la parte de "horarios" a cómo los tengas guardados.
    """
    # =========================
    # EJEMPLO 1 (recomendado): business.hours_json
    # hours_json tipo:
    # {
    #   "mon":[["08:00","22:00"]],
    #   "tue":[["08:00","22:00"]],
    #   ...
    # }
    # =========================
    hours = getattr(business, "hours_json", None)
    if not hours:
        return None

    key_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_key = key_map[now.weekday()]
    ranges = hours.get(day_key) or []

    def parse_hhmm(s):
        hh, mm = s.split(":")
        return time(int(hh), int(mm))

    # Busca el rango donde now cae adentro; si cruza medianoche también sirve
    for start_s, end_s in ranges:
        start_t = parse_hhmm(start_s)
        end_t = parse_hhmm(end_s)

        start_dt = now.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
        end_dt = now.replace(hour=end_t.hour, minute=end_t.minute, second=0, microsecond=0)

        # Si el cierre es "menor" que apertura, cruza medianoche
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)

        if start_dt <= now <= end_dt:
            return end_dt

    return None


def _open_status(business, now):
    """
    Retorna (is_open, closes_at_datetime_or_none)
    Usa schedule_mon..schedule_sun (formato "HH:MM-HH:MM")
    y soporta rangos que cruzan medianoche (ej 18:00-02:00).
    """
    if not getattr(business, "is_accepting_orders", True):
        return False, None

    def _dt_for(t, base_dt):
        return base_dt.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

    # 1) Caso: abierto por horario de AYER que cruza medianoche
    yday = now - timedelta(days=1)
    sch_y = business._get_schedule_for_weekday(yday.weekday())
    parsed_y = business._parse_range(sch_y)

    if parsed_y:
        start_y, end_y = parsed_y
        if start_y > end_y:  # cruza medianoche
            if now.time() <= end_y:
                closes_at = _dt_for(end_y, now)
                return True, closes_at

    # 2) Caso: horario de HOY
    sch = business._get_schedule_for_weekday(now.weekday())
    parsed = business._parse_range(sch)

    if not parsed:
        return False, None

    start, end = parsed

    # rango normal
    if start < end:
        if start <= now.time() <= end:
            closes_at = _dt_for(end, now)
            return True, closes_at
        return False, None

    # rango que cruza medianoche
    if now.time() >= start:
        closes_at = _dt_for(end, now) + timedelta(days=1)
        return True, closes_at

    return False, None

# =====================================================
# HOME
# =====================================================

def home(request):
    q = request.GET.get("q", "").strip()
    business_type = request.GET.get("type", "").strip()
    zone = request.GET.get("zone", "").strip()

    # ✅ default: mostrar TODOS
    # (solo filtra cuando open=1)
    only_open = "1" if request.GET.get("open") == "1" else "0"

    qs = Business.objects.filter(is_active=True, is_approved=True)

    if business_type in ["RESTAURANT", "COMMERCE"]:
        qs = qs.filter(business_type=business_type)

    # zone exacta (SUR/NORTE/ORIENTE/CENTRO)
    if zone:
        qs = qs.filter(zone=zone)

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(address__icontains=q) |
            Q(zone__icontains=q) |
            Q(tags__icontains=q) |
            Q(menu_categories__name__icontains=q) |
            Q(menu_categories__items__name__icontains=q) |
            Q(menu_categories__items__description__icontains=q)
        ).distinct()

    if hasattr(Business, "plan"):
        qs = qs.annotate(
            plan_rank=Case(
                When(plan="PREMIUM", then=Value(3)),
                When(plan="STANDARD", then=Value(2)),
                When(plan="BASIC", then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by("-plan_rank", "name")
    else:
        qs = qs.order_by("name")

    businesses = list(qs)

    now = timezone.localtime()

    # agregar estado calculado (mantengo tu lógica)
    for b in businesses:
        is_open, closes_at = _open_status(b, now)
        b.open_now = is_open
        b.closes_at_dt = closes_at

        # ✅ por compatibilidad: si alguna parte usa _is_open_now
        b._is_open_now = is_open
        b._closes_at = closes_at

    # ✅ filtro solo abiertos (mantengo tu lógica)
    if only_open == "1":
        businesses = [b for b in businesses if getattr(b, "open_now", False)]

    # zonas desde choices del modelo
    zones = Business._meta.get_field("zone").choices

    return render(request, "home.html", {
        "businesses": businesses,
        "q": q,
        "business_type": business_type,
        "zone": zone,
        "only_open": only_open,
        "zones": zones,
    })

# =====================================================
# BUSINESS DETAIL  (tu URL es /negocio/<slug>/)
# =====================================================

def business_detail(request, slug):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    active_slug = request.session.get("active_cart_business")
    cart_warning = bool(active_slug and active_slug != business.slug)

    pdf_only = _is_pdf_only(business)

    menu_files = MenuFile.objects.filter(business=business, is_active=True).order_by("-uploaded_at")

    categories = []
    items_by_category = {}
    cart_items = []
    cart_total = 0

    buyer = _get_buyer(request, business.slug)
    cart = _get_cart(request, business.slug)

    if not pdf_only:
        categories = MenuCategory.objects.filter(business=business).order_by("name")

        # ✅ MenuItem usa is_available, no is_active
        items = MenuItem.objects.filter(
            business=business,
            is_available=True
        ).select_related("category").order_by("category__name", "order", "name")

        for c in categories:
            items_by_category[c.id] = [it for it in items if it.category_id == c.id]

        # construir carrito
        if cart:
            item_ids = []
            for k in cart.keys():
                try:
                    item_ids.append(int(k))
                except ValueError:
                    pass

            # ✅ solo disponibles
            db_items = MenuItem.objects.filter(
                id__in=item_ids,
                business=business,
                is_available=True
            )
            db_map = {str(i.id): i for i in db_items}

            for item_id_str, qty in cart.items():
                it = db_map.get(str(item_id_str))
                if not it:
                    continue
                try:
                    qty = int(qty or 0)
                except ValueError:
                    qty = 0
                if qty <= 0:
                    continue

                subtotal = int(it.price) * qty
                cart_total += subtotal
                cart_items.append({
                    "id": it.id,
                    "name": it.name,
                    "price": int(it.price),
                    "qty": qty,
                    "subtotal": subtotal,
                })

    return render(request, "business_detail.html", {
        "business": business,
        "is_pdf_only": pdf_only,
        "menu_files": menu_files,
        "categories": categories,
        "items_by_category": items_by_category,
        "cart_warning": cart_warning,
        "cart_items": cart_items,
        "cart_total": cart_total,
        "buyer": buyer,
        "active_slug": active_slug,
    })


# =====================================================
# WhatsApp: por negocio (PDF o pedido completo)
# =====================================================

def whatsapp_redirect(request, slug):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    whatsapp = "".join(ch for ch in (getattr(business, "whatsapp", "") or "") if ch.isdigit())
    if not whatsapp:
        messages.error(request, "Este negocio aún no tiene WhatsApp configurado.")
        return redirect("business_detail", slug=business.slug)

    pdf_only = _is_pdf_only(business)
    buyer = _get_buyer(request, business.slug)

    lines = [f"Hola! Quiero contactar a *{business.name}*.", ""]

    if pdf_only:
        lines.append("📄 Vi que manejan *menú en PDF*.")
        lines.append("¿Me confirmas disponibilidad y cómo hago el pedido?")
    else:
        cart = _get_cart(request, business.slug)
        if not cart:
            lines.append("Aún no he agregado productos al carrito.")
        else:
            item_ids = []
            for k in cart.keys():
                try:
                    item_ids.append(int(k))
                except ValueError:
                    pass

            # ✅ solo disponibles
            items = MenuItem.objects.filter(
                id__in=item_ids,
                business=business,
                is_available=True
            )
            m = {str(i.id): i for i in items}

            total = 0
            lines.append("🧾 *Pedido:*")
            for item_id_str, qty in cart.items():
                it = m.get(str(item_id_str))
                if not it:
                    continue
                try:
                    qty = int(qty or 0)
                except ValueError:
                    qty = 0
                if qty <= 0:
                    continue
                subtotal = int(it.price) * qty
                total += subtotal
                lines.append(
                    f"- {qty} x {it.name} (${int(it.price):,}) = ${subtotal:,}".replace(",", ".")
                )

            lines.append("")
            lines.append(f"💰 *Total aprox:* ${total:,}".replace(",", "."))

    # buyer
    if any(buyer.get(k) for k in ["name", "phone", "address", "notes"]):
        lines.append("")
        lines.append("👤 *Datos del comprador:*")
        if buyer.get("name"):
            lines.append(f"Nombre: {buyer['name']}")
        if buyer.get("phone"):
            lines.append(f"Tel: {buyer['phone']}")
        if buyer.get("address"):
            lines.append(f"Dirección: {buyer['address']}")
        if buyer.get("notes"):
            lines.append(f"Notas: {buyer['notes']}")

    text = "\n".join(lines).strip()
    return redirect(f"https://wa.me/{whatsapp}?text={quote(text, safe='', encoding='utf-8')}")


# =====================================================
# WhatsApp: compatibilidad antigua por ITEM
# =====================================================

def whatsapp_item_redirect(request, item_id):
    # ✅ MenuItem usa is_available
    item = get_object_or_404(MenuItem, id=item_id, is_available=True)
    business = item.business

    whatsapp = "".join(ch for ch in (getattr(business, "whatsapp", "") or "") if ch.isdigit())
    if not whatsapp:
        messages.error(request, "Este negocio aún no tiene WhatsApp configurado.")
        return redirect("business_detail", slug=business.slug)

    text = (
        f"Hola! Quiero pedir 1 x *{item.name}* en *{business.name}*.\n"
        f"Precio: ${int(item.price):,}".replace(",", ".") + "\n"
        "¿Está disponible?"
    )
    return redirect(f"https://wa.me/{whatsapp}?text={quote(text)}")


# =====================================================
# CART ENDPOINTS (los que tu urls.py espera)
# =====================================================

@require_POST
def cart_add(request, slug, item_id):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    if _is_pdf_only(business):
        messages.warning(request, "Este negocio usa menú PDF. Contáctalo por WhatsApp.")
        return redirect("business_detail", slug=business.slug)

    # ✅ MenuItem usa is_available
    item = get_object_or_404(MenuItem, id=item_id, business=business, is_available=True)

    cart = _get_cart(request, business.slug)
    key = str(item.id)
    cart[key] = int(cart.get(key, 0)) + 1
    _save_cart(request, business.slug, cart)

    request.session["active_cart_business"] = business.slug
    request.session.modified = True

    return redirect(f"/negocio/{business.slug}/#cart")


@require_POST
def cart_update(request, slug, item_id):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    cart = _get_cart(request, business.slug)
    key = str(item_id)

    try:
        qty = int(request.POST.get("qty", "1"))
    except ValueError:
        qty = 1

    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = qty

    _save_cart(request, business.slug, cart)

    if cart:
        request.session["active_cart_business"] = business.slug
    else:
        if request.session.get("active_cart_business") == business.slug:
            request.session.pop("active_cart_business", None)
    request.session.modified = True

    return redirect(f"/negocio/{business.slug}/#cart")


@require_POST
def cart_remove(request, slug, item_id):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    cart = _get_cart(request, business.slug)
    cart.pop(str(item_id), None)
    _save_cart(request, business.slug, cart)

    if not cart and request.session.get("active_cart_business") == business.slug:
        request.session.pop("active_cart_business", None)
        request.session.modified = True

    return redirect(f"/negocio/{business.slug}/#cart")


@require_POST
def cart_clear(request, slug):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)
    _clear_cart(request, business.slug)
    return redirect(f"/negocio/{business.slug}/#cart")


from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Business

@require_POST
def cart_set_buyer(request, slug):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    buyer = {
        "name": (request.POST.get("name") or "").strip(),
        "phone": (request.POST.get("phone") or "").strip(),
        "address": (request.POST.get("address") or "").strip(),
        "notes": (request.POST.get("notes") or "").strip(),
    }
    _save_buyer(request, business.slug, buyer)

    # ✅ si le dio al botón "Enviar por WhatsApp", redirigir al flujo nuevo
    if request.POST.get("go_whatsapp") == "1":
        return redirect("send_whatsapp_order", slug=business.slug)

    # ✅ si solo guardó datos
    return redirect(f"/negocio/{business.slug}/#cart")


def cart_whatsapp(request, slug):
    """
    Tu url:
      cart/<slug>/whatsapp/
    Ahora redirige al sistema nuevo de pedidos (orders app).
    """
    return redirect("send_whatsapp_order", slug=slug)