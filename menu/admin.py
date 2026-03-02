from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.urls import path

from .models import MenuFile, MenuCategory, MenuItem


@admin.register(MenuFile)
class MenuFileAdmin(admin.ModelAdmin):
    pass


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    pass


class MenuItemAdminForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        business = cleaned.get("business")
        category = cleaned.get("category")

        # Validación dura: la categoría debe ser del mismo negocio
        if business and category and category.business_id != business.id:
            raise ValidationError(
                {"category": "Esta categoría pertenece a otro negocio. Selecciona una categoría del mismo negocio."}
            )
        return cleaned


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    form = MenuItemAdminForm

    class Media:
        js = ("menu/admin_menuitem_dynamic_category.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "categories-by-business/",
                self.admin_site.admin_view(self.categories_by_business),
                name="menu_menuitem_categories_by_business",
            )
        ]
        return custom + urls

    def categories_by_business(self, request):
        """
        Devuelve categorías filtradas por business_id:
        /admin/menu/menuitem/categories-by-business/?business_id=1
        """
        business_id = request.GET.get("business_id")
        if not business_id:
            return JsonResponse({"results": []})

        qs = MenuCategory.objects.filter(business_id=business_id).order_by("order", "name")
        data = [{"id": c.id, "name": c.name} for c in qs]
        return JsonResponse({"results": data})