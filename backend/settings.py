import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
# from celery.schedules import crontab
from pathlib import Path
import environ
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# External service keys
DOUBLETICK_API_KEY = env("DOUBLETICK_API_KEY", default="dummy_key")
DOUBLETICK_SENDER_ID = env("DOUBLETICK_SENDER_ID", default="0000000000")
AFRICASTALKING_USERNAME = env("AFRICASTALKING_USERNAME", default="test")
AFRICASTALKING_API_KEY = env("AFRICASTALKING_API_KEY", default="dummy")

ASGI_APPLICATION = "helpdesk.asgi.application"


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-&mx*m9f0d3i67c^n$=o79ac7ejax299+0yedv+oh&y2f6w_b29'

DEBUG = True

ALLOWED_HOSTS = []

DOUBLETICK_API_KEY = env("DOUBLETICK_API_KEY")
DOUBLETICK_SENDER_ID = env("DOUBLETICK_SENDER_ID")

AFRICASTALKING_USERNAME = env("AFRICASTALKING_USERNAME")
AFRICASTALKING_API_KEY = env("AFRICASTALKING_API_KEY")


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = "apikey"
EMAIL_HOST_PASSWORD = os.getenv("SENDGRID_API_KEY") 
DEFAULT_FROM_EMAIL = "sonnen.naswem@bdic.ng"

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'debug_toolbar',
    'django_prometheus',

    'backend.core',
    'channels'
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
   # "https://your-production-domain.com",
]

CORS_ALLOW_CREDENTIALS = True

sentry_sdk.init(
    dsn="https://21838d79efdeac158c82c02e75a06638@o4510476514426880.ingest.us.sentry.io/4510476680626176",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
     "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,   # 👈 adjust this number as needed
     
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = [
    "127.0.0.1",
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'benue_helpdesk',   #  
        'USER': 'helpdesk_user',         #  
        'PASSWORD': 'GodIsGreat234#', # 
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

ROOT_URLCONF = 'backend.helpdesk.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.helpdesk.wsgi.application'

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),   # default is 5 minutes
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),      # default is 1 day
    "ROTATE_REFRESH_TOKENS": True,                    # optional: issue new refresh token on use
    "BLACKLIST_AFTER_ROTATION": True,                 # optional: prevent reuse of old refresh tokens
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.User'
# Celery settings
# CELERY_BROKER_URL = 'redis://localhost:6379/0'   # 👈 Redis as broker
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_BEAT_SCHEDULE = {
#    "send-deadline-reminders-every-hour": {
#        "task": "backend.core.task.send_deadline_reminders",
#        "schedule": crontab(minute=0, hour="*"),  # every hour
#    },
# }