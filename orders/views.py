from urllib.parse import quote
from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from businesses.models import Business
from menu.models import MenuItem
from users.models import AppCustomer
from .models import Order, OrderItem, CustomerProfile
from .utils import normalize_phone


# =========================
# Helpers
# =========================
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


def get_logged_app_customer(request):
    if (
        request.user.is_authenticated
        and request.session.get("customer_auth")
        and hasattr(request.user, "app_customer")
    ):
        return request.user.app_customer
    return None


def get_effective_delivery_type(business, buyer):
    """
    Determina el tipo de entrega real según:
    - la modalidad del negocio
    - lo guardado en sesión del comprador
    """
    service_mode = str(getattr(business, "service_mode", "") or "").upper()
    buyer = buyer or {}

    # Si el negocio solo permite recoger, forzar pickup
    if service_mode == "PICKUP":
        return "pickup"

    # Si el negocio solo permite domicilio, forzar delivery
    if service_mode == "DELIVERY":
        return "delivery"

    # Si permite ambos, usar lo guardado por el comprador
    delivery_type = (buyer.get("delivery_type") or "delivery").strip().lower()
    if delivery_type not in ["delivery", "pickup"]:
        delivery_type = "delivery"

    return delivery_type


def get_delivery_fee_amount(business, buyer):
    """
    Devuelve el costo de domicilio real según el tipo de entrega.
    """
    delivery_type = get_effective_delivery_type(business, buyer)

    if delivery_type != "delivery":
        return 0

    return int(Decimal(str(getattr(business, "delivery_fee", 0) or 0)))


# =========================
# API - métodos de pago
# =========================
@api_view(["POST"])
def payment_options(request):
    phone = normalize_phone(request.data.get("phone"))
    business_slug = request.data.get("business_slug")

    if not phone or not business_slug:
        return Response(
            {"ok": False, "error": "phone and business_slug are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        Business.objects.get(
            slug=business_slug,
            is_active=True,
            is_approved=True
        )
    except Business.DoesNotExist:
        return Response(
            {"ok": False, "error": "business not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    profile, created = CustomerProfile.objects.get_or_create(phone=phone)

    is_first_order = profile.successful_orders == 0
    can_pay_cash = profile.can_pay_cash()

    allowed_methods = [Order.PAYMENT_TRANSFER]

    if can_pay_cash:
        allowed_methods.append(Order.PAYMENT_CASH)

    return Response({
        "ok": True,
        "is_first_order": is_first_order,
        "can_pay_cash": can_pay_cash,
        "allowed_payment_methods": allowed_methods
    })


# =========================
# Carrito en sesión
# =========================
def _get_cart(request, slug: str) -> dict:
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

    subtotal = 0
    cart_count = 0
    for k, q in cart.items():
        try:
            q = int(q)
        except Exception:
            q = 0
        cart_count += q
        subtotal += price_map.get(str(k), 0) * q

    buyer = request.session.get(_buyer_key(business.slug), {}) or {}
    delivery_type = get_effective_delivery_type(business, buyer)
    delivery_fee = get_delivery_fee_amount(business, buyer)
    total = subtotal + delivery_fee

    active_info = _get_active_cart_info(request)

    return JsonResponse({
        "ok": True,
        "item_id": item_id,
        "qty": qty,
        "item_subtotal": item_subtotal,
        "cart_subtotal": subtotal,
        "delivery_type": delivery_type,
        "delivery_fee": delivery_fee,
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
    delivery_type = get_effective_delivery_type(business, buyer)

    customer = get_or_create_customer(buyer_name, buyer_phone)
    allowed_methods = get_available_payment_methods(customer)

    if payment_method not in allowed_methods:
        payment_method = Order.PAYMENT_TRANSFER

    app_customer = get_logged_app_customer(request)

    order = Order.objects.create(
        business=business,
        customer=customer,
        app_customer=app_customer,
        buyer_name=buyer_name,
        buyer_phone=buyer_phone,
        buyer_address=buyer_address,
        buyer_notes=buyer_notes,
        payment_method=payment_method,
        delivery_type=delivery_type,
        total=0,
    )

    subtotal = 0
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
        line_subtotal = qty * price
        subtotal += line_subtotal

        OrderItem.objects.create(
            order=order,
            name=item.name,
            qty=qty,
            price=price,
        )

        lines.append(
            f"• {qty} x {item.name} (${price:,}) = ${line_subtotal:,}".replace(",", ".")
        )

    delivery_fee = get_delivery_fee_amount(business, buyer)
    total = subtotal + delivery_fee

    order.total = total
    order.save(update_fields=["total"])

    if customer:
        customer.successful_orders += 1
        if buyer_name and not customer.name:
            customer.name = buyer_name
            customer.save(update_fields=["successful_orders", "name"])
        else:
            customer.save(update_fields=["successful_orders"])

    if app_customer:
        changed = False

        if buyer_name and app_customer.full_name != buyer_name:
            app_customer.full_name = buyer_name
            changed = True

        if buyer_phone and app_customer.phone != buyer_phone:
            existing = AppCustomer.objects.filter(phone=buyer_phone).exclude(pk=app_customer.pk).exists()
            if not existing:
                app_customer.phone = buyer_phone
                changed = True

        if buyer_address and not app_customer.default_address:
            app_customer.default_address = buyer_address
            changed = True

        if changed:
            app_customer.save()

    subtotal_str = f"${subtotal:,}".replace(",", ".")
    delivery_fee_str = f"${delivery_fee:,}".replace(",", ".")
    total_str = f"${total:,}".replace(",", ".")

    if payment_method == Order.PAYMENT_CASH:
        payment_label = "Efectivo"
    else:
        payment_label = "Transferencia"

    if delivery_type == "pickup":
        delivery_label = "Recoger en el punto"
    else:
        delivery_label = "Domicilio"

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
        f"*Método de entrega:* {delivery_label}\n"
        f"*Método de pago:* {payment_label}\n"
        f"*Estado del cliente:* {client_status}\n\n"
        f"*Detalle:*\n"
        + ("\n".join(lines) if lines else "- (sin items)")
        + f"\n\n*Subtotal productos:* {subtotal_str}"
        + (f"\n*Domicilio:* {delivery_fee_str}" if delivery_fee > 0 else "\n*Domicilio:* $0")
        + f"\n*Total:* {total_str}"
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