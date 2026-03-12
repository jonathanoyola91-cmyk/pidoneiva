from urllib.parse import quote
import re

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse

from businesses.models import Business
from menu.models import MenuItem
from .models import Order, OrderItem, CustomerProfile


# =========================
# Helpers
# =========================
def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)


def _cart_key(slug: str) -> str:
    return f"cart_{slug}"


def _buyer_key(slug: str) -> str:
    return f"buyer_{slug}"


def get_or_create_customer(name: str, phone: str):
    clean_phone = normalize_phone(phone)

    if not clean_phone:
        return None

    customer, created = CustomerProfile.objects.get_or_create(
        phone=clean_phone,
        defaults={"name": (name or "").strip()},
    )

    if name and not customer.name:
        customer.name = name.strip()
        customer.save(update_fields=["name"])

    return customer


def get_available_payment_methods(customer):
    methods = [Order.PAYMENT_TRANSFER]

    if customer and customer.can_pay_cash():
        methods.append(Order.PAYMENT_CASH)

    return methods


# =========================
# Carrito en sesión
# =========================
def _get_cart(request, slug: str) -> dict:
    """
    Retorna el carrito desde sesión.
    Formato: {"12": 1, "15": 3}
    """
    return request.session.get(_cart_key(slug), {}) or {}


def _save_cart(request, slug: str, cart: dict) -> None:
    request.session[_cart_key(slug)] = cart
    request.session.modified = True


def _set_active_cart_business(request, business) -> None:
    request.session["active_cart_business"] = business.slug
    request.session["active_cart_business_slug"] = business.slug
    request.session["active_cart_business_name"] = business.name
    request.session.modified = True


def _clear_active_cart_business(request, slug: str | None = None) -> None:
    active_slug = request.session.get("active_cart_business_slug") or request.session.get("active_cart_business")

    if slug is None or active_slug == slug:
        request.session.pop("active_cart_business", None)
        request.session.pop("active_cart_business_slug", None)
        request.session.pop("active_cart_business_name", None)
        request.session.modified = True


def _get_active_cart_info(request) -> dict:
    return {
        "slug": request.session.get("active_cart_business_slug") or request.session.get("active_cart_business"),
        "name": request.session.get("active_cart_business_name", ""),
    }


# =========================
# Carrito
# =========================
@require_POST
def cart_update_json(request, slug, item_id):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    cart = _get_cart(request, business.slug)
    key = str(item_id)

    try:
        qty = int(request.POST.get("qty") or request.POST.get("next") or "1")
    except (TypeError, ValueError):
        qty = 1

    if qty <= 0:
        cart.pop(key, None)
        qty = 0
    else:
        cart[key] = qty

    _save_cart(request, business.slug, cart)

    if cart:
        _set_active_cart_business(request, business)
    else:
        _clear_active_cart_business(request, business.slug)

    item = MenuItem.objects.filter(id=item_id, business=business).first()
    item_price = int(item.price or 0) if item else 0
    item_subtotal = item_price * qty

    ids = [int(k) for k in cart.keys() if str(k).isdigit()]
    items = MenuItem.objects.filter(business=business, id__in=ids).values("id", "price")
    price_map = {str(x["id"]): int(x["price"] or 0) for x in items}

    total = 0
    cart_count = 0
    for k, q in cart.items():
        try:
            q = int(q)
        except Exception:
            q = 0
        cart_count += q
        total += price_map.get(str(k), 0) * q

    active_info = _get_active_cart_info(request)

    return JsonResponse({
        "ok": True,
        "item_id": item_id,
        "qty": qty,
        "item_subtotal": item_subtotal,
        "cart_total": total,
        "cart_count": cart_count,
        "is_empty": (len(cart) == 0),
        "active_cart_business_slug": active_info["slug"],
        "active_cart_business_name": active_info["name"],
    })


@require_GET
def go_to_active_cart(request):
    active_slug = request.session.get("active_cart_business_slug") or request.session.get("active_cart_business")

    if not active_slug:
        return redirect("/")

    return redirect(f"/negocio/{active_slug}/#cart")


