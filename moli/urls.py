from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views   # 👈 Eğer views core içindeyse bu şekilde olmalı

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.order_list, name="order_list"),
    path("order/new/", views.order_create, name="order_create"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),
    path("musteri/new/", views.musteri_create, name="musteri_create"),
    path("export/excel/", views.export_orders_excel, name="export_orders_excel"),
]

# ✅ QR kodları ve medya dosyaları için
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
