"""
Django settings for moli project (optimized for PostgreSQL + Render).
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# 📌 Ana dizin yolu
BASE_DIR = Path(__file__).resolve().parent.parent

# 📌 .env dosyasını manuel olarak BASE_DIR'den yükle
dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print(f"✅ .env yüklendi: {dotenv_path}")
else:
    print(f"⚠️ .env bulunamadı: {dotenv_path}")

# ⚙️ Güvenlik
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-placeholder')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,.onrender.com').split(',')

# 📦 Yüklü uygulamalar
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

# 🌐 Middleware sırası — ⚡️ Düzenlenmiş
MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',  # ⚡️ Cache en üste
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',  # ⚡️ Cache en alta
]

# 📌 URL ve WSGI ayarları
ROOT_URLCONF = 'moli.urls'
WSGI_APPLICATION = 'moli.wsgi.application'

# 📝 Template ayarları
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    print("✅ Render veritabanına bağlanılıyor...")
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    print("⚠️ DATABASE_URL bulunamadı, Railway fallback devreye girdi!")
    DATABASES = {
        'default': dj_database_url.parse(
            'postgresql://postgres:xUPplVVDFeKUSjnfTgtxIvvrZAWnMSaq@switchyard.proxy.rlwy.net:23849/railway',
            conn_max_age=600,
            ssl_require=True
        )
    }


# ⚡ PostgreSQL performans seçenekleri
DATABASES['default']['OPTIONS'] = {
    'options': '-c statement_timeout=30000 -c lock_timeout=5000 -c idle_in_transaction_session_timeout=10000'
}

# 🔒 Şifre doğrulama
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 🌍 Dil / Zaman
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# 🧠 Cache (Redis varsa kullan, yoksa LocMem)
if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'IGNORE_EXCEPTIONS': True,
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

CACHE_MIDDLEWARE_SECONDS = 120  # 2 dakika cache
CACHE_MIDDLEWARE_KEY_PREFIX = 'moli'

# 🧭 Oturum ayarları (Cache + DB)
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = 15 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# 🧰 Statik / Medya dosyaları
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 🌍 Production — Whitenoise sıkıştırma
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 🔐 HTTPS güvenlik ayarları
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# 👤 Giriş / çıkış yönlendirmeleri
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# 🆔 Varsayılan Primary Key tipi
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 🌐 Supabase Ayarları
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_BUCKET_NAME = os.getenv('SUPABASE_BUCKET_NAME', 'qr-codes')

BASE_URL = os.getenv('BASE_URL', 'https://moli-app.onrender.com')


# 🔑 Gemini API anahtarı
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")