from django.db import models
from businesses.models import Business


class MenuFile(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="menu_files")
    file = models.FileField(upload_to="menus/pdfs/")
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PDF - {self.business.name}"


class MenuCategory(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="menu_categories")
    name = models.CharField(max_length=60)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.business.name} - {self.name}"


class MenuItem(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="menu_items")
    category = models.ForeignKey(
        MenuCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )

    name = models.CharField(max_length=80)
    description = models.CharField(max_length=220, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    photo = models.ImageField(upload_to="menus/items/", blank=True, null=True)
    is_available = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.business.name} - {self.name}"