"""
Django settings for config project.
Production-ready for Render + Postgres + WhiteNoise + (optional) Cloudflare R2.
"""

import os
from pathlib import Path
import dj_database_url
import mimetypes

mimetypes.add_type("image/webp", ".webp", strict=True)

# =========================
# Base directory
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent


# =========================
# SECURITY
# =========================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-fallback-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

# =========================
# Allowed Hosts
# =========================
allowed_hosts_env = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()

if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
else:
    # En producción NO usar "*"
    ALLOWED_HOSTS = ["*"] if DEBUG else [
        ".onrender.com",
        "pidoneiva.com",
        "www.pidoneiva.com",
    ]


# =========================
# CSRF Trusted Origins
# =========================
csrf_env = os.environ.get("CSRF_TRUSTED_ORIGINS", "").strip()

if csrf_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_env.split(",") if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        "https://*.onrender.com",
        "https://pidoneiva.com",
        "https://www.pidoneiva.com",
    ]


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
    "orders.apps.OrdersConfig",

    "storages",  # R2 / S3
]


# =========================
# Middleware
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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
# R2 (Cloudflare)
# =========================
USE_R2 = os.environ.get("USE_R2", "0") == "1"

if USE_R2:

    AWS_ACCESS_KEY_ID = (os.environ.get("R2_ACCESS_KEY_ID") or "").strip()
    AWS_SECRET_ACCESS_KEY = (os.environ.get("R2_SECRET_ACCESS_KEY") or "").strip()
    AWS_STORAGE_BUCKET_NAME = (os.environ.get("R2_BUCKET_NAME") or "").strip()
    AWS_S3_ENDPOINT_URL = (os.environ.get("R2_ENDPOINT_URL") or "").strip()

    AWS_S3_REGION_NAME = "auto"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_ADDRESSING_STYLE = "path"

    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "public, max-age=31536000",
    }

    PUBLIC_BASE = (os.environ.get("R2_PUBLIC_BASE_URL") or "").strip().rstrip("/")

    if PUBLIC_BASE:
        AWS_S3_CUSTOM_DOMAIN = PUBLIC_BASE.replace("https://", "").replace("http://", "")
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
    else:
        MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# límites de subida recomendados
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
# =========================
# Security Behind Proxy (Render)
# =========================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

SECURE_SSL_REDIRECT = (
    os.environ.get("SECURE_SSL_REDIRECT", "1") == "1"
    and not DEBUG
)


# =========================
# Logging
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