"""
Django settings for moli project.
"""

from pathlib import Path
import os
import dj_database_url

# 📌 Ana dizin yolu
BASE_DIR = Path(__file__).resolve().parent.parent

# ⚠️ Güvenlik
SECRET_KEY = 'django-insecure-=txqn8ko9(2^=#k50qxd^@y-6gujv3a0%f283zfkz23@_i2wy#'

# 💡 Geliştirme sırasında True, Render'da otomatik False yapılacak
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Render ve local için izinli hostlar
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.onrender.com']

# 📦 Uygulamalar
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

# 🌐 Middleware sırası
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Statik dosyaları production'da servis eder
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'moli.urls'

# 🧠 Template ayarları
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
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

WSGI_APPLICATION = 'moli.wsgi.application'

# 🗃️ Veritabanı — Railway PostgreSQL
DATABASES = {
    'default': dj_database_url.parse(
        'postgresql://postgres:xUPplVVDFeKUSjnfTgtxIvvrZAWnMSaq@switchyard.proxy.rlwy.net:23849/railway',
        conn_max_age=600,
        ssl_require=True
    )
}

# 🔐 Şifre doğrulama
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 🌍 Uluslararasılaştırma
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# 🧠 Basit Cache Ayarı
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Varsayılan cache süresi (saniye)
CACHE_MIDDLEWARE_SECONDS = 60
CACHE_MIDDLEWARE_KEY_PREFIX = ''

# 🧰 Statik dosyalar
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "media",   # ✅ QR kodlarını da static build içine dahil et
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 📂 Medya dosyaları (örneğin yüklenen resimler, QR kodlar)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 🌍 Production ortamı için statik dosya ayarı (Render)
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 👤 Login yönlendirmeleri
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/home/"
LOGOUT_REDIRECT_URL = "/login/"

# 🔑 Varsayılan primary key tipi
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
