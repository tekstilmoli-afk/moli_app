from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 🧭 Admin paneli
    path("admin/", admin.site.urls),

    # 🏠 Ana sayfa (sipariş listesi)
    path("", views.order_list, name="order_list"),

    # 📝 Sipariş işlemleri
    path("order/new/", views.order_create, name="order_create"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),

    # 👤 Müşteri işlemleri
    path("musteri/new/", views.musteri_create, name="musteri_create"),

    # 📤 Excel aktarımı
    path("export/excel/", views.export_orders_excel, name="export_orders_excel"),
]

# 📌 Statik dosyalar (CSS, JS) için servis ayarı
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 📌 Medya dosyaları (örneğin QR kodları ve yüklenen resimler)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)