from urllib.parse import quote

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse

from businesses.models import Business
from menu.models import MenuItem
from .models import Order, OrderItem


# =========================
# Carrito en sesión (FIX)
# =========================
def _cart_key(slug: str) -> str:
    # ✅ importante: coincide con el resto de tu código (send_whatsapp_order)
    return f"cart_{slug}"


def _get_cart(request, slug: str) -> dict:
    """
    Retorna el carrito desde sesión.
    Formato: {"12": 1, "15": 3}
    """
    return request.session.get(_cart_key(slug), {}) or {}


def _save_cart(request, slug: str, cart: dict) -> None:
    request.session[_cart_key(slug)] = cart
    request.session.modified = True


@require_POST
def cart_update_json(request, slug, item_id):
    business = get_object_or_404(Business, slug=slug, is_active=True, is_approved=True)

    cart = _get_cart(request, business.slug)  # esperado: {"12": 1, "15": 3}
    key = str(item_id)

    # ✅ acepta qty (FormData) y también next (por si tus botones envían next)
    try:
        qty = int(request.POST.get("qty") or request.POST.get("next") or "1")
    except (TypeError, ValueError):
        qty = 1

    if qty <= 0:
        cart.pop(key, None)
        qty = 0
    else:
        # ✅ tu estructura: id -> int
        cart[key] = qty

    _save_cart(request, business.slug, cart)

    # ✅ calcular subtotal y total usando DB (más confiable)
    item = MenuItem.objects.filter(id=item_id, business=business).first()
    item_price = int(item.price or 0) if item else 0
    item_subtotal = item_price * qty

    # total del carrito
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

    return JsonResponse({
        "ok": True,
        "item_id": item_id,
        "qty": qty,
        "item_subtotal": item_subtotal,
        "cart_total": total,
        "cart_count": cart_count,
        "is_empty": (len(cart) == 0),
    })


@require_GET
def send_whatsapp_order(request, slug):
    business = get_object_or_404(Business, slug=slug)

    cart = request.session.get(f"cart_{slug}", {}) or {}
    buyer = request.session.get(f"buyer_{slug}", {}) or {}

    if not cart:
        return redirect("business_detail", slug=slug)

    # 1) crear Order
    order = Order.objects.create(
        business=business,
        buyer_name=buyer.get("name", ""),
        buyer_phone=buyer.get("phone", ""),
        buyer_address=buyer.get("address", ""),
        buyer_notes=buyer.get("notes", ""),
        total=0,
    )

    total = 0
    lines = []

    # 2) crear OrderItems
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

        # agregar item al mensaje (con puntos)
        lines.append(
            f"• {qty} x {item.name} (${price:,}) = ${subtotal:,}".replace(",", ".")
        )

    # 3) guardar total FINAL una sola vez
    order.total = total
    order.save(update_fields=["total"])

    # 4) construir mensaje FINAL una sola vez
    total_str = f"${total:,}".replace(",", ".")

    msg = (
        f"*Pedido #{order.number}*\n"
        f"*{business.name}*\n\n"
        f"*Cliente:*\n"
        f"{order.buyer_name}\n"
        f"{order.buyer_phone}\n"
        f"{order.buyer_address}\n"
        f"{order.buyer_notes}\n\n"
        f"*Detalle:*\n"
        + ("\n".join(lines) if lines else "- (sin items)")
        + f"\n\n*Total:* {total_str}"
    )

    # limpiar carrito (recomendado)
    request.session[f"cart_{slug}"] = {}
    request.session.modified = True

    # WhatsApp del negocio
    phone = getattr(business, "whatsapp", "") or getattr(business, "phone", "") or ""
    phone = "".join(c for c in str(phone) if c.isdigit())

    if not phone:
        return redirect("business_detail", slug=slug)

    url = f"https://wa.me/{phone}?text={quote(msg, safe='', encoding='utf-8')}"
    return redirect(url)