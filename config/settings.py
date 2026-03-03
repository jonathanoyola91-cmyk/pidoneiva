"""
Django settings for config project.
Production-ready for Render + Postgres + WhiteNoise + (optional) Cloudflare R2.
"""

import os
from pathlib import Path

import dj_database_url

# =========================
# Base directory
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent


# =========================
# SECURITY
# =========================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-fallback-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

# Allowed hosts (Render)
allowed_hosts_env = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
if allowed_hosts_env:
    # ejemplo: ".onrender.com,tu-dominio.com,www.tu-dominio.com"
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
else:
    # En producción NO uses "*". Pero lo dejamos para no bloquear si aún no configuras env vars.
    ALLOWED_HOSTS = ["*"] if DEBUG else [".onrender.com"]

# CSRF trusted origins (Render)
csrf_env = os.environ.get("CSRF_TRUSTED_ORIGINS", "").strip()
if csrf_env:
    # ejemplo: "https://*.onrender.com,https://tu-dominio.com,https://www.tu-dominio.com"
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_env.split(",") if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]


# =========================
# Applications
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "businesses",
    "menu",
    "users",

    # django-storages (R2 / S3 compatible)
    "storages",
]


# =========================
# Middleware
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # ✅ WhiteNoise para servir estáticos
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================
# URLs / WSGI
# =========================
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


# =========================
# Templates
# =========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# =========================
# Database
# =========================
# ✅ En Render usa DATABASE_URL (Postgres).
# ✅ En local, si no existe DATABASE_URL, usa sqlite.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {"timeout": 20},
        }
    }


# =========================
# Password validation
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =========================
# Internationalization
# =========================
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True


# =========================
# Static / Media
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ✅ En desarrollo/local puedes tener /static
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# WhiteNoise storage (static)
# (en Django 4.2/5 funciona perfecto)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media local (si no usas R2)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# =========================
# Auth redirects
# =========================
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"


# =========================
# Default auto field
# =========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================
# R2 (Cloudflare) / S3 compatible
# =========================
# ✅ Por defecto OFF en local para no romper tu Windows.
# ✅ En Render debes poner USE_R2=1 (Environment).
USE_R2 = os.environ.get("USE_R2", "0") == "1"

if USE_R2:
    AWS_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
    AWS_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
    AWS_STORAGE_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "").strip()
    AWS_S3_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "").strip()

    # ✅ Validación para evitar 500 al subir (si falta algo, falla al arrancar con mensaje claro)
    missing = []
    if not AWS_ACCESS_KEY_ID:
        missing.append("R2_ACCESS_KEY_ID")
    if not AWS_SECRET_ACCESS_KEY:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not AWS_STORAGE_BUCKET_NAME:
        missing.append("R2_BUCKET_NAME")
    if not AWS_S3_ENDPOINT_URL:
        missing.append("R2_ENDPOINT_URL")
    if missing:
        raise RuntimeError(f"USE_R2=1 pero faltan env vars: {', '.join(missing)}")

    # ✅ Detectar placeholders típicos
    if AWS_STORAGE_BUCKET_NAME in {"R2_BUCKET_NAME", "YOUR_BUCKET_NAME"}:
        raise RuntimeError("R2_BUCKET_NAME tiene placeholder. Pon el nombre REAL del bucket.")
    if "TU_ACCOUNT_ID" in AWS_S3_ENDPOINT_URL or "YOUR_ACCOUNT_ID" in AWS_S3_ENDPOINT_URL:
        raise RuntimeError("R2_ENDPOINT_URL tiene placeholder. Pon tu Account ID REAL en la URL.")

    AWS_S3_REGION_NAME = "auto"
    AWS_S3_SIGNATURE_VERSION = "s3v4"

    # ✅ CLAVE para Cloudflare R2 (evita 500 al subir archivos)
    AWS_S3_ADDRESSING_STYLE = "path"

    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

    # ✅ MEDIA a R2 (subida por S3)
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # ✅ Dominio público para SERVIR archivos (r2.dev o tu dominio)
    # Esto es lo que hace que {{ obj.logo.url }} use r2.dev en vez de r2.cloudflarestorage.com
    PUBLIC_BASE = os.environ.get("R2_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not PUBLIC_BASE:
        raise RuntimeError(
            "USE_R2=1 pero falta R2_PUBLIC_BASE_URL (usa el Public Development URL r2.dev o tu dominio)."
        )

    AWS_S3_CUSTOM_DOMAIN = PUBLIC_BASE.replace("https://", "").replace("http://", "")
    AWS_S3_URL_PROTOCOL = "https:"

    # MEDIA_URL (para templates y consistencia)
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"


# =========================
# Basic security when behind proxy (Render)
# =========================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "1") == "1" and not DEBUG


# =========================
# Logging (mostrar errores reales en Render runtime logs)
# =========================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}