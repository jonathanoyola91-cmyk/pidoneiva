from urllib.parse import quote

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET

from businesses.models import Business
from menu.models import MenuItem
from .models import Order, OrderItem


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