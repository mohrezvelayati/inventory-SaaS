import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *  # noqa: F403


SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "phone_number",
    "code",
    "password",
    "current_password",
    "new_password",
    "access",
    "refresh",
}


def scrub_sensitive_data(event, hint):
    def scrub(value):
        if isinstance(value, dict):
            return {
                key: (
                    "[Filtered]"
                    if isinstance(key, str) and key.lower() in SENSITIVE_KEYS
                    else scrub(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return scrub(event)


render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")  # noqa: F405
if render_hostname and render_hostname not in ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS.append(render_hostname)  # noqa: F405

if SECRET_KEY == "django-insecure-local-development-only":  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY must be set in production")
if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production")

DEBUG = False
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
DATABASES["default"]["CONN_MAX_AGE"] = int(  # noqa: F405
    os.getenv("DATABASE_CONN_MAX_AGE", "60")  # noqa: F405
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "3600"))  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},  # noqa: F405
}

if SENTRY_DSN:  # noqa: F405
    sentry_sdk.init(
        dsn=SENTRY_DSN,  # noqa: F405
        integrations=[DjangoIntegration()],
        environment=APP_ENVIRONMENT,  # noqa: F405
        release=APP_RELEASE,  # noqa: F405
        send_default_pii=False,
        before_send=scrub_sensitive_data,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),  # noqa: F405
    )
