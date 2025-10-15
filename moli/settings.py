"""
Django settings for moli project.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv  # 👈 .env dosyasını okumak için

# 📌 .env dosyasını yükle
load_dotenv()

# 📌 Ana dizin yolu
BASE_DIR = Path(__file__).resolve().parent.parent

# ⚠️ Güvenlik
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-=txqn8ko9(2^=#k50qxd^@y-6gujv3a0%f283zfkz23@_i2wy#')

# 💡 DEBUG ayarı (.env'den okunur)
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# 🌐 İzin verilen hostlar (Render + Local)
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

# 🌐 Middleware sırası — ✅ DÜZELTİLMİŞ
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # ⬅️ Giriş kontrolü cache'ten önce
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # ⬇️ Cache middleware'leri en alta
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
]

# 📌 URL ve WSGI ayarları
ROOT_URLCONF = 'moli.urls'

# 📝 Template ayarları (HTML dosyalarını bulması için)
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

WSGI_APPLICATION = 'moli.wsgi.application'

# 🗃️ Veritabanı (Render / Railway)
DATABASES = {
    'default': dj_database_url.parse(
        os.getenv('DATABASE_URL', 'postgresql://postgres:xUPplVVDFeKUSjnfTgtxIvvrZAWnMSaq@switchyard.proxy.rlwy.net:23849/railway'),
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

# 🌍 Dil ve saat ayarları
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# 🧠 Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
CACHE_MIDDLEWARE_SECONDS = 60
CACHE_MIDDLEWARE_KEY_PREFIX = ''

# 🧰 Statik dosyalar
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 📂 Medya dosyaları
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 🌍 Production için Whitenoise ayarı
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 👤 Giriş / çıkış yönlendirmeleri
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# 🆔 Varsayılan Primary Key tipi
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 🌐 Supabase Ayarları (QR kodları burada saklayacağız)
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_BUCKET_NAME = os.getenv('SUPABASE_BUCKET_NAME', 'qr-codes')

BASE_URL = "https://moli-app.onrender.com"

# 🧭 Oturum ayarları (15 dakika)
SESSION_COOKIE_AGE = 15 * 60  # 15 dakika
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
