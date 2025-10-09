from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.order_list, name="order_list"),                    # 🏠 Ana sayfa → Sipariş Listesi
    path("order/new/", views.order_create, name="order_create"),       # ➕ Yeni Sipariş
    path("order/<int:pk>/", views.order_detail, name="order_detail"),  # 🔍 Sipariş Detay
    path("musteri/new/", views.musteri_create, name="musteri_create"), # 🧍 Yeni Müşteri
    path("export/excel/", views.export_orders_excel, name="export_orders_excel"),
]

# 📂 Medya dosyaları (örneğin QR kodlar) için geliştirme ortamında servis
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
