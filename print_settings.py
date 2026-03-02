import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
print("SETTINGS=", os.environ.get("DJANGO_SETTINGS_MODULE"))
print("BASE_DIR=", settings.BASE_DIR)
print("STATIC_ROOT=", settings.STATIC_ROOT)