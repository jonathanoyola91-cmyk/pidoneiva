from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/negocio/editar/", views.business_edit, name="business_edit"),
    path("dashboard/enviar-revision/", views.request_review, name="request_review"),
    path("dashboard/planes/", views.change_plan, name="change_plan"),
    path("dashboard/estadisticas/", views.stats, name="stats"),
    path("stats/", views.stats, name="stats"),

    path("dashboard/categorias/", views.category_list, name="category_list"),
    path("dashboard/categorias/nueva/", views.category_create, name="category_create"),
    path("dashboard/categorias/<int:pk>/editar/", views.category_edit, name="category_edit"),
    path("dashboard/categorias/<int:pk>/eliminar/", views.category_delete, name="category_delete"),

    path("dashboard/productos/", views.item_list, name="item_list"),
    path("dashboard/productos/nuevo/", views.item_create, name="item_create"),
    path("dashboard/productos/<int:pk>/editar/", views.item_edit, name="item_edit"),
    path("dashboard/productos/<int:pk>/eliminar/", views.item_delete, name="item_delete"),

    path("dashboard/menus/", views.pdf_list, name="pdf_list"),
    path("dashboard/menus/subir/", views.pdf_upload, name="pdf_upload"),
    path("dashboard/menus/<int:pk>/eliminar/", views.pdf_delete, name="pdf_delete"),
    path("solicitar/", views.request_access, name="request_access"),
    
    ]