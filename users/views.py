from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from businesses.models import Business
from menu.models import MenuCategory, MenuItem, MenuFile
from orders.models import Order
from orders.utils import normalize_phone

from .forms import BusinessForm, MenuCategoryForm, MenuItemForm, MenuFileForm
from .forms_access import AccessRequestForm
from .models import AppCustomer


def _get_user_business(user):
    # MVP: 1 usuario = 1 negocio
    return Business.objects.filter(owner=user).first()


def _is_customer_session(request):
    return bool(request.session.get("customer_auth") is True)


def _customer_login(request, user):
    login(request, user)
    request.session["customer_auth"] = True
    request.session.modified = True


def _customer_logout(request):
    request.session.pop("customer_auth", None)
    request.session.modified = True
    logout(request)


@login_required
def dashboard(request):
    business = _get_user_business(request.user)
    return render(request, "dashboard/dashboard.html", {"business": business})


@login_required
def stats(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")

    visits = business.visits_count or 0
    clicks = business.whatsapp_clicks or 0
    conversion = (clicks / visits * 100) if visits > 0 else 0.0

    return render(
        request,
        "dashboard/stats.html",
        {
            "business": business,
            "visits": visits,
            "clicks": clicks,
            "conversion": conversion,
        },
    )


@login_required
def change_plan(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")

    return render(request, "dashboard/change_plan.html", {"business": business})


@login_required
def request_review(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")

    if request.method == "POST":
        business.review_requested = True
        business.review_requested_at = timezone.now()
        business.save()
        return redirect("dashboard")

    return render(request, "dashboard/request_review_confirm.html", {"business": business})


@login_required
def business_edit(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado. Contacta al admin.")

    if request.method == "POST":
        print("DEBUG POST keys:", list(request.POST.keys()))
        print("DEBUG FILES keys:", list(request.FILES.keys()))
        print("DEBUG logo in FILES?:", "logo" in request.FILES)
        print("DEBUG cover_image in FILES?:", "cover_image" in request.FILES)

        form = BusinessForm(request.POST, request.FILES, instance=business)

        ok = form.is_valid()
        print("DEBUG is_valid:", ok)
        print("DEBUG errors:", form.errors)

        if ok:
            obj = form.save()
            print("DEBUG saved logo:", obj.logo.name if obj.logo else None)
            print("DEBUG saved cover:", obj.cover_image.name if obj.cover_image else None)
            print("DEBUG saved latitude:", obj.latitude)
            print("DEBUG saved longitude:", obj.longitude)
            messages.success(request, "Negocio actualizado correctamente.")
            return redirect("dashboard")
    else:
        form = BusinessForm(instance=business)

    return render(request, "dashboard/business_edit.html", {"form": form, "business": business})


@login_required
def category_list(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")
    cats = MenuCategory.objects.filter(business=business).order_by("order", "name")
    return render(request, "dashboard/category_list.html", {"cats": cats})


@login_required
def category_create(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")

    if request.method == "POST":
        form = MenuCategoryForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.business = business
            obj.save()
            return redirect("category_list")
    else:
        form = MenuCategoryForm()

    return render(request, "dashboard/category_form.html", {"form": form, "title": "Nueva categoría"})


@login_required
def category_edit(request, pk):
    business = _get_user_business(request.user)
    cat = get_object_or_404(MenuCategory, pk=pk)
    if not business or cat.business_id != business.id:
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        form = MenuCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            return redirect("category_list")
    else:
        form = MenuCategoryForm(instance=cat)

    return render(request, "dashboard/category_form.html", {"form": form, "title": "Editar categoría"})


@login_required
def category_delete(request, pk):
    business = _get_user_business(request.user)
    cat = get_object_or_404(MenuCategory, pk=pk)
    if not business or cat.business_id != business.id:
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        cat.delete()
        return redirect("category_list")

    return render(request, "dashboard/confirm_delete.html", {"obj": cat})


@login_required
def item_list(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")
    items = MenuItem.objects.filter(business=business).select_related("category").order_by("order", "name")
    return render(request, "dashboard/item_list.html", {"items": items})


@login_required
def item_create(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")

    if business.plan == "BASIC" or business.menu_mode == "PDF":
        return HttpResponseForbidden("Tu plan actual solo permite menú PDF.")

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES)
        form.fields["category"].queryset = MenuCategory.objects.filter(business=business)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.business = business

            if obj.category and obj.category.business_id != business.id:
                return HttpResponseForbidden("Categoría inválida.")

            obj.save()
            return redirect("item_list")
    else:
        form = MenuItemForm()
        form.fields["category"].queryset = MenuCategory.objects.filter(business=business)

    return render(
        request,
        "dashboard/item_form.html",
        {"form": form, "title": "Nuevo producto"},
    )


@login_required
def item_edit(request, pk):
    business = _get_user_business(request.user)
    item = get_object_or_404(MenuItem, pk=pk)

    if not business or item.business_id != business.id:
        return HttpResponseForbidden("No autorizado")

    if business.plan == "BASIC" or business.menu_mode == "PDF":
        return HttpResponseForbidden("Tu plan actual solo permite menú PDF.")

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        form.fields["category"].queryset = MenuCategory.objects.filter(business=business)

        if form.is_valid():
            obj = form.save(commit=False)

            if obj.category and obj.category.business_id != business.id:
                return HttpResponseForbidden("Categoría inválida.")

            obj.save()
            return redirect("item_list")
    else:
        form = MenuItemForm(instance=item)
        form.fields["category"].queryset = MenuCategory.objects.filter(business=business)

    return render(
        request,
        "dashboard/item_form.html",
        {"form": form, "title": "Editar producto"},
    )


@login_required
def item_delete(request, pk):
    business = _get_user_business(request.user)
    item = get_object_or_404(MenuItem, pk=pk)
    if not business or item.business_id != business.id:
        return HttpResponseForbidden("No autorizado")

    if business.plan == "BASIC" or business.menu_mode == "PDF":
        return HttpResponseForbidden("Tu plan actual solo permite menú PDF.")

    if request.method == "POST":
        item.delete()
        return redirect("item_list")

    return render(request, "dashboard/confirm_delete.html", {"obj": item})


@login_required
def pdf_list(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")
    pdfs = MenuFile.objects.filter(business=business).order_by("-uploaded_at")
    return render(request, "dashboard/pdf_list.html", {"pdfs": pdfs})


@login_required
def pdf_upload(request):
    business = _get_user_business(request.user)
    if not business:
        return HttpResponseForbidden("No tienes un negocio asignado.")

    if request.method == "POST":
        form = MenuFileForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.business = business
            obj.save()
            return redirect("pdf_list")
    else:
        form = MenuFileForm()

    return render(request, "dashboard/pdf_form.html", {"form": form, "title": "Subir menú PDF"})


@login_required
def pdf_delete(request, pk):
    business = _get_user_business(request.user)
    pdf = get_object_or_404(MenuFile, pk=pk)
    if not business or pdf.business_id != business.id:
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        pdf.delete()
        return redirect("pdf_list")

    return render(request, "dashboard/confirm_delete.html", {"obj": pdf})


def request_access(request):
    if request.method == "POST":
        form = AccessRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, "request_access_done.html")
    else:
        form = AccessRequestForm()

    return render(request, "request_access.html", {"form": form})


@require_http_methods(["GET", "POST"])
def customer_register(request):
    if request.user.is_authenticated and _is_customer_session(request) and hasattr(request.user, "app_customer"):
        return redirect("customer_my_orders")

    next_url = request.GET.get("next") or request.POST.get("next") or "/"

    if request.method == "POST":
        full_name = (request.POST.get("full_name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        phone = normalize_phone(request.POST.get("phone"))
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        if not full_name or not email or not phone or not password or not confirm_password:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, "users/register.html", {"next": next_url})

        if len(password) < 6:
            messages.error(request, "La contraseña debe tener al menos 6 caracteres.")
            return render(request, "users/register.html", {"next": next_url})

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, "users/register.html", {"next": next_url})

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Ya existe una cuenta con ese correo.")
            return render(request, "users/register.html", {"next": next_url})

        if AppCustomer.objects.filter(phone=phone).exists():
            messages.error(request, "Ya existe una cuenta con ese teléfono.")
            return render(request, "users/register.html", {"next": next_url})

        username_base = email.split("@")[0]
        username = username_base
        suffix = 1

        while User.objects.filter(username=username).exists():
            username = f"{username_base}{suffix}"
            suffix += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name,
        )

        AppCustomer.objects.create(
            user=user,
            phone=phone,
            full_name=full_name,
        )

        auth_user = authenticate(request, username=username, password=password)
        if auth_user:
            _customer_login(request, auth_user)

        messages.success(request, "Tu cuenta fue creada correctamente.")
        return redirect(next_url)

    return render(request, "users/register.html", {"next": next_url})


@require_http_methods(["GET", "POST"])
def customer_login(request):
    if request.user.is_authenticated and _is_customer_session(request) and hasattr(request.user, "app_customer"):
        return redirect("customer_my_orders")

    next_url = request.GET.get("next") or request.POST.get("next") or "/"

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        if not email or not password:
            messages.error(request, "Debes ingresar correo y contraseña.")
            return render(request, "users/login.html", {"next": next_url})

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            messages.error(request, "Credenciales inválidas.")
            return render(request, "users/login.html", {"next": next_url})

        auth_user = authenticate(request, username=user.username, password=password)
        if not auth_user:
            messages.error(request, "Credenciales inválidas.")
            return render(request, "users/login.html", {"next": next_url})

        if not hasattr(auth_user, "app_customer"):
            messages.error(request, "Esta cuenta no está habilitada como cliente.")
            return render(request, "users/login.html", {"next": next_url})

        _customer_login(request, auth_user)
        messages.success(request, "Has iniciado sesión correctamente.")
        return redirect(next_url)

    return render(request, "users/login.html", {"next": next_url})


def customer_logout(request):
    _customer_logout(request)
    messages.success(request, "Has cerrado sesión.")
    return redirect("/")


@login_required
def customer_my_orders(request):
    if not _is_customer_session(request) or not hasattr(request.user, "app_customer"):
        messages.error(request, "Debes iniciar sesión como cliente para ver tus pedidos.")
        return redirect(f"/clientes/ingresar/?next={request.path}")

    app_customer = request.user.app_customer

    orders = (
        Order.objects
        .filter(app_customer=app_customer)
        .select_related("business")
        .prefetch_related("items")
        .order_by("-created_at")
    )

    return render(
        request,
        "users/my_orders.html",
        {
            "orders": orders,
            "app_customer": app_customer,
        },
    )