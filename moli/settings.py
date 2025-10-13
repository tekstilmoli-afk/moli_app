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

# 🌐 İzin verilen hostlar (Render + Local)
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.onrender.com']

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

# 📌 URL ve WSGI ayarları
ROOT_URLCONF = 'moli.urls'
WSGI_APPLICATION = 'moli.wsgi.application'

# 🗃️ Veritabanı (Render / Railway)
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

# 🌍 Dil ve saat ayarları
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# 🧠 Cache (isteğe bağlı basit yapı)
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
    BASE_DIR / "static",  # Proje içindeki static klasörü
]
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic çıktısı buraya gider

# 📂 Medya dosyaları (örneğin yüklenen resimler, QR kodlar)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 🌍 Production için Whitenoise ayarı
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 👤 Oturum yönlendirmeleri (opsiyonel)
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# 🆔 Varsayılan Primary Key tipi
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