@require_POST
def cart_clear_and_switch(request, slug):
    new_business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    active_slug = request.session.get("active_cart_business_slug") or request.session.get("active_cart_business")

    if active_slug:
        request.session.pop(f"cart_{active_slug}", None)
        request.session.pop(f"buyer_{active_slug}", None)

    _clear_active_cart_business(request)
    _set_active_cart_business(request, new_business)

    request.session.modified = True
    return redirect(f"/negocio/{new_business.slug}/")


# =========================
# Checkout / envío WhatsApp
# =========================
@require_GET
def send_whatsapp_order(request, slug):
    business = get_object_or_404(Business, slug=slug)

    cart = request.session.get(_cart_key(slug), {}) or {}
    buyer = request.session.get(_buyer_key(slug), {}) or {}

    if not cart:
        return redirect("business_detail", slug=slug)

    buyer_name = (buyer.get("name") or "").strip()
    buyer_phone = normalize_phone(buyer.get("phone", ""))
    buyer_address = (buyer.get("address") or "").strip()
    buyer_notes = (buyer.get("notes") or "").strip()
    payment_method = (buyer.get("payment_method") or Order.PAYMENT_TRANSFER).strip()

    customer = get_or_create_customer(buyer_name, buyer_phone)
    allowed_methods = get_available_payment_methods(customer)

    # Si es primer pedido, solo transferencia
    if payment_method not in allowed_methods:
        payment_method = Order.PAYMENT_TRANSFER

    order = Order.objects.create(
        business=business,
        customer=customer,
        buyer_name=buyer_name,
        buyer_phone=buyer_phone,
        buyer_address=buyer_address,
        buyer_notes=buyer_notes,
        payment_method=payment_method,
        total=0,
    )

    total = 0
    lines = []

    for item_id, qty in cart.items():
        try:
            qty = int(qty)
        except Exception:
            continue

        item = MenuItem.objects.filter(id=item_id, business=business).first()
        if not item:
            continue

        price = int(item.price or 0)
        subtotal = qty * price
        total += subtotal

        OrderItem.objects.create(
            order=order,
            name=item.name,
            qty=qty,
            price=price,
        )

        lines.append(
            f"• {qty} x {item.name} (${price:,}) = ${subtotal:,}".replace(",", ".")
        )

    order.total = total
    order.save(update_fields=["total"])

    # incrementar historial del cliente
    if customer:
        customer.successful_orders += 1
        if buyer_name and not customer.name:
            customer.name = buyer_name
            customer.save(update_fields=["successful_orders", "name"])
        else:
            customer.save(update_fields=["successful_orders"])

    total_str = f"${total:,}".replace(",", ".")

    if payment_method == Order.PAYMENT_CASH:
        payment_label = "Efectivo"
    else:
        payment_label = "Transferencia"

    client_status = "Cliente nuevo"
    if customer and customer.can_pay_cash():
        client_status = "Cliente con historial"

    msg = (
        f"*Pedido #{order.number}*\n"
        f"*{business.name}*\n\n"
        f"*Cliente:*\n"
        f"{order.buyer_name}\n"
        f"{order.buyer_phone}\n"
        f"{order.buyer_address}\n"
        f"{order.buyer_notes}\n\n"
        f"*Método de pago:* {payment_label}\n"
        f"*Estado del cliente:* {client_status}\n\n"
        f"*Detalle:*\n"
        + ("\n".join(lines) if lines else "- (sin items)")
        + f"\n\n*Total:* {total_str}"
    )

    request.session[_cart_key(slug)] = {}
    _clear_active_cart_business(request, slug)
    request.session.modified = True

    phone = getattr(business, "whatsapp", "") or getattr(business, "phone", "") or ""
    phone = "".join(c for c in str(phone) if c.isdigit())

    if not phone:
        return redirect("business_detail", slug=slug)

    url = f"https://wa.me/{phone}?text={quote(msg, safe='', encoding='utf-8')}"
    return redirect(url)