from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from businesses.models import Business
from menu.models import MenuCategory, MenuItem, MenuFile
from .forms import BusinessForm, MenuCategoryForm, MenuItemForm, MenuFileForm
from .forms_access import AccessRequestForm


def _get_user_business(user):
    # MVP: 1 usuario = 1 negocio
    return Business.objects.filter(owner=user).first()


@login_required
def dashboard(request):
    business = _get_user_business(request.user)
    return render(request, "dashboard/dashboard.html", {"business": business})


# ✅ NUEVA VISTA: Estadísticas
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


# ✅ NUEVA VISTA: Cambiar plan
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
        form = BusinessForm(request.POST, request.FILES, instance=business)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = BusinessForm(instance=business)

    return render(request, "dashboard/business_edit.html", {"form": form})


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

    # 🔒 Bloqueo para plan BASIC o modo PDF
    if business.plan == "BASIC" or business.menu_mode == "PDF":
        return HttpResponseForbidden("Tu plan actual solo permite menú PDF.")

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES)
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

    return render(request, "dashboard/item_form.html", {"form": form, "title": "Nuevo producto"})


@login_required
def item_edit(request, pk):
    business = _get_user_business(request.user)
    item = get_object_or_404(MenuItem, pk=pk)
    if not business or item.business_id != business.id:
        return HttpResponseForbidden("No autorizado")

    # 🔒 Bloqueo para plan BASIC o modo PDF
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

    return render(request, "dashboard/item_form.html", {"form": form, "title": "Editar producto"})


@login_required
def item_delete(request, pk):
    business = _get_user_business(request.user)
    item = get_object_or_404(MenuItem, pk=pk)
    if not business or item.business_id != business.id:
        return HttpResponseForbidden("No autorizado")

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