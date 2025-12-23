import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

primary_domain = os.getenv("DJANGO_PRIMARY_DOMAIN", "esgrequesthub.dreadops.site").strip()
if primary_domain and primary_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(primary_domain)

website_hostname = os.getenv("WEBSITE_HOSTNAME")
if website_hostname and website_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(website_hostname)

csrf_hosts = [host.strip() for host in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if host.strip()]
if website_hostname:
    csrf_hosts.append(f"https://{website_hostname}")
if primary_domain:
    for scheme in ("https", "http"):
        origin = f"{scheme}://{primary_domain}"
        if origin not in csrf_hosts:
            csrf_hosts.append(origin)
if csrf_hosts:
    CSRF_TRUSTED_ORIGINS = csrf_hosts

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
    "hub.apps.HubConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "accounts.middleware.PasswordChangeRequiredMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "request_hub.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "hub.context_processors.notification_badges",
            ],
        },
    },
]

WSGI_APPLICATION = "request_hub.wsgi.application"
ASGI_APPLICATION = "request_hub.asgi.application"

DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "admin123")
DB_PASSWORD = os.getenv("DB_PASSWORD", "@Password123")
DB_HOST = os.getenv("DB_HOST", "requesthub-postgre.postgres.database.azure.com")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
DB_SSLROOTCERT = os.getenv("DB_SSLROOTCERT")
DB_CONN_MAX_AGE = int(os.getenv("DB_CONN_MAX_AGE", "60"))

db_options = {}
if DB_SSLMODE:
    db_options["sslmode"] = DB_SSLMODE
if DB_SSLROOTCERT:
    db_options["sslrootcert"] = DB_SSLROOTCERT

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": DB_CONN_MAX_AGE,
        "OPTIONS": db_options,
    }
}

if not db_options:
    DATABASES["default"].pop("OPTIONS")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

media_url_setting = os.getenv("DJANGO_MEDIA_URL", "media/").strip()
if not media_url_setting.startswith("/"):
    media_url_setting = f"/{media_url_setting}"
if not media_url_setting.endswith("/"):
    media_url_setting = f"{media_url_setting}/"
MEDIA_URL = media_url_setting

media_root_setting = os.getenv("DJANGO_MEDIA_ROOT")
if media_root_setting:
    MEDIA_ROOT = Path(media_root_setting).expanduser()
else:
    MEDIA_ROOT = BASE_DIR / "media"

try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except OSError:
    # Some deployment targets provide a read-only mount during build; skip creation errors.
    pass

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "hub:dashboard"
LOGOUT_REDIRECT_URL = "login"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

PROFILE_COMPLETION_EXEMPT_URLS = [
    "accounts:update",
    "logout",
]
